# Velaris-Agent 技术方案

> 基于 OpenHarness 二开, 实现商旅AI助手 / AI TokenCost / OpenClaw 车端运行环境三大产品场景

---

## 1. 项目概述

### 1.1 定位

Velaris 是一个面向**智能决策**的 AI Agent 平台, 基于 OpenHarness 开源框架二开, 聚焦三个核心场景:

| 场景 | 核心价值 | 用户 |
|------|----------|------|
| **商旅AI助手** | 机票酒店多平台比价 + 意图识别 + 一站式出行方案 | 商旅用户/企业差旅 |
| **AI TokenCost** | AI 使用成本优化, 识别浪费, 输出可执行降本方案 | AI 开发者/企业 |
| **OpenClaw** | 车端开放智能体运行环境, 三段式派单协议 | 出行平台/Robotaxi |

### 1.2 技术基座

| 层 | 技术 | 说明 |
|----|------|------|
| 语言 | Python 3.10+ | 与 flight-compare 同语言, AI 生态最成熟 |
| 框架 | OpenHarness (fork) | 17K LOC, 10子系统, 114测试, 生产就绪 |
| LLM | Anthropic SDK | 多提供商兼容 (OpenAI, Kimi, Vertex, Bedrock) |
| 数据验证 | Pydantic v2 | 严格类型, JSON Schema 自动生成 |
| CLI | Typer | 异步友好, 自动补全 |
| HTTP | httpx | 异步 HTTP 客户端 |
| UI | React/Ink | 终端 UI (TypeScript) |
| 测试 | pytest + pytest-asyncio | 异步测试, 114+ 用例 |
| 包管理 | uv | 快速依赖解析 |
| lint | ruff | 行长 100, target py3.11 |
| 类型 | mypy strict | 严格模式 |

### 1.3 OpenHarness 继承的核心能力

```
OpenHarness 10 子系统
├── Engine        核心 agent 循环, 流式工具调用编排
├── Tools         43+ 内置工具, BaseTool 抽象, ToolRegistry
├── Skills        Markdown-first 知识注入, SkillRegistry
├── Plugins       插件发现/加载/生命周期, plugin.json manifest
├── Permissions   多级权限 (tool/file/command), 3种模式 (default/plan/full_auto)
├── Hooks         生命周期事件 (session_start/end, pre/post_tool_use)
├── Memory        持久化跨会话记忆, MEMORY.md 索引
├── Swarm         多 agent 协调, subprocess/in-process/tmux 后端
├── Tasks         后台任务管理, shell/agent 任务
└── Coordinator   agent 定义, team 注册, 任务通知
```

---

## 2. 整体架构

### 2.1 架构图

```
                         Velaris Agent Platform
                    ┌─────────────────────────────────┐
                    │           CLI / API              │
                    │    (velaris / vl 命令行入口)       │
                    └──────────────┬──────────────────-┘
                                   │
                    ┌──────────────▼──────────────────-┐
                    │        Engine (Query Loop)        │
                    │  流式对话 -> 工具调用 -> 结果回传    │
                    └──────────────┬──────────────────-┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
┌─────────▼─────────┐  ┌─────────-▼─────────┐  ┌─────────-▼─────────┐
│   商旅AI助手       │  │   AI TokenCost     │  │   OpenClaw         │
│                    │  │                    │  │                    │
│ Tools:             │  │ Tools:             │  │ Tools:             │
│  - parse_intent    │  │  - analyze_usage   │  │  - match_vehicles  │
│  - search_flights  │  │  - model_compare   │  │  - calculate_route │
│  - search_hotels   │  │  - optimize_suggest│  │  - score_proposals │
│  - recommend       │  │                    │  │  - form_contract   │
│                    │  │ Skills:            │  │                    │
│ Skills:            │  │  - cost-audit      │  │ Protocol:          │
│  - travel-compare  │  │  - model-routing   │  │  - IntentOrder     │
│  - travel-budget   │  │                    │  │  - ServiceProposal │
│  - travel-itinerary│  │ Data:              │  │  - Transaction     │
│                    │  │  - model_prices    │  │    Contract        │
│ 集成:              │  │                    │  │                    │
│  flight-compare    │  │                    │  │ Agents:            │
│  (直接 import)     │  │                    │  │  - VehicleAgent    │
│                    │  │                    │  │  - UserAgent       │
└────────────────────┘  └────────────────────┘  └────────────────────┘
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────-┐
                    │      OpenHarness 基础设施          │
                    │  Permissions | Hooks | Memory     │
                    │  Swarm | Tasks | Plugins | MCP    │
                    └──────────────────────────────────-┘
```

### 2.2 目录结构

