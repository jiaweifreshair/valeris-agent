"""Velaris execution 修复工具。"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


class BizRepairExecutionToolInput(BaseModel):
    """execution 修复工具入参。"""

    execution_id: str = Field(description="需要修复的 Velaris execution_id")


class BizRepairExecutionTool(BaseTool):
    """按 execution_id 补写审计并推进 audit_status。"""

    name = "biz_repair_execution"
    description = "Repair audit trail for a Velaris execution by execution_id."
    input_model = BizRepairExecutionToolInput

    def is_read_only(self, arguments: BizRepairExecutionToolInput) -> bool:
        del arguments
        return False

    async def execute(self, arguments: BizRepairExecutionToolInput, context: ToolExecutionContext) -> ToolResult:
        try:
            from velaris_agent.velaris.execution_repair import ExecutionRepairService

            service = ExecutionRepairService(cwd=context.cwd)
            payload = service.repair_execution(arguments.execution_id)
            return ToolResult(output=json.dumps(payload, ensure_ascii=False, sort_keys=True))
        except Exception as exc:
            return ToolResult(output=f"execution 修复失败: {exc}", is_error=True)

