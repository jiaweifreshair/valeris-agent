"""Velaris execution 列表工具。"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class BizListExecutionsToolInput(BaseModel):
    """execution 列表工具入参。"""

    limit: int = Field(default=10, ge=1, le=100, description="返回条数上限")


class BizListExecutionsTool(BaseTool):
    """按工作区列出最近的 execution 摘要。"""

    name = "biz_list_executions"
    description = "List recent Velaris executions for the current project."
    input_model = BizListExecutionsToolInput

    def is_read_only(self, arguments: BizListExecutionsToolInput) -> bool:
        del arguments
        return True

    async def execute(self, arguments: BizListExecutionsToolInput, context: ToolExecutionContext) -> ToolResult:
        try:
            from velaris_agent.velaris.execution_recall import ExecutionRecallService

            service = ExecutionRecallService(cwd=context.cwd)
            executions = service.list_executions(limit=arguments.limit)
            payload = {
                "cwd": str(context.cwd.resolve()),
                "total": len(executions),
                "executions": executions,
            }
            return ToolResult(output=json.dumps(payload, ensure_ascii=False, sort_keys=True))
        except Exception as exc:
            return ToolResult(output=f"execution 列表读取失败: {exc}", is_error=True)

