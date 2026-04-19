"""Velaris 业务闭环执行工具。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from velaris_agent.velaris.orchestrator import VelarisBizOrchestrator
from velaris_agent.velaris.execution_contract import DecisionExecutionRequest


class BizExecuteToolInput(BaseModel):
    """业务闭环执行工具入参。"""

    query: str = Field(description="业务查询或目标描述")
    payload: dict[str, Any] = Field(default_factory=dict, description="业务负载")
    scenario: str | None = Field(default=None, description="可选：显式指定场景")
    constraints: dict[str, Any] = Field(default_factory=dict, description="业务约束")
    session_id: str | None = Field(default=None, description="可选：显式指定会话 ID")


class BizExecuteTool(BaseTool):
    """执行 Velaris 路由治理闭环。"""

    name = "biz_execute"
    description = "Execute a full Velaris business flow with routing, authority, task ledger, and outcome recording."
    input_model = BizExecuteToolInput

    def is_read_only(self, arguments: BizExecuteToolInput) -> bool:
        del arguments
        # biz_execute 会写入 task/outcome/audit/session 等运行时记录，因此不能标记为只读。
        return False

    async def execute(self, arguments: BizExecuteToolInput, context: ToolExecutionContext) -> ToolResult:
        orchestrator = context.metadata.get("velaris_orchestrator")
        if not isinstance(orchestrator, VelarisBizOrchestrator):
            orchestrator = VelarisBizOrchestrator(cwd=context.cwd)

        try:
            payload = orchestrator.execute_request(
                DecisionExecutionRequest(
                    query=arguments.query,
                    payload=arguments.payload,
                    constraints=arguments.constraints,
                    scenario_hint=arguments.scenario,
                    session_id=arguments.session_id,
                )
            )
        except RuntimeError as exc:
            error_payload = exc.args[0] if exc.args and isinstance(exc.args[0], dict) else {"error": str(exc)}
            return ToolResult(
                output=json.dumps(error_payload, ensure_ascii=False, sort_keys=True),
                is_error=True,
            )
        return ToolResult(output=json.dumps(payload, ensure_ascii=False, sort_keys=True))