```
velaris-agent-py/
├── pyproject.toml                      # 包配置 (name="velaris")
├── README.md
├── docs/
│   ├── TECHNICAL-PLAN.md              # 本文档
│   ├── SHOWCASE.md
│   ├── TRAVEL-ASSISTANT.md            # 商旅助手指南
│   ├── TOKENCOST.md                   # TokenCost 指南
│   └── OPENCLAW-PROTOCOL.md           # 三段式派单协议
├── src/
│   └── velaris/                        # (原 openharness/)
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py                      # velaris / vl 命令
│       ├── api/                        # LLM 提供商抽象
│       ├── engine/                     # 核心 agent 循环
│       ├── tools/                      # 内置工具 + 场景工具注册
│       ├── skills/                     # 技能系统
│       ├── plugins/                    # 插件系统
│       ├── permissions/                # 权限管理
│       ├── hooks/                      # 生命周期钩子
│       ├── memory/                     # 持久化记忆
│       ├── swarm/                      # 多 agent 协调
│       ├── tasks/                      # 后台任务
│       ├── coordinator/                # agent 编排
│       ├── config/                     # 配置管理
│       ├── services/                   # 跨切面服务
│       ├── prompts/                    # 系统提示词
│       ├── ui/                         # UI 后端
│       ├── bridge/                     # 前后端桥接
│       ├── types/                      # 公共类型
│       ├── utils/                      # 工具函数
│       └── scenarios/                  # ★ 新增: 产品场景
│           ├── __init__.py
│           ├── travel/                 # 商旅AI助手
│           │   ├── __init__.py
│           │   ├── types.py
│           │   ├── tools/
│           │   │   ├── __init__.py
│           │   │   ├── parse_intent.py
│           │   │   ├── search_flights.py
│           │   │   ├── search_hotels.py
│           │   │   └── recommend.py
│           │   └── skills/
│           │       ├── travel-compare.md
│           │       ├── travel-budget.md
│           │       └── travel-itinerary.md
│           ├── tokencost/              # AI TokenCost
│           │   ├── __init__.py
│           │   ├── types.py
│           │   ├── data/
│           │   │   └── model_prices.py
│           │   ├── tools/
│           │   │   ├── __init__.py
│           │   │   ├── analyze_usage.py
│           │   │   ├── model_compare.py
│           │   │   └── optimize_suggest.py
│           │   └── skills/
│           │       ├── cost-audit.md
│           │       └── model-routing.md
│           └── openclaw/               # 车端运行环境
│               ├── __init__.py
│               ├── types.py
│               ├── protocol/
│               │   ├── __init__.py
│               │   ├── intent_order.py
│               │   ├── service_proposal.py
│               │   └── transaction_contract.py
│               ├── dispatch/
│               │   ├── __init__.py
│               │   ├── dispatcher.py
│               │   └── scorer.py
│               ├── agents/
│               │   ├── __init__.py
│               │   ├── vehicle_agent.py
│               │   └── user_agent.py
│               ├── governance/
│               │   └── permissions.py
│               ├── tools/
│               │   ├── __init__.py
│               │   ├── match_vehicles.py
│               │   ├── calculate_route.py
│               │   ├── score_proposals.py
│               │   └── form_contract.py
│               └── skills/
│                   ├── ride-dispatch.md
│                   └── service-negotiation.md
├── tests/
│   ├── ...                             # (原有 60 个测试文件)
│   └── test_scenarios/                 # ★ 新增: 场景测试
│       ├── test_travel/
│       ├── test_tokencost/
│       └── test_openclaw/
├── scripts/
│   ├── ...                             # (原有 9 个 E2E 脚本)
│   ├── e2e_travel.py                   # 商旅 E2E
│   ├── e2e_tokencost.py                # TokenCost E2E
│   └── e2e_openclaw.py                 # OpenClaw E2E
└── frontend/
    └── terminal/                       # React/Ink 终端 UI
```

---

## 3. 场景一: 商旅AI助手

### 3.1 核心流程

```
用户输入 (自然语言, 中文)
  │  "下周三去上海出差, 预算3000, 要直飞"
  │
  ▼
TravelIntentParseTool (LLM 辅助)
  │  -> TravelSearchIntent { departure: "北京", destination: "上海",
  │       date: "2026-04-09", budget_max: 3000, direct_only: true }
  │
  ▼
[并行] FlightSearchTool + HotelSearchTool
  │  直接调用 flight-compare service 层:
  │    - Ctrip (携程)
  │    - Qunar (去哪儿)
  │    - Trip.com
  │    - Fliggy (飞猪) [实验性]
  │    - Meituan (美团) [实验性]
  │
  ▼
TravelRecommendTool (LLM 辅助)
  │  -> 三档推荐:
  │     - 最省: 携程经济舱 ¥680 + 如家 ¥298
  │     - 舒适: 去哪儿商务舱 ¥1580 + 全季 ¥488
  │     - 最优: 携程经济舱 ¥680 + 全季 ¥488 (性价比最高)
  │  -> 建议: "周三早班机更便宜, 建议7:00出发..."
  │
  ▼
Agent 自然语言输出给用户
```

