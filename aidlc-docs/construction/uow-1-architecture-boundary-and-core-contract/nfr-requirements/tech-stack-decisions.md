# Tech Stack Decisions

## 1. 决策目标

本文件记录 `UOW-1 - Architecture Boundary And Core Contract` 在 NFR Requirements 阶段正式锁定的技术栈与技术边界决策。
这些决策服务于三个目标：

- 保证 `Velaris` 的 execution-level contract 有单一、可验证的持久化主线
- 保证 governance gate、审计与恢复语义不依赖“增强路径”补位
- 为后续 `NFR Design` 与 `Code Generation` 提供收敛方向，而不是继续保留并行技术路线

## 2. 决策摘要

| 编号 | 决策 | 结论 |
| --- | --- | --- |
| TSD-01 | 主存储技术 | `execution / task / outcome / audit / session` 统一使用 SQLite（项目内单库） |
| TSD-02 | 当前阶段覆盖边界 | 只正式锁定 UOW-1 当前对象；后续对象延续 SQLite 主线，但不在本单元超前细化 |
| TSD-03 | 运行时后端策略 | 旧的 JSON / 文件真相源彻底停用；文件系统仅保留 transcript 导出等非真相用途 |
| TSD-04 | 审计与异步补写技术边界 | 不新增 Redis / Kafka；即使存在补审计，最终落点仍为 SQLite（同库） |
| TSD-05 | 工具输出 contract | 以 `DecisionExecutionEnvelope` 为正式 contract，只保留极少数兼容 alias |
| TSD-06 | 安全基线 | 默认脱敏 + 明确文件路径边界 + 最小权限/文件权限 + 禁止写入敏感目录 |
| TSD-07 | 性能收束策略 | 保持当前单进程本地编排主线，不额外引入中间件，以满足 `planning + gate p95 < 500ms` |

## 3. 详细技术决策

### TSD-01 SQLite 作为本单元唯一正式主存储

#### 决策

`UOW-1` 中正式承诺以下对象统一进入 SQLite 主线（默认路径 `<project>/.velaris-agent/velaris.db`）：

- `BizExecutionRecord`（`execution_records`）
- session snapshot / reference（`session_records`）
- task ledger records（`task_ledger_records`）
- outcome records（`outcome_records`）
- audit event records（`audit_events`）

#### 理由

1. 用户已确认 SQLite 取代 PostgreSQL 成为默认且唯一主线存储。
2. execution、audit 与 session 若分散在多种持久化介质上，会直接破坏恢复与审计边界。
3. SQLite 单库更适合本阶段“最小可信闭环”的交付节奏：零外部依赖、易复现、易测试。

#### 影响

- `src/velaris_agent/persistence/factory.py` 默认围绕 SQLite 构建仓储并幂等 bootstrap schema。
- `src/openharness/services/session_storage.py` 默认写入 SQLite；旧 JSON session 文件不再读写。

### TSD-02 只锁定 UOW-1 当前对象，不超前细化后续对象

#### 决策

本阶段只正式锁定 `execution / task / outcome / audit / session` 五类对象进入 SQLite。
对更后续的决策记忆扩展对象，只写入“后续单元延续 SQLite 主线”，不在本单元提前承诺表结构或具体持久化模型。

#### 理由

1. 这能避免 `UOW-1` 超范围承诺尚未设计的对象。
2. 这同时保留“单库真相源”的关键约束，不会让后续单元重新打开主存储选型。

#### 影响

- `UOW-2` 与 `UOW-3` 只能在 SQLite 主线上继续展开
- 后续设计可以细化对象，但不能重新引入第二套正式主存储

### TSD-03 旧 JSON / 文件真相源彻底停用

#### 决策

旧的 JSON session 文件（`latest.json / session-*.json`）不再读写、也不做迁移。
文件系统仅保留“导出 transcript”等辅助输出，不承载恢复真相源。

#### 理由

1. 多真相源会放大恢复歧义，破坏 execution-level contract 的稳定性。
2. 本单元已把 execution 视为一等主对象，必须避免在“文件 / 内存 / 数据库”之间摇摆。

#### 影响

- `session_storage` 的恢复与列表页逻辑必须完全来自 SQLite
- 任何继续依赖旧 JSON 文件的代码与测试必须移除

### TSD-04 审计最终落点统一为 SQLite，不新增额外中间件

#### 决策

