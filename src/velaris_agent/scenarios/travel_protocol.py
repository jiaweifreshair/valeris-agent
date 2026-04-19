"""商旅场景协议模型。

Velaris 的 travel 场景用于演示“自然语言 -> 候选方案 -> 推荐 -> 确认执行”的最小闭环，
因此这里定义一套对前端/工具层友好的协议化结构：

- `TravelIntentSlots`：从 query 中抽取的核心槽位（路线/预算/直飞约束等）。
- `TravelOption`：标准化候选方案，用于评分与展示。
- `TravelCompareResult`：统一输出，支持 requires_confirmation/confirm/completed 流程。

注意：这些模型是“协议层”，不等同于真实机票/酒店系统的数据结构。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TravelWorkflowStatus(str, Enum):
    """商旅对比/确认工作流状态。"""

    REQUIRES_CONFIRMATION = "requires_confirmation"
    COMPLETED = "completed"
    INVALID_CONFIRMATION = "invalid_confirmation"
    NO_MATCH = "no_match"


class TravelIntentSlots(BaseModel):
    """商旅意图槽位。"""

    query: str = Field(default="", description="用户原始自然语言请求")
    origin: str | None = Field(default=None, description="出发地")
    destination: str | None = Field(default=None, description="目的地")
    budget_max: float | None = Field(default=None, description="预算上限（元）")
    direct_only: bool = Field(default=False, description="是否只接受直飞")


class TravelOption(BaseModel):
    """标准化商旅候选项。"""

    id: str = Field(description="候选项 ID")
    label: str = Field(description="候选项标题")
    price: float = Field(ge=0, description="价格（元）")
    duration_minutes: float = Field(ge=0, description="耗时（分钟）")
    direct: bool = Field(default=False, description="是否直飞")
    comfort: float = Field(default=0.0, ge=0, le=1, description="舒适度评分（0-1）")
    total_score: float | None = Field(default=None, description="综合评分")
    score_breakdown: dict[str, float] = Field(default_factory=dict, description="评分拆解")
    supplier: str | None = Field(default=None, description="供应商/航司/OTA 标识")
    depart_at: str | None = Field(default=None, description="起飞/出发时间（可选）")
    arrive_at: str | None = Field(default=None, description="到达时间（可选）")
    reason: str | None = Field(default=None, description="简要推荐原因")
    metadata: dict[str, Any] = Field(default_factory=dict, description="原始扩展信息")


class TravelNextAction(BaseModel):
    """前端可直接消费的下一步动作。"""

    action: str = Field(description="动作类型，如 confirm_travel_option/view_all_options")
    label: str = Field(description="面向用户的动作提示文案")
    payload: dict[str, Any] = Field(default_factory=dict, description="动作需要的最小 payload")


class TravelAuditTrace(BaseModel):
    """商旅场景审计轨迹（演示级）。"""

    trace_id: str = Field(description="追踪 ID")
    source_type: str = Field(description="数据源类型")
    accepted_option_ids: list[str] = Field(default_factory=list, description="通过约束过滤的候选项 ID")
    recommended_option_id: str | None = Field(default=None, description="推荐候选项 ID")
    selected_option_id: str | None = Field(default=None, description="确认时选中的候选项 ID")
    proposal_id: str | None = Field(default=None, description="提案 ID")
    summary: str = Field(default="", description="执行摘要")
    created_at: str = Field(description="协议生成时间")


class TravelCompareResult(BaseModel):
    """统一商旅比较结果。"""

    scenario: str = Field(default="travel", description="场景标识")
    intent: str = Field(default="travel_compare", description="统一工具意图")
    status: TravelWorkflowStatus = Field(description="当前工作流状态")
    query: str = Field(default="", description="用户原始请求")
    user_id: str = Field(default="anonymous", description="用户 ID")
    session_id: str = Field(description="会话 ID")
    intent_slots: TravelIntentSlots = Field(description="解析后的意图槽位")
    options: list[TravelOption] = Field(default_factory=list, description="候选方案")
    recommended: TravelOption | None = Field(default=None, description="推荐方案")
    cheapest: dict[str, Any] | None = Field(default=None, description="最便宜方案摘要（演示用途）")
    accepted_option_ids: list[str] = Field(default_factory=list, description="通过约束过滤的候选项 ID")
    summary: str = Field(default="", description="简要摘要")
    explanation: str = Field(default="", description="推荐或失败说明")
    requires_confirmation: bool = Field(default=False, description="是否需要用户确认")
    next_actions: list[TravelNextAction] = Field(default_factory=list, description="下一步动作列表")
    proposal_id: str | None = Field(default=None, description="提案 ID")
    execution_status: str | None = Field(default=None, description="履约状态（completed 时提供）")
    external_ref: str | None = Field(default=None, description="外部履约引用（completed 时提供）")
    audit_trace: TravelAuditTrace = Field(description="审计轨迹")

