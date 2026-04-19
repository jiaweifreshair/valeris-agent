"""Velaris execution 召回工具。

该工具只做薄桥接：
- 输入：execution_id
- 输出：Velaris 定义的标准化 execution envelope（含最小 alias）
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class BizRecallExecutionToolInput(BaseModel):
    """execution 召回工具入参。"""

    execution_id: str = Field(description="Velaris execution_id")


class BizRecallExecutionTool(BaseTool):
    """按 execution_id 召回历史执行包络。"""

    name = "biz_recall_execution"
    description = "Recall a Velaris execution envelope by execution_id."
    input_model = BizRecallExecutionToolInput

    def is_read_only(self, arguments: BizRecallExecutionToolInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: BizRecallExecutionToolInput, context: ToolExecutionContext) -> ToolResult:
        try:
            from velaris_agent.velaris.execution_recall import ExecutionRecallService

            service = ExecutionRecallService(cwd=context.cwd)
            payload = service.recall_execution(arguments.execution_id)
            if payload is None:
                return ToolResult(output=f"Execution not found: {arguments.execution_id}", is_error=True)
            return ToolResult(output=json.dumps(payload, ensure_ascii=False, sort_keys=True))
        except Exception as exc:
            return ToolResult(output=f"execution 召回失败: {exc}", is_error=True)

