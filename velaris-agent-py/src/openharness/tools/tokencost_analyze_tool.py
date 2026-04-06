"""Velaris Token 成本分析工具。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from velaris_agent.adapters.tokencost import TokenCostSourceAdapter
from velaris_agent.biz.engine import run_scenario


class TokenCostAnalyzeToolInput(BaseModel):
    """Token 成本分析工具入参。"""

    current_monthly_cost: float = Field(default=0, description="当前月度成本")
    target_monthly_cost: float = Field(default=0, description="目标月度成本")
    suggestions: list[dict[str, Any]] = Field(default_factory=list, description="候选优化建议")
    source: dict[str, Any] = Field(default_factory=dict, description="可选：数据源配置，支持 inline/file/http")


class TokenCostAnalyzeTool(BaseTool):
    """执行 Token 成本优化分析。"""

    name = "tokencost_analyze"
    description = "Analyze token cost optimization suggestions and project monthly savings."
    input_model = TokenCostAnalyzeToolInput

    def is_read_only(self, arguments: TokenCostAnalyzeToolInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: TokenCostAnalyzeToolInput, context: ToolExecutionContext) -> ToolResult:
        del context
        payload = await TokenCostSourceAdapter().resolve_payload(
            source=arguments.source,
            overrides={
                "current_monthly_cost": arguments.current_monthly_cost,
                "target_monthly_cost": arguments.target_monthly_cost,
                "suggestions": arguments.suggestions,
            },
        )
        result = run_scenario("tokencost", payload)
        return ToolResult(output=json.dumps(result, ensure_ascii=False, sort_keys=True))
