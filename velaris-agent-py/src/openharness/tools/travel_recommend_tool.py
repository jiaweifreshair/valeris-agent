"""Velaris 商旅推荐工具。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from velaris_agent.adapters.travel import TravelSourceAdapter
from velaris_agent.biz.engine import run_scenario


class TravelRecommendToolInput(BaseModel):
    """商旅推荐工具入参。"""

    budget_max: float = Field(default=0, description="预算上限")
    direct_only: bool = Field(default=False, description="是否仅允许直飞")
    options: list[dict[str, Any]] = Field(default_factory=list, description="候选商旅方案")
    source: dict[str, Any] = Field(default_factory=dict, description="可选：数据源配置，支持 inline/file/http")


class TravelRecommendTool(BaseTool):
    """执行商旅方案筛选与推荐。"""

    name = "travel_recommend"
    description = "Recommend the best travel plan under budget, direct-flight, and comfort constraints."
    input_model = TravelRecommendToolInput

    def is_read_only(self, arguments: TravelRecommendToolInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: TravelRecommendToolInput, context: ToolExecutionContext) -> ToolResult:
        del context
        payload = await TravelSourceAdapter().resolve_payload(
            source=arguments.source,
            overrides={
                "budget_max": arguments.budget_max,
                "direct_only": arguments.direct_only,
                "options": arguments.options,
            },
        )
        result = run_scenario("travel", payload)
        return ToolResult(output=json.dumps(result, ensure_ascii=False, sort_keys=True))