### 3.2 数据模型

```python
# scenarios/travel/types.py

from pydantic import BaseModel, Field
from enum import Enum

class TravelSearchRequest(BaseModel):
    """商旅搜索请求"""
    query: str                                    # 自然语言查询
    departure: str | None = None                  # 出发城市
    destination: str | None = None                # 目的城市
    date: str | None = None                       # 出发日期 (YYYY-MM-DD)
    return_date: str | None = None                # 返回日期
    budget_max: float | None = None               # 预算上限 (CNY)
    preferences: TravelPreferences | None = None  # 偏好设置

class TravelPreferences(BaseModel):
    """出行偏好"""
    direct_only: bool = False                     # 仅直飞
    hotel_star_min: int = 3                       # 最低星级
    time_window: str | None = None                # "morning" / "afternoon" / "evening"
    cabin_class: str = "economy"                  # economy / business / first
    hotel_distance_km: float | None = None        # 距目的地最大距离

class FlightOption(BaseModel):
    """机票选项"""
    provider: str                                 # 渠道 (ctrip/qunar/fliggy/meituan/trip)
    airline: str                                  # 航空公司
    flight_no: str                                # 航班号
    departure_time: str                           # 起飞时间
    arrival_time: str                             # 到达时间
    duration_minutes: int                         # 飞行时长
    price: float                                  # 价格 (CNY)
    cabin_class: str                              # 舱位
    stops: int = 0                                # 经停次数
    baggage: str | None = None                    # 行李额

class HotelOption(BaseModel):
    """酒店选项"""
    provider: str                                 # 渠道
    name: str                                     # 酒店名
    star_rating: int                              # 星级
    price_per_night: float                        # 每晚价格
    distance_km: float | None = None              # 距目的地距离
    score: float | None = None                    # 评分
    address: str | None = None                    # 地址

class TravelOption(BaseModel):
    """组合出行方案"""
    flight: FlightOption | None = None
    hotel: HotelOption | None = None
    total_price: float
    score: float                                  # 综合评分 0-1
    tags: list[str] = []                          # ["最省", "舒适", "最优"]

class TravelRecommendation(BaseModel):
    """最终推荐结果"""
    cheapest: TravelOption                        # 最省方案
    comfort: TravelOption                         # 舒适方案
    best_overall: TravelOption                    # 综合最优
    all_options: list[TravelOption]               # 所有可选方案
    advice: str                                   # 自然语言建议
    search_meta: SearchMeta                       # 搜索元数据

class SearchMeta(BaseModel):
    """搜索元数据"""
    total_flights: int
    total_hotels: int
    providers_searched: list[str]
    search_duration_ms: int
```

### 3.3 工具实现

#### TravelIntentParseTool

```python
# scenarios/travel/tools/parse_intent.py

class TravelIntentParseInput(BaseModel):
    query: str = Field(description="用户的自然语言旅行查询")

class TravelIntentParseTool(BaseTool):
    name = "travel_intent_parse"
    description = "解析自然语言旅行查询为结构化搜索意图"
    input_model = TravelIntentParseInput

    async def execute(self, args, context) -> ToolResult:
        # 调用 LLM 解析意图
        # 返回 TravelSearchRequest JSON
        ...

    def is_read_only(self, args) -> bool:
        return True
```

#### FlightSearchTool

```python
# scenarios/travel/tools/search_flights.py

class FlightSearchTool(BaseTool):
    name = "flight_search"
    description = "在多个平台搜索机票并聚合结果"
    input_model = FlightSearchInput

    def __init__(self, compare_service: CompareService):
        self._service = compare_service

    async def execute(self, args, context) -> ToolResult:
        # 直接调用 flight-compare 的 CompareService
        intent = TravelSearchIntent(
            departure_city=args.departure,
            destination_city=args.destination,
            departure_date=args.date,
        )
        results = await self._service.search_flights(intent)
        return ToolResult(output=json.dumps([r.model_dump() for r in results]))
```

### 3.4 与 flight-compare 集成方式

**直接代码级集成** (同 Python, 无 HTTP 开销):

```python
# 在 pyproject.toml 中添加:
# dependencies = [..., "flight-compare @ file:///Users/apus/flight-compare"]

# 或通过 sys.path:
import sys
sys.path.insert(0, "/Users/apus/flight-compare")
from app.services.compare_service import CompareService
from app.models import TravelSearchIntent, SearchOption
```

**支持的渠道** (继承 flight-compare):

