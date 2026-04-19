"""execution 召回与恢复测试。"""

from __future__ import annotations

from pathlib import Path

from velaris_agent.velaris.execution_recall import ExecutionRecallService
from velaris_agent.velaris.orchestrator import VelarisBizOrchestrator


def test_execution_recall_service_can_roundtrip_completed_execution(tmp_path: Path) -> None:
    """完成态 execution 必须可按 execution_id 召回出 envelope。"""

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
    )

    execution_id = str(executed["envelope"]["execution"]["execution_id"])
    recall = ExecutionRecallService(cwd=tmp_path)
    recalled = recall.recall_execution(execution_id)

    assert recalled is not None
    assert set(recalled.keys()) == {"audit_event_count", "envelope", "outcome", "result", "session_id"}
    assert recalled["envelope"]["execution"]["execution_id"] == execution_id
    assert recalled["envelope"]["execution"]["execution_status"] == "completed"
    assert recalled["envelope"]["plan"]["scenario"] == "tokencost"
    assert recalled["outcome"]["success"] is True
    assert recalled["audit_event_count"] >= 1


def test_execution_recall_service_lists_executions_by_cwd(tmp_path: Path) -> None:
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
    )

    execution_id = str(executed["envelope"]["execution"]["execution_id"])
    recall = ExecutionRecallService(cwd=tmp_path)
    items = recall.list_executions(limit=10)

    assert any(item.get("execution_id") == execution_id for item in items)


def test_execution_recall_service_returns_none_for_unknown_execution(tmp_path: Path) -> None:
    recall = ExecutionRecallService(cwd=tmp_path)
    assert recall.recall_execution("exec-missing") is None

