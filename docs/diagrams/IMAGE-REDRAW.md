# 图片重画（Mermaid 版）

> 来源：你提供的 3 张截图（ShanClaw 架构图 + Claude Code Runtime 架构图）
> 说明：按可读信息重画了核心结构与主链路；极小字号注释做了语义归并。

## 1) ShanClaw 智能体循环架构（重画）

```mermaid
flowchart LR
  %% 输入入口
  subgraph ENTRY[输入入口]
    E1[TUI 终端交互]
    E2[CLI 命令行]
    E3[Daemon 守护进程]
    E4[Desktop 客户端]
  end

  %% 主循环
  subgraph LOOP[主循环]
    L1[上下文观察]
    L2[LLM 调用]
    L3[响应处理]
    L4[工具三阶段]
    L5[循环判定]
    L1 --> L2 --> L3 --> L4 --> L5
  end

  %% 工具能力
  subgraph TOOLS[工具与执行]
    T1[MCP 工具]
    T2[网关工具]
    T3[cloud_delegate]
    T4[use_skill]
    T5[file_read / bash / screenshot / browser]
  end

  %% 外部运行时
  subgraph RUNTIME[外部运行时]
    R1[Anthropic Claude]
    R2[OpenAI / Google]
    R3[Shannon Cloud]
    R4[MCP Server 进程]
  end

  %% 安全和治理
  subgraph GOV[治理与安全]
    G1[五重权限模型]
    G2[硬拦截规则]
    G3[Shell AST 分析]
    G4[allow + 默认安全]
  end

  %% 记忆与上下文
  subgraph MEMORY[上下文与记忆]
    M1[窗口监控]
    M2[PersistLearnings]
    M3[GenerateSummary]
    M4[ShapeHistory]
  end

  %% 云委托
  subgraph CLOUD[Cloud 委托流程]
    C1[SubmitTaskStream]
    C2[SSE 事件流]
    C3[工作流类型]
    C4[结果聚合]
  end

  %% Hooks
  subgraph HOOKS[Hooks 钩子]
    H1[PreToolUse]
    H2[PostToolUse]
    H3[Session 生命周期]
  end

  %% 模式切换
  subgraph MODE[模式管理]
    D1[TUI 模式]
    D2[CLI 模式]
    D3[Daemon 模式]
    D4[自动审批]
  end

  %% Daemon 核心
  subgraph DAEMON[Daemon 核心模块]
    K1[HTTP Server]
    K2[SessionCache]
    K3[RunAgent]
    K4[EventBus]
    K5[ApprovalBroker]
    K6[MCP Supervisor]
    K7[Config 热重载]
  end

  ENTRY --> LOOP
  LOOP --> TOOLS
  TOOLS --> RUNTIME

  LOOP -.安全策略.-> GOV
  LOOP -.上下文回写.-> MEMORY
  LOOP -.委托执行.-> CLOUD
  LOOP -.生命周期拦截.-> HOOKS
  LOOP -.运行模式.-> MODE

  MODE --> DAEMON
  CLOUD --> DAEMON
  HOOKS --> DAEMON
```

---

## 2) Claude Code Agent Runtime（重画）

```mermaid
flowchart LR
  %% 入口层
  subgraph INPUT[入口形态]
    I1[Interactive REPL]
    I2[Headless / SDK]
    I3[Remote / CCR]
    I4[Bridge 工作节点]
    I5[Server Mode]
  end

  %% Query Loop
  subgraph QUERY[Query Loop / 对话循环]
    Q1[QueryEngine.ts]
    Q2[query.ts 主循环]
    Q3[System Prompt 组装]
    Q4[services/api/claude.ts]
    Q5[循环控制]
    Q1 --> Q2 --> Q3 --> Q4 --> Q5
  end

  %% Tool Runtime
  subgraph TOOLRT[Tool Runtime]
    T1[tools.ts 注册中心]
    T2[toolOrchestration.ts]
    T3[toolExecution.ts]
    T4[Tools 统一协议]
    T5[StreamingToolExecutor]
    T1 --> T2 --> T3 --> T4 --> T5
  end

  %% 执行资源
  subgraph EXEC[执行资源]
    X1[Anthropic Claude API]
    X2[MCP Server 进程]
    X3[本地文件系统]
    X4[Shell / 子进程]
  end

  %% 权限系统
  subgraph PERM[权限决策]
    P1[PermissionMode]
    P2[4 路 Race 解析]
    P3[Bash Classifier]
    P4[LLM 自动判断]
    P5[规则引擎 allow/deny/ask]
    P6[ResolveOnce 原子竞争]
  end

  %% 上下文压缩
  subgraph CONTEXT[上下文压缩]
    C1[snip_compact]
    C2[microcompact]
    C3[context collapse]
    C4[折叠已完成子对话]
    C5[autoCompact]
  end

  %% 能力系统
  subgraph CAP[能力系统]
    A1[Commands 80+]
    A2[Skills 技能]
    A3[Plugins 插件]
    A4[MCP Client]
  end

  %% Agent/Task
  subgraph AGENT[Agent / Task 子系统]
    G1[AgentTool]
    G2[Task 统一壳]
    G3[SendMessageTool]
    G4[worktree / remote 隔离]
  end

  %% 记忆状态
  subgraph STATE[持久化状态]
    S1[bootstrap/state.ts]
    S2[AppStateStore]
    S3[sessionStorage.ts]
    S4[history.ts]
    S5[compact boundary]
    S6[fileHistory]
    S7[memdir/MEMORY.md]
  end

  %% 右侧能力块
  subgraph EXT[扩展能力块]
    E1[BUDDY 虚拟宠物]
    E2[KAIROS 常驻智能体]
    E3[ULTRAPLAN 远程规划]
    E4[Coordinator 协调器]
  end

  INPUT --> QUERY --> TOOLRT --> EXEC
  QUERY -.权限拦截.-> PERM
  QUERY -.上下文治理.-> CONTEXT
  TOOLRT -.能力扩展.-> CAP
  TOOLRT -.任务编排.-> AGENT
  QUERY -.状态沉淀.-> STATE
  AGENT -.多智能体协作.-> EXT
```

---

## 3) 对齐 Velaris 的映射建议

- `Query Loop` 对齐 `Goal/Policy/Team` 三层：输入解析、策略选择、角色编排。
- `Tool Runtime + Permission` 对齐 `Control/Authority`：执行生命周期 + 审批治理。
- `State + Context` 对齐 `Evaluation`：把每次策略结果沉淀到 Outcome 回放。
- `Cloud Delegate / Agent Task` 对齐 `delegated_openclaw / delegated_claude_code / hybrid` 路由策略。