| 渠道 | 类型 | 状态 |
|------|------|------|
| 携程 (Ctrip) | 机票+酒店 | 稳定 |
| 去哪儿 (Qunar) | 机票+酒店 | 稳定 |
| Trip.com | 机票+酒店 | 稳定 |
| 飞猪 (Fliggy) | 机票+酒店 | 实验性 |
| 美团 (Meituan) | 酒店 | 实验性 |

---

## 4. 场景二: AI TokenCost

### 4.1 核心流程

```
用户输入
  │  "分析我上个月的 OpenAI API 用量, 给出降本建议"
  │  (附带 usage.json 或 API key)
  │
  ▼
UsageAnalyzeTool (纯计算)
  │  -> 成本分布:
  │     - gpt-4o: $45.20 (60%)
  │     - gpt-4o-mini: $12.30 (16%)
  │     - text-embedding: $2.10 (3%)
  │  -> 浪费指标:
  │     - 重复调用: 23%
  │     - 过长 prompt: 15%
  │     - 低利用率模型: gpt-4o 用于简单分类任务
  │
  ▼
ModelCompareTool (LLM 辅助)
  │  -> 替代方案矩阵:
  │     | 当前 | 替代 | 成本节省 | 质量影响 |
  │     | gpt-4o | gpt-4.1-mini | -80% | -5% |
  │     | gpt-4o | deepseek-v3 | -89% | -8% |
  │
  ▼
OptimizeSuggestTool (LLM 辅助)
  │  -> 优化建议:
  │     1. [高优] 分类任务切换到 gpt-4.1-nano, 月省 $30
  │     2. [中优] 添加 prompt 缓存, 月省 $15
  │     3. [低优] 批量请求合并, 月省 $5
  │
  ▼
Agent 自然语言输出给用户
```

### 4.2 数据模型

```python
# scenarios/tokencost/types.py

class ApiUsageRecord(BaseModel):
    """单次 API 调用记录"""
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float | None = None       # 如已知
    task_type: str | None = None        # "chat", "embedding", "completion"
    latency_ms: int | None = None

class UsageAnalysis(BaseModel):
    """用量分析结果"""
    total_cost_usd: float
    total_tokens: int
    by_model: dict[str, ModelUsageSummary]
    by_task_type: dict[str, float]
    top_expensive_calls: list[ApiUsageRecord]
    waste_indicators: list[WasteIndicator]
    period: str                          # "2026-03", "last_30_days"

class WasteIndicator(BaseModel):
    """浪费指标"""
    type: str                            # "repeated_calls", "long_prompts", "wrong_model"
    description: str
    estimated_waste_usd: float
    affected_calls: int

class ModelPricing(BaseModel):
    """模型定价"""
    input_per_1m: float                  # 每百万输入 token 价格 (USD)
    output_per_1m: float                 # 每百万输出 token 价格 (USD)
    context_window: int | None = None
    provider: str | None = None

class ModelComparison(BaseModel):
    """模型对比结果"""
    current_model: str
    alternatives: list[AlternativeModel]

class AlternativeModel(BaseModel):
    """替代模型"""
    model: str
    cost_saving_percent: float
    quality_impact: str                  # "negligible", "minor", "moderate", "significant"
    latency_change: str                  # "faster", "similar", "slower"
    recommended_for: list[str]           # 推荐的任务类型

class OptimizationSuggestion(BaseModel):
    """优化建议"""
    priority: str                        # "high", "medium", "low"
    type: str                            # "model_switch", "prompt_cache", "batch", "reduce_tokens"
    description: str
    estimated_saving_usd: float
    quality_impact: str
    effort: str                          # "low", "medium", "high"
    implementation: str                  # 具体实施步骤
```

### 4.3 模型定价数据库

