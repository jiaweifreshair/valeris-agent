"""execution 修复与补审计测试。"""

from __future__ import annotations

from pathlib import Path

from velaris_agent.velaris.execution_repair import ExecutionRepairService
from velaris_agent.velaris.orchestrator import VelarisBizOrchestrator


def test_execution_repair_service_backfills_missing_audit_events(tmp_path: Path) -> None:
    """当 execution 处于 failed/pending audit_status 时，应可通过 repair 补写最小审计并推进状态。"""

    class BrokenAuditStore:
        def append_event(
            self,
            session_id: str,
            step_name: str,
            operator_id: str,
            payload: dict[str, object] | None = None,
        ) -> None:
            raise RuntimeError(f"audit down: {step_name}")

    orchestrator = VelarisBizOrchestrator(audit_store=BrokenAuditStore(), cwd=tmp_path)

    executed = orchestrator.execute(
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
        session_id="session-exec-repair",
    )

    execution_id = str(executed["envelope"]["execution"]["execution_id"])
    stored_before = orchestrator.execution_repository.get(execution_id)
    assert stored_before is not None
    assert stored_before.audit_status == "failed"

    repair = ExecutionRepairService(cwd=tmp_path)
    result = repair.repair_execution(execution_id)

    assert result["audit_status_before"] == "failed"
    assert result["audit_status_after"] == "persisted"
    assert result["events_appended"] >= 1

    stored_after = orchestrator.execution_repository.get(execution_id)
    assert stored_after is not None
    assert stored_after.audit_status == "persisted"


def test_execution_repair_is_idempotent_when_audit_is_already_persisted(tmp_path: Path) -> None:
    orchestrator = VelarisBizOrchestrator(cwd=tmp_path)
    executed = orchestrator.execute(
        query="我每月 OpenAI 成本 2000 美元，想降到 800",
        constraints={"target_monthly_cost": 800},
        payload={
            "current_monthly_cost": 2000,
            "target_monthly_cost": 800,
            "suggestions": [
                {
                    "id": "switch-tier",
                    "title": "分层路由",
                    "estimated_saving": 900,
                    "quality_retention": 0.88,
                    "execution_speed": 0.9,
                    "effort": "medium",
                }
            ],
        },
        session_id="session-exec-repair-idempotent",
    )

    execution_id = str(executed["envelope"]["execution"]["execution_id"])
    stored = orchestrator.execution_repository.get(execution_id)
    assert stored is not None
    assert stored.audit_status in {"persisted", "not_required"}

    repair = ExecutionRepairService(cwd=tmp_path)
    result = repair.repair_execution(execution_id)

    assert result["repaired"] is False
    assert result["events_appended"] == 0

