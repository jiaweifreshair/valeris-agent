# UOW-1 代码总结 - Repository Layer

## 范围

本文件总结 `UOW-1` 在持久化主线上的收束。当前仓库默认且唯一主线为 **SQLite 单库**
（默认路径：`<project>/.velaris-agent/velaris.db`），覆盖：

- schema bootstrap
- execution / session 显式仓储
- task / outcome / audit 运行时仓储
- `session_storage` 的 SQLite 化
- 写入前脱敏与 JSON 序列化约束

## 关键实现文件

- `src/velaris_agent/persistence/schema.py`
- `src/velaris_agent/persistence/sqlite_execution.py`
- `src/velaris_agent/persistence/sqlite_runtime.py`
- `src/velaris_agent/persistence/factory.py`
- `src/velaris_agent/persistence/__init__.py`
- `src/openharness/services/session_storage.py`

## 已落地设计对照

### 1. SQLite 成为正式主存储

- schema bootstrap 显式创建 `session_records` 与 `execution_records` 两张主表，并保留 payload 型卫星表：
  - `task_ledger_records`
  - `outcome_records`
  - `audit_events`
- 工厂层在解析到 `cwd/sqlite_database_path` 时会 **幂等** bootstrap schema，避免调用方必须先手动 init 才能运行。

### 2. session / execution 显式主记录

- `SessionRecord` 以 `session_id` 为主键保存 `snapshot_json`（其中必须包含 `cwd`，以支持按工作区检索）。
- `BizExecutionRecord` 以 `execution_id` 为主键保存执行主状态字段与 `resume_cursor`，
  同时允许通过 `session_id` 建立引用关系（不强制等同）。

### 3. 不依赖 SQLite JSON1

所有 JSON 字段统一以 TEXT 存储，序列化/反序列化由 Python 负责（`json.dumps/json.loads`），
避免运行环境差异（例如 JSON1 扩展缺失）导致的行为漂移。

### 4. session_storage 收束到 SQLite 主线

- OpenHarness 的 session snapshot 不再写入 `latest.json / session-*.json`。
- 文件系统仅保留 Markdown transcript 导出作为辅助输出，不承载恢复真相源。

### 5. 默认脱敏写入

`PayloadRedactor` 在 barrier / runtime 存储前被复用，确保敏感字段不以明文落库（尤其是 audit 与 snapshot）。

## 测试覆盖点

- `tests/test_persistence/test_schema.py`
- `tests/test_persistence/test_sqlite_execution.py`
- `tests/test_persistence/test_sqlite_runtime.py`
- `tests/test_services/test_session_storage.py`
- `tests/test_biz/test_persistence_barrier.py`

重点覆盖：

- schema 是否包含 session/execution 主表
- execution/session 仓储的 create/update/get/list 语义
- runtime 仓储的写入与查询
- session_storage 的保存/按 cwd 列表/按 id 读取

## 剩余风险

- SQLite 文件落盘依赖工作区可写权限；若 `cwd` 不可写，必须在 scenario 执行前 fail-closed。
- WAL + 并发写在极端情况下仍可能出现锁竞争；需持续关注 busy_timeout 与事务边界。