```python
# scenarios/tokencost/data/model_prices.py

MODEL_PRICES: dict[str, ModelPricing] = {
    # OpenAI
    "gpt-4o":          ModelPricing(input_per_1m=2.50, output_per_1m=10.00, context_window=128000, provider="openai"),
    "gpt-4o-mini":     ModelPricing(input_per_1m=0.15, output_per_1m=0.60,  context_window=128000, provider="openai"),
    "gpt-4.1":         ModelPricing(input_per_1m=2.00, output_per_1m=8.00,  context_window=1047576, provider="openai"),
    "gpt-4.1-mini":    ModelPricing(input_per_1m=0.40, output_per_1m=1.60,  context_window=1047576, provider="openai"),
    "gpt-4.1-nano":    ModelPricing(input_per_1m=0.10, output_per_1m=0.40,  context_window=1047576, provider="openai"),
    "o3-mini":         ModelPricing(input_per_1m=1.10, output_per_1m=4.40,  context_window=200000, provider="openai"),
    "o4-mini":         ModelPricing(input_per_1m=1.10, output_per_1m=4.40,  context_window=200000, provider="openai"),

    # Anthropic
    "claude-opus-4":   ModelPricing(input_per_1m=15.00, output_per_1m=75.00, context_window=200000, provider="anthropic"),
    "claude-sonnet-4": ModelPricing(input_per_1m=3.00,  output_per_1m=15.00, context_window=200000, provider="anthropic"),
    "claude-haiku-3.5":ModelPricing(input_per_1m=0.80,  output_per_1m=4.00,  context_window=200000, provider="anthropic"),

    # Google
    "gemini-2.5-pro":  ModelPricing(input_per_1m=1.25,  output_per_1m=10.00, context_window=1048576, provider="google"),
    "gemini-2.0-flash":ModelPricing(input_per_1m=0.10,  output_per_1m=0.40,  context_window=1048576, provider="google"),

    # DeepSeek
    "deepseek-v3":     ModelPricing(input_per_1m=0.27,  output_per_1m=1.10,  context_window=128000, provider="deepseek"),
    "deepseek-r1":     ModelPricing(input_per_1m=0.55,  output_per_1m=2.19,  context_window=128000, provider="deepseek"),
}
```

---

## 5. 场景三: OpenClaw 车端运行环境

### 5.1 核心定位

OpenClaw **不是自动驾驶系统**, 而是车内服务编排层 (Vehicle Agent Runtime):

```
┌──────────────────────────────────────────────────────┐
│                    OpenClaw Runtime                    │
│                                                       │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │ 服务编排  │  │ 工具调用  │  │ 权限边界  │  │ 记忆管理││
│  │ Service  │  │ Tool     │  │ Permission│  │ Memory ││
│  │ Orch.    │  │ Calling  │  │ Boundary  │  │ Mgmt.  ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘│
│       └──────────────┼──────────────┼───────────-┘     │
│                      ▼                                 │
│              ┌──────────────┐                          │
│              │ 收益结算引擎  │                          │
│              │ Revenue      │                          │
│              │ Settlement   │                          │
│              └──────────────┘                          │
└──────────────────────────────────────────────────────┘
```

### 5.2 三段式派单协议

#### Stage 1: IntentOrder (用户 agent -> 意图订单)

从"我要一辆车"升级为"任务请求":

```python
# scenarios/openclaw/protocol/intent_order.py

class Location(BaseModel):
    lat: float
    lng: float
    name: str

class TimeRequirements(BaseModel):
    earliest: datetime
    latest: datetime | None = None
    flexibility: Literal["exact", "flexible_15m", "flexible_30m", "flexible_1h"] = "flexible_15m"

class ServicePreferences(BaseModel):
    vehicle_type: Literal["economy", "comfort", "premium", "accessible"] | None = None
    driver_style: Literal["quiet", "social", "professional"] | None = None
    carpool_willing: bool = False
    environment: list[str] = []          # ["quiet", "music_ok", "smoke_free"]

class Budget(BaseModel):
    max_price: float
    currency: str = "CNY"
    surge_acceptable: bool = False       # 是否接受溢价

class PrivacyLevel(str, Enum):
    STANDARD = "standard"                # 标准
    ENHANCED = "enhanced"                # 增强 (不记录行程详情)
    MAXIMUM = "maximum"                  # 最高 (端到端加密)

class TripConstraints(BaseModel):
    luggage: int = 0                     # 行李件数
    children: int = 0                    # 儿童人数
    elderly: int = 0                     # 老人人数
    wheelchair: bool = False             # 轮椅需求
    pets: bool = False                   # 宠物

class EnterpriseIdentity(BaseModel):
    company_id: str | None = None
    reimbursement_code: str | None = None
    cost_center: str | None = None
    travel_policy: str | None = None     # 差旅政策等级

class IntentOrder(BaseModel):
    """意图订单 - 用户 agent 发出的结构化任务请求"""
    order_id: str
    user_id: str
    origin: Location
    destination: Location
    time_requirements: TimeRequirements
    service_preferences: ServicePreferences = ServicePreferences()
    budget: Budget
    privacy_level: PrivacyLevel = PrivacyLevel.STANDARD
    constraints: TripConstraints = TripConstraints()
    enterprise_identity: EnterpriseIdentity | None = None
    additional_services: list[str] = []  # ["wifi", "charger", "water", "snack"]
    created_at: datetime
```

#### Stage 2: ServiceProposal (车端 agent -> 服务提案)

从"抢单"升级为"服务投标":

