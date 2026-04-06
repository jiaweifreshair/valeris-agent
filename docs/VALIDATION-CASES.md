# Velaris Agent 验证场景（OpenHarness 二开）

> 目标：用可测量场景验证“路由治理 + 决策执行 + 结果回写”闭环。

## 1. Case A：商旅 AI 助手

### 1.1 目标

输入自然语言出行需求，输出可解释的机酒组合推荐。

### 1.2 核心链路

1. `parse_intent`：意图解析。
2. `search_flights` + `search_hotels`：并行检索。
3. `recommend`：组合评分与三档推荐（最省/舒适/最优）。

### 1.3 路由策略建议

- 默认：`local_closed_loop`
- 需审计或外部副作用：`delegated_openclaw`

### 1.4 验证指标

- 推荐可采纳率 >= 60%
- 查询耗时 P95 < 8s
- 组合总价误差 <= 5%

## 2. Case B：AI TokenCost

### 2.1 目标

分析 API 用量，输出可执行降本建议并估算节省空间。

### 2.2 核心链路

1. `analyze_usage`：成本结构识别。
2. `model_compare`：模型质量/成本/时延对比。
3. `optimize_suggest`：建议分级与优先级排序。

### 2.3 路由策略建议

- 默认：`local_closed_loop`
- 写配置/批量执行变更：`delegated_claude_code`

### 2.4 验证指标

- 建议采纳率 >= 60%
- 30 天成本下降 >= 30%
- 质量损失 <= 10%
- 单次分析成本 <= $0.10

## 3. Case C：OpenClaw 运行环境

### 3.1 目标

实现三段式派单协议：意图单 -> 服务提案 -> 交易合约。

### 3.2 核心链路

1. `match_vehicles`：候选运力匹配。
2. `calculate_route`：路径与时效评估。
3. `score_proposals`：多目标打分。
4. `form_contract`：合约生成与审计。

### 3.3 路由策略建议

- 默认：`delegated_openclaw`
- 涉及代码联动改造：`hybrid_openclaw_claudecode`

### 3.4 验证指标

- 调度成功率 >= 95%
- 审批命中率可解释（100% 可追踪）
- 越权执行率 = 0

## 4. 通用验收门槛

1. 编译错误 0。
2. Typecheck 0 error。
3. 核心单测通过。
4. 路由决策含 trace 字段。
5. 任务账本完整记录 queued/running/completed 或 failed。

## 5. 当前完成度

- 已完成：路由器、能力签发、任务账本、Outcome 回写、契约文件。
- 已验证：`pnpm typecheck` 与 `pnpm test` 全部通过。
- 待完成：三大业务场景工具链与真实外部 runtime 全链路联调。

