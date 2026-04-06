# Velaris-Agent 架构文档（OpenHarness 二开）

## 1. 架构目标

Velaris-Agent 不再只作为“多 Agent 框架”，而是聚焦为：

1. 决策中枢：把自然语言目标编译为可执行策略。
2. 治理中枢：把权限、审批、停止条件从 Prompt 中剥离。
3. 评估中枢：形成质量/成本/风险可回放闭环。

## 2. 总体分层

### 2.1 逻辑分层

| 层级 | 组件 | 职责 |
|---|---|---|
| L0 | EventBus / AgentNetwork | 事件总线与子 Agent 协作 |
| L1 | GoalParser | NL -> Goal 结构化解析 |
| L2 | PolicyRouter / Planner | 策略路由与执行计划生成 |
| L3 | DecisionCore | 候选过滤、多维打分、模型路由 |
| L4 | AuthorityService / Executor | 最小权限签发与执行编排 |
| L5 | Evaluator / OutcomeStore | 结果评估与策略反馈回写 |
| Control | TaskLedger | 生命周期账本、审计与回放 |

### 2.2 OpenHarness 继承点

Velaris 二开明确复用 OpenHarness 的系统思想：

- Engine：会话循环与工具调用。
- Tools + Skills：领域工具与技能知识注入。
- Permissions + Hooks：审批与拦截。
- Swarm + Tasks + Coordinator：多 agent 协调与后台任务。
- Memory：跨会话记忆与长期优化。

## 3. 关键数据流

```text
用户输入
  -> GoalParser 目标结构化
  -> PolicyRouter 路由策略命中
  -> AuthorityService 签发能力令牌
  -> Planner / DecisionCore 产出执行方案
  -> Executor 执行技能链路
  -> Evaluator 计算质量/成本/风险
  -> OutcomeStore 回写结果
  -> TaskLedger 保留全流程轨迹
```

## 4. 路由治理模型

### 4.1 输入契约

`contracts/decision-contract/input.schema.json` 定义路由输入：

- goal/risk/state/budgets
- capabilityDemand/governance
- availableRuntimes

### 4.2 输出契约

`contracts/decision-contract/output.schema.json` 定义决策输出：

- selectedStrategy + selectedRoute
- stopProfile + activeStopConditions
- authorityPlan + executionPlan
- trace（规则命中链路）

### 4.3 策略配置

`config/routing-policy.yaml` 定义：

- 策略集（local/delegated/hybrid）
- 停止画像（strict_approval/balanced/fast_fail）
- 规则优先级和匹配条件

## 5. 当前代码映射

| 目标能力 | 文件 |
|---|---|
| 策略路由 | `packages/core/src/policy/router.ts` |
| 默认策略 | `packages/core/src/policy/default-routing-policy.ts` |
| 能力令牌 | `packages/core/src/governance/authority.ts` |
| 任务账本 | `packages/core/src/control/task-ledger.ts` |
| Outcome 回写 | `packages/core/src/eval/outcome-store.ts` |
| 主会话编排 | `packages/core/src/agent.ts` |
| Python 业务能力层 | `velaris-agent-py/src/openharness/biz/engine.py` |
| Python 路由治理层 | `velaris-agent-py/src/openharness/velaris/` |
| Python 业务闭环工具 | `velaris-agent-py/src/openharness/tools/biz_execute_tool.py` |

## 6. 三大业务场景映射

1. 商旅 AI 助手
- 路由目标：`local_closed_loop` 或 `delegated_openclaw`
- 关注指标：推荐准确率、比价耗时、用户采纳率

2. AI TokenCost
- 路由目标：`local_closed_loop`
- 关注指标：成本下降率、质量损失、分析成本

3. OpenClaw 运行环境
- 路由目标：`delegated_openclaw` / `hybrid_openclaw_claudecode`
- 关注指标：审批命中率、越权阻断率、调度成功率

## 7. 演进路线

1. 先在 TS 核心完成路由治理闭环与契约稳定。
2. 已在仓库内落地 `velaris-agent-py/`，并补齐 `biz + velaris runtime` 的 Python 最小闭环。
3. 最终形成“Python 生产运行时 + TS 策略仿真与测试层”的双轨架构。
