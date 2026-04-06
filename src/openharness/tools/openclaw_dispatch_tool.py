"""Velaris OpenClaw 调度提案工具。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from velaris_agent.adapters.openclaw import OpenClawDispatchAdapter
from velaris_agent.biz.engine import run_scenario


class OpenClawDispatchToolInput(BaseModel):
    """OpenClaw 调度提案工具入参。"""

    max_budget_cny: float = Field(default=0, description="预算上限")
    proposals: list[dict[str, Any]] = Field(default_factory=list, description="候选调度提案")
    source: dict[str, Any] = Field(default_factory=dict, description="可选：数据源配置，支持 inline/file/http")


class OpenClawDispatchTool(BaseTool):
    """执行 OpenClaw 派单提案筛选与合约就绪判断。"""

    name = "openclaw_dispatch"
    description = "Score dispatch proposals, enforce safety and compliance gates, and return the best OpenClaw proposal."
    input_model = OpenClawDispatchToolInput

    def is_read_only(self, arguments: OpenClawDispatchToolInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: OpenClawDispatchToolInput, context: ToolExecutionContext) -> ToolResult:
        del context
        payload = await OpenClawDispatchAdapter().resolve_payload(
            source=arguments.source,
            overrides={
                "max_budget_cny": arguments.max_budget_cny,
                "proposals": arguments.proposals,
            },
        )
        result = run_scenario("openclaw", payload)
        return ToolResult(output=json.dumps(result, ensure_ascii=False, sort_keys=True))