```python
# scenarios/openclaw/protocol/service_proposal.py

class ETA(BaseModel):
    minutes: float
    confidence: float = Field(ge=0, le=1)  # 置信度

class PricingItem(BaseModel):
    type: str                             # "base", "distance", "time", "surge", "addon"
    description: str
    amount: float

class Pricing(BaseModel):
    base_price: float
    surcharges: list[PricingItem] = []
    total_price: float
    currency: str = "CNY"

class DriverProfile(BaseModel):
    driver_id: str
    rating: float = Field(ge=0, le=5)
    completed_trips: int
    style: str                            # "quiet", "social", "professional"
    languages: list[str] = ["zh"]
    years_experience: int | None = None

class VehicleProfile(BaseModel):
    model: str                            # "Tesla Model 3", "BYD Han"
    year: int
    capacity: int                         # 乘客容量
    features: list[str] = []              # ["ev", "autopilot", "air_purifier", "wifi"]
    license_plate: str | None = None

class AddOnService(BaseModel):
    service_id: str
    name: str
    price: float
    description: str

class CommitmentBoundaries(BaseModel):
    max_wait_minutes: int
    cancellation_policy: str              # "free_5min", "charge_after_3min"
    risk_notes: list[str] = []            # 风险说明

class ServiceProposal(BaseModel):
    """服务提案 - 车端 agent 返回的结构化投标"""
    proposal_id: str
    vehicle_id: str
    order_id: str
    eta: ETA
    pricing: Pricing
    driver: DriverProfile
    vehicle: VehicleProfile
    add_on_services: list[AddOnService] = []
    task_understanding_score: float = Field(ge=0, le=1)  # 任务理解程度
    historical_fulfillment_score: float = Field(ge=0, le=1)  # 历史履约分
    commitment_boundaries: CommitmentBoundaries
    created_at: datetime
```

#### Stage 3: TransactionContract (协议化成交)

从"黑箱匹配"升级为"可审计契约":

```python
# scenarios/openclaw/protocol/transaction_contract.py

class PriceComposition(BaseModel):
    base: float
    surcharges: list[PricingItem]
    add_ons: list[PricingItem]
    total: float
    currency: str = "CNY"

class DataPermissions(BaseModel):
    location_sharing: Literal["trip_only", "session", "none"] = "trip_only"
    ad_authorization: Literal["none", "non_intrusive", "full"] = "none"
    data_retention: str = "30_days"       # 数据保留期

class WaitRules(BaseModel):
    free_wait_minutes: int = 5
    charge_per_minute: float = 1.0

class BreachClause(BaseModel):
    party: Literal["user", "driver", "platform"]
    condition: str                        # 违约条件描述
    penalty: str                          # 处罚描述

class ProfitSharing(BaseModel):
    driver_percent: float                 # 司机分成比例
    platform_percent: float               # 平台分成比例
    ecosystem_percent: float = 0          # 生态商家分成

class ReviewMechanism(BaseModel):
    appeal_window: str = "24h"            # 申诉窗口
    arbitration_method: str = "platform"  # 仲裁方式
    rating_mutual: bool = True            # 双向评价

class Signatures(BaseModel):
    user_signed_at: datetime | None = None
    vehicle_signed_at: datetime | None = None
    platform_witnessed_at: datetime | None = None

class TransactionContract(BaseModel):
    """可审计交易合约"""
    contract_id: str
    order_id: str
    proposal_id: str
    price_composition: PriceComposition
    service_scope: list[str]             # 服务范围
    data_permissions: DataPermissions
    wait_rules: WaitRules
    breach_clauses: list[BreachClause]
    add_on_profit_sharing: ProfitSharing
    review_mechanism: ReviewMechanism
    signatures: Signatures
    status: Literal["draft", "signed", "active", "completed", "disputed", "cancelled"]
    created_at: datetime
```

### 5.3 调度引擎

```python
# scenarios/openclaw/dispatch/dispatcher.py

class ScoredProposal(BaseModel):
    proposal: ServiceProposal
    score: float                          # 综合评分 0-1
    score_breakdown: dict[str, float]     # 各维度得分

class DispatchResult(BaseModel):
    order: IntentOrder
    proposals_received: int
    winning_proposal: ScoredProposal
    contract: TransactionContract
    dispatch_duration_ms: int

class DispatchEngine:
    """三段式派单调度引擎"""

    SCORING_WEIGHTS = {
        "price": 0.25,
        "eta": 0.25,
        "task_fit": 0.20,
        "reliability": 0.15,
        "add_on_value": 0.15,
    }

    def __init__(self, vehicle_registry: VehicleRegistry):
        self._vehicles = vehicle_registry

    async def submit_intent(self, order: IntentOrder) -> str:
        """Stage 1: 广播意图订单到所有匹配车辆"""
        ...

    async def collect_proposals(
        self, order_id: str, timeout: float = 30.0
    ) -> list[ServiceProposal]:
        """Stage 2: 收集车端 agent 的服务提案"""
        ...

    async def evaluate_proposals(
        self, proposals: list[ServiceProposal], order: IntentOrder
    ) -> list[ScoredProposal]:
        """评分排序: price * 0.25 + eta * 0.25 + task_fit * 0.20 + ..."""
        ...

    async def form_contract(
        self, order: IntentOrder, proposal: ServiceProposal
    ) -> TransactionContract:
        """Stage 3: 生成可审计合约"""
        ...

    async def full_dispatch(self, order: IntentOrder) -> DispatchResult:
        """完整三段式流程"""
        order_id = await self.submit_intent(order)
        proposals = await self.collect_proposals(order_id)
        scored = await self.evaluate_proposals(proposals, order)
        contract = await self.form_contract(order, scored[0].proposal)
        return DispatchResult(
            order=order,
            proposals_received=len(proposals),
            winning_proposal=scored[0],
            contract=contract,
            dispatch_duration_ms=...,
        )
```