即使中风险 execution 允许补审计，`UOW-1` 也不引入 Redis、Kafka 或其它额外基础设施作为正式依赖。
补审计若存在，其最终落点仍必须是 SQLite（同库）。

#### 理由

1. 本轮强调“最小可信闭环”，不优先扩张基础设施复杂度。
2. 单库落点能让审计与恢复边界更清晰，便于 focused tests 验证。

#### 影响

- NFR Design 需要在“不引入新中间件”的前提下设计补审计可追踪机制
- 补审计是流程策略，不是新的存储主线

### TSD-05 `DecisionExecutionEnvelope` 作为正式工具 contract

#### 决策

`biz_execute` 与后续相关桥接输出应以 `DecisionExecutionEnvelope` 为正式 contract 真相源。
旧字段兼容策略收束为“极少数 alias”，建议保留：

- `session_id`
- `result`
- `outcome`
- `audit_event_count`

除上述 alias 外，不再长期承诺旧平铺字段集合的稳定性。

#### 理由

1. 用户已确认“大部分字段迁入 envelope，只保留极少数兼容别名字段”。
2. 这能把 contract 主语义重新集中到 `Velaris`，避免 `OpenHarness` 继续扮演解释层。

#### 影响

- 文档、测试与新开发都应面向 envelope 编写
- 桥接层只做薄透传，不额外解释内部状态含义

### TSD-06 SQLite 安全基线随主存储决策一并锁定

#### 决策

既然 SQLite 是唯一正式主存储，则其最小安全基线也必须一起锁定：

- 默认脱敏：snapshot / audit / outcome 等长期持久化内容必须过 `PayloadRedactor`
- 明确文件路径边界：仅允许写入 `<project>/.velaris-agent/`，拒绝写入敏感目录（如 `.ssh`、`/etc` 等）
- 最小权限：数据库文件应由当前用户持有，并尽量收紧文件权限（配合宿主机权限模型）
- secret 注入：任何凭据仍通过环境变量或受控 secret 注入，而非硬编码到 snapshot

#### 理由

1. 用户已确认“脱敏 / 最小暴露”优先纳入。
2. SQLite 以文件形态落盘时，路径边界与文件权限就是安全边界的一部分，必须被明确约束。

#### 影响

- 不能为了“调试方便”扩大 snapshot/audit 的敏感字段暴露面
- OpenHarness 作为桥接层不得绕过 Velaris 自行定义敏感字段暴露规则

### TSD-07 保持单进程编排主线，优先收敛而非扩张

#### 决策

为满足本单元 `planning + gate p95 < 500ms` 的目标，当前阶段不新增缓存层、消息队列或新的独立协调服务。
优先沿用现有单进程编排 + SQLite 最小持久化链路收敛。

#### 理由

1. 本轮目标是“默认路径收束 / 最小可信闭环”，不是性能极限优化。
2. 当前性能门槛较宽松，优先收敛主语义与持久化主线更符合阶段目标。

#### 影响

- 性能优化首先从减少不必要序列化、控制同步写入路径、减少无意义回退分支入手
- 若后续需要更激进性能优化，应在不破坏 execution / gate / audit 语义的前提下进行

## 4. 对当前代码的直接指导

这些技术决策对当前代码有以下直接指向：

1. `src/velaris_agent/persistence/sqlite_execution.py` 承担 `execution / session` 的显式主记录落点。
2. `src/velaris_agent/persistence/sqlite_runtime.py` 承担 `task / outcome / audit` 的运行时落点。
3. `src/velaris_agent/persistence/factory.py` 负责 SQLite schema 幂等 bootstrap 与仓储构建，避免调用方绕过工厂。
4. `src/openharness/services/session_storage.py` 负责 OpenHarness 会话快照落库；其恢复入口不再依赖旧 JSON 文件。

## 5. 本阶段未做的技术承诺

为避免在 NFR Requirements 阶段超前进入实现细节，本文件明确不在本阶段承诺：

- 是否引入 SQLCipher 或其它 SQLite 文件级加密方案（当前默认依赖宿主机磁盘/权限能力）
- 是否继续从 payload 型卫星表演进到更细粒度显式列
- 中风险补审计的具体调度机制（同步/异步/修复命令）
- `DecisionExecutionEnvelope` 的最终 JSON 嵌套层级与字段裁剪策略
- 精确到单 SQL 或单函数的性能优化手段

这些内容留待下一阶段 `NFR Design` 继续收束。
