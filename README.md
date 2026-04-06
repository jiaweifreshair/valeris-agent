# Velaris Agent（OpenHarness 二开版）

> 目标：基于 OpenHarness 打造可审计、可治理、可持续优化的多场景决策系统。

## 1. 项目定位

Velaris Agent 当前定位为 **决策中枢 + 治理编排层**，面向三个核心业务场景：

1. 商旅 AI 助手：行程意图解析、多源比价、组合推荐。
2. AI TokenCost：成本审计、模型替换建议、降本闭环。
3. OpenClaw 车端运行环境：三段式派单协议与可审计调度。

系统采用 **OpenHarness 能力模型** 做二次开发：

- Engine：流式 Agent 循环与工具调用编排。
- Tools/Skills：工具和技能体系。
- Permissions/Hooks：权限和生命周期治理。
- Swarm/Tasks/Coordinator：多 Agent 协作与后台任务。
- Memory：跨会话记忆与策略回写。

OpenHarness 上游仓库：`git@github.com:HKUDS/OpenHarness.git`

## 2. 当前仓库状态

本仓库保留 TypeScript 决策运行时实现，并已补齐 OpenHarness 风格的治理骨架：

- 路由策略引擎：`PolicyRouter`
- 权限签发：`AuthorityService`
- 任务账本：`TaskLedger`
- 结果沉淀：`OutcomeStore`
- Python 运行时已补齐 `biz` 业务能力层与 `velaris` 路由治理闭环
- Python 路由器已改为读取统一策略文件 `config/routing-policy.yaml`
- `velaris_agent.*` 原生命名空间已开始承载新业务/治理实现，`openharness.*` 保留兼容导出

对应代码位置：

- `packages/core/src/policy/`
- `packages/core/src/governance/`
- `packages/core/src/control/`
- `packages/core/src/eval/`
- `velaris-agent-py/src/openharness/biz/`
- `velaris-agent-py/src/openharness/velaris/`

## 3. 架构分层

| 层级 | 模块 | 核心职责 |
|---|---|---|
| L0 | EventBus / AgentNetwork | 事件总线、子 Agent 编排 |
| L1 | GoalParser | 自然语言与结构化目标统一解析 |
| L2 | PolicyRouter / Planner | 策略路由与执行计划生成 |
| L3 | DecisionCore | 多维打分、约束过滤、模型路由 |
| L4 | AuthorityService / Executor | 最小权限签发与执行编排 |
| L5 | Evaluator / OutcomeStore | 质量成本评估、策略反馈回写 |
| Control | TaskLedger | 生命周期跟踪与审计回放 |

## 4. 核心契约与策略配置

- 路由策略：`config/routing-policy.yaml`
- 决策输入契约：`contracts/decision-contract/input.schema.json`
- 决策输出契约：`contracts/decision-contract/output.schema.json`
- 停止条件契约：`contracts/decision-contract/stop-conditions.schema.json`

## 5. 开发与验证

### 环境要求

- Node.js >= 20
- pnpm >= 10

### 常用命令

```bash
pnpm install
pnpm build
pnpm typecheck
pnpm test
```

### 当前测试状态

- `@velaris/core`：44 个测试全部通过（含新增路由治理测试）。

## 6. Phase 化二开计划

### Phase 1（已完成）

1. 引入 OpenHarness 风格治理模型（路由/权限/账本/结果回写）。
2. 契约化输入输出与停止条件。
3. 补齐单元测试并通过 typecheck/test。

### Phase 2（进行中）

1. 已引入 `velaris-agent-py/`，迁入本地 OpenHarness Python 基线并完成首轮入口改造。
2. 已接入 `biz_execute / biz_plan / biz_score / biz_run_scenario` 业务能力工具。
3. 已补齐 `travel_recommend / tokencost_analyze / openclaw_dispatch` 三类领域工具入口。
4. 三类领域工具已支持 `file/http` 数据源 adapter，并保留显式入参覆盖。
5. 已落地商旅、TokenCost、OpenClaw 三类场景测试，并映射 Python 版路由、签权、账本、Outcome。

### Phase 3（待执行）

1. 打通路由策略到真实外部 runtime（OpenClaw/Claude Code）。
2. 抽离 TS 为策略仿真与契约验证层。
3. 建立统一 API 与观测面板（质量/成本/风险/审批命中率）。

## 7. 文档索引

- 技术总方案：`docs/TECHNICAL-PLAN.md`
- 架构文档：`docs/ARCHITECTURE.md`
- 场景验证：`docs/VALIDATION-CASES.md`
- Python 迁移说明：`velaris-agent-py/docs/MIGRATION.md`