### 5.4 评分算法

```python
# scenarios/openclaw/dispatch/scorer.py

class ProposalScorer:
    """多维提案评分器"""

    def score_price(self, proposal: ServiceProposal, order: IntentOrder) -> float:
        """价格得分: 越接近预算下限越高, 超出预算为 0"""
        ratio = proposal.pricing.total_price / order.budget.max_price
        if ratio > 1.0:
            return 0.0
        return 1.0 - ratio  # 越便宜分越高

    def score_eta(self, proposal: ServiceProposal) -> float:
        """ETA 得分: 5分钟内满分, 超过30分钟为0"""
        minutes = proposal.eta.minutes
        if minutes <= 5:
            return 1.0
        if minutes >= 30:
            return 0.0
        return (30 - minutes) / 25

    def score_task_fit(self, proposal: ServiceProposal, order: IntentOrder) -> float:
        """任务匹配度: 基于 task_understanding_score + 约束满足"""
        base = proposal.task_understanding_score
        # 检查约束: 行李/儿童/轮椅
        if order.constraints.wheelchair and "accessible" not in proposal.vehicle.features:
            return 0.0
        if order.constraints.luggage > 0 and proposal.vehicle.capacity < 4:
            base *= 0.8
        return base

    def score_reliability(self, proposal: ServiceProposal) -> float:
        """可靠性: 基于历史履约分"""
        return proposal.historical_fulfillment_score

    def score_add_on_value(self, proposal: ServiceProposal, order: IntentOrder) -> float:
        """附加服务价值: 匹配用户请求的附加服务"""
        if not order.additional_services:
            return 0.5  # 无需求时给中间分
        matched = sum(
            1 for s in order.additional_services
            if any(a.name == s for a in proposal.add_on_services)
        )
        return matched / len(order.additional_services)
```

### 5.5 车端 Agent

```python
# scenarios/openclaw/agents/vehicle_agent.py

class VehicleCapabilities(BaseModel):
    """车辆能力描述"""
    vehicle_id: str
    vehicle_profile: VehicleProfile
    driver_profile: DriverProfile
    current_location: Location
    available: bool = True
    add_on_services: list[AddOnService] = []
    operating_area: list[str] = []       # 运营区域

class VehicleAgent:
    """车端智能体 - 接收 IntentOrder, 评估能力, 生成 ServiceProposal"""

    def __init__(self, capabilities: VehicleCapabilities):
        self._cap = capabilities

    async def evaluate_order(self, order: IntentOrder) -> ServiceProposal | None:
        """评估是否能接单, 生成服务提案"""
        # 1. 检查基本可用性
        if not self._cap.available:
            return None

        # 2. 计算 ETA
        distance = self._calculate_distance(self._cap.current_location, order.origin)
        eta_minutes = distance / 0.5  # 简化: 假设 0.5km/min

        # 3. 计算价格
        trip_distance = self._calculate_distance(order.origin, order.destination)
        base_price = trip_distance * 2.5  # 简化: 2.5 CNY/km

        # 4. 评估任务理解度
        task_score = self._assess_task_understanding(order)

        # 5. 生成提案
        return ServiceProposal(
            proposal_id=generate_id(),
            vehicle_id=self._cap.vehicle_id,
            order_id=order.order_id,
            eta=ETA(minutes=eta_minutes, confidence=0.85),
            pricing=Pricing(base_price=base_price, total_price=base_price),
            driver=self._cap.driver_profile,
            vehicle=self._cap.vehicle_profile,
            add_on_services=self._match_add_ons(order),
            task_understanding_score=task_score,
            historical_fulfillment_score=self._cap.driver_profile.rating / 5.0,
            commitment_boundaries=CommitmentBoundaries(
                max_wait_minutes=10,
                cancellation_policy="free_5min",
            ),
            created_at=datetime.now(),
        )
```

---

