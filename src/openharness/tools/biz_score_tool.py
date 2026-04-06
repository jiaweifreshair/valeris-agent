"""Velaris 业务评分工具。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from velaris_agent.biz.engine import score_options
from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class BizScoreToolInput(BaseModel):
    """业务评分工具入参。"""

    options: list[dict[str, Any]] = Field(description="候选项列表，每项需包含 id 和 scores")
    weights: dict[str, float] = Field(description="维度权重")


class BizScoreTool(BaseTool):
    """按业务权重对候选项排序。"""

    name = "biz_score"
    description = "Score and rank business options with Velaris multi-dimensional weights."
    input_model = BizScoreToolInput

    def is_read_only(self, arguments: BizScoreToolInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: BizScoreToolInput, context: ToolExecutionContext) -> ToolResult:
        del context
        ranked = score_options(arguments.options, arguments.weights)
        return ToolResult(output=json.dumps(ranked, ensure_ascii=False, sort_keys=True))
