"""execution 修复工具测试。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from velaris_agent.velaris.orchestrator import VelarisBizOrchestrator


class BrokenAuditStore:
    """用于构造审计写入失败场景的最小假仓储。"""

    def append_event(
        self,
        session_id: str,
        step_name: str,
        operator_id: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        """模拟审计存储不可用，稳定触发 repair 路径。"""

        del session_id, step_name, operator_id, payload
        raise RuntimeError("audit down")


@pytest.mark.asyncio
async def test_biz_repair_execution_tool_repairs_failed_execution(tmp_path: Path) -> None:
    """biz_repair_execution 应能把 failed audit_status 的 execution 推进到 persisted。"""

    orchestrator = VelarisBizOrchestrator(audit_store=BrokenAuditStore(), cwd=tmp_path)
    created = orchestrator.execute(
        query="我收到了两个 offer，一个薪资更高，一个成长更强，帮我做人生目标决策",
        payload={
            "domain": "career",
            "risk_tolerance": "moderate",
            "constraints": ["一年内希望带团队", "不希望长期 996"],
            "options": [
                {
                    "id": "offer-a",
                    "label": "Offer A：高薪成熟岗",
                    "dimensions": {
                        "growth": 0.56,
                        "income": 0.93,
                        "fulfillment": 0.61,
                        "stability": 0.82,
                        "balance": 0.38,
                    },
                },
                {
                    "id": "offer-b",
                    "label": "Offer B：成长型核心岗",
                    "dimensions": {
                        "growth": 0.95,
                        "income": 0.71,
                        "fulfillment": 0.9,
                        "stability": 0.68,
                        "balance": 0.79,
                    },
                },
            ],
        },
        session_id="session-exec-repair-tool",
    )

    execution_id = str(created["envelope"]["execution"]["execution_id"])
    stored_before = orchestrator.execution_repository.get(execution_id)
    assert stored_before is not None
    assert stored_before.audit_status == "failed"

    registry = create_default_tool_registry()
    context = ToolExecutionContext(cwd=tmp_path, metadata={"tool_registry": registry})
    repair_tool = registry.get("biz_repair_execution")
    assert repair_tool is not None

    repaired = await repair_tool.execute(
        repair_tool.input_model(execution_id=execution_id),
        context,
    )

    assert repaired.is_error is False
    repaired_payload = json.loads(repaired.output)
    assert repaired_payload["audit_status_before"] == "failed"
    assert repaired_payload["audit_status_after"] == "persisted"
    assert repaired_payload["events_appended"] >= 1