## 6. 品牌重命名清单

### 6.1 全量替换

| 原始 | 替换为 | 涉及范围 |
|------|--------|----------|
| `openharness` | `velaris` | 所有 Python import, 目录名, 包名 |
| `OpenHarness` | `Velaris` | 类名, docstring, README |
| `OPENHARNESS_` | `VELARIS_` | 环境变量 |
| `~/.openharness/` | `~/.velaris/` | 配置目录 |
| `.openharness/` | `.velaris/` | 项目级配置 |
| `oh` (CLI) | `vl` | CLI 快捷命令 |
| `openharness` (CLI) | `velaris` | CLI 完整命令 |

### 6.2 不需要改的

- Anthropic SDK import (保持 `from anthropic import ...`)
- React/Ink 前端代码 (独立, 通过 IPC 通信)
- 测试框架 (pytest 配置不变)
- CI/CD workflow (仅改触发路径)

---

## 7. 实施计划

### Phase 0: 品牌重命名 + 初始化 (2h)

| 步骤 | 内容 | 预计时间 |
|------|------|----------|
| 0.1 | `src/openharness/` -> `src/velaris/` 目录重命名 | 5min |
| 0.2 | 全量替换 import 路径和字符串引用 | 30min |
| 0.3 | 更新 `pyproject.toml` (包名, CLI 入口) | 10min |
| 0.4 | 更新配置路径 (`config/paths.py`) | 15min |
| 0.5 | 创建 `scenarios/` 目录结构 | 10min |
| 0.6 | 配置 flight-compare 集成 | 15min |
| 0.7 | 运行测试确认重命名无破坏 | 15min |
| 0.8 | 更新 README.md | 20min |

### Phase 1: 商旅AI助手 (3h)

| 步骤 | 内容 | 预计时间 |
|------|------|----------|
| 1.1 | 数据模型 (`types.py`) | 30min |
| 1.2 | TravelIntentParseTool | 30min |
| 1.3 | FlightSearchTool + HotelSearchTool | 45min |
| 1.4 | TravelRecommendTool | 30min |
| 1.5 | Skills (3 个 markdown) | 20min |
| 1.6 | 注册到 ToolRegistry | 15min |
| 1.7 | 测试 | 30min |

### Phase 2: AI TokenCost (3h)

| 步骤 | 内容 | 预计时间 |
|------|------|----------|
| 2.1 | 数据模型 + 定价库 | 30min |
| 2.2 | UsageAnalyzeTool | 45min |
| 2.3 | ModelCompareTool | 30min |
| 2.4 | OptimizeSuggestTool | 30min |
| 2.5 | Skills (2 个 markdown) | 15min |
| 2.6 | 注册 + 测试 | 30min |

### Phase 3: OpenClaw (4h)

| 步骤 | 内容 | 预计时间 |
|------|------|----------|
| 3.1 | 三段式协议 Pydantic 模型 | 45min |
| 3.2 | 调度引擎 + 评分器 | 60min |
| 3.3 | VehicleAgent + UserAgent | 45min |
| 3.4 | 4 个 Tools | 30min |
| 3.5 | 车端权限 | 20min |
| 3.6 | Skills (2 个 markdown) | 15min |
| 3.7 | 测试 | 30min |

### Phase 4: 集成 + 文档 (2h)

| 步骤 | 内容 | 预计时间 |
|------|------|----------|
| 4.1 | ScenarioSettings 配置 | 20min |
| 4.2 | Plugin 化包装 | 30min |
| 4.3 | E2E 测试脚本 | 30min |
| 4.4 | 文档 (3 个场景指南) | 40min |

---

## 8. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| flight-compare import 路径兼容 | 中 | 中 | 添加 sys.path 或 pyproject extras |
| OpenHarness 重命名遗漏 | 低 | 低 | grep -r 全量搜索, 测试覆盖 |
| LLM 调用成本 (E2E测试) | 中 | 低 | Mock LLM 用于单元测试, 真实 LLM 仅 E2E |
| OpenClaw 无真实车辆 | 确定 | 低 | 仿真优先, VehicleAgent 为进程内模拟 |
| Playwright 依赖 (flight-compare) | 中 | 中 | 可选依赖, 无 Playwright 时降级为 HTTP mock |

---

## 9. 验证标准

| 检查项 | 命令 | 标准 |
|--------|------|------|
| Lint | `uv run ruff check src tests` | 0 errors |
| 类型 | `uv run mypy src/velaris` | 0 errors |
| 单元测试 | `uv run pytest tests/ -q` | 全部通过 |
| 场景测试 | `uv run pytest tests/test_scenarios/ -q` | 全部通过 |
| E2E | `uv run python scripts/e2e_travel.py` | 通过 |
| CLI | `velaris --help` | 正常输出 |
