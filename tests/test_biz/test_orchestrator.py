"""Velaris 业务编排闭环测试。"""

from __future__ import annotations

from openharness.velaris.orchestrator import VelarisBizOrchestrator


def test_orchestrator_executes_tokencost_flow_with_runtime_controls():
    orchestrator = VelarisBizOrchestrator()

    result = orchestrator.execute(
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
                },
                {
                    "id": "cache-enable",
                    "title": "缓存命中",
                    "estimated_saving": 250,
                    "quality_retention": 0.97,
                    "execution_speed": 0.75,
                    "effort": "low",
                },
            ],
        },
        session_id="session-token",
    )

    assert result["plan"]["scenario"] == "tokencost"
    assert result["routing"]["selected_strategy"] == "local_closed_loop"
    assert result["authority"]["approvals_required"] is False
    assert result["task"]["status"] == "completed"
    assert result["result"]["projected_monthly_cost"] == 850
    assert result["outcome"]["success"] is True
    assert len(orchestrator.task_ledger.list_by_session("session-token")) == 1
    assert len(orchestrator.outcome_store.list_by_session("session-token")) == 1


def test_orchestrator_executes_robotclaw_flow_with_strict_governance():
    orchestrator = VelarisBizOrchestrator()

    result = orchestrator.execute(
        query="为 robotaxi 派单生成服务提案并形成交易合约",
        constraints={"requires_audit": True},
        payload={
            "max_budget_cny": 200000,
            "proposals": [
                {
                    "id": "dispatch-a",
                    "price_cny": 180000,
                    "eta_minutes": 22,
                    "safety_score": 0.95,
                    "compliance_score": 0.95,
                    "available": True,
                },
                {
                    "id": "dispatch-b",
                    "price_cny": 100000,
                    "eta_minutes": 18,
                    "safety_score": 0.68,
                    "compliance_score": 0.82,
                    "available": True,
                },
            ],
        },
        session_id="session-robotclaw",
    )

    assert result["plan"]["scenario"] == "robotclaw"
    assert result["routing"]["selected_strategy"] == "delegated_robotclaw"
    assert result["authority"]["approvals_required"] is True
    assert "audit" in result["authority"]["required_capabilities"]
    assert result["result"]["recommended"]["id"] == "dispatch-a"
    assert result["task"]["status"] == "completed"
    assert result["outcome"]["reason_codes"][0] == "R001_high_risk_go_robotclaw"
