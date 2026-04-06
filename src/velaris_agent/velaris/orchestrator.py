"""Velaris 原生业务编排器。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from velaris_agent.biz.engine import build_capability_plan, run_scenario
from velaris_agent.velaris.authority import AuthorityService
from velaris_agent.velaris.outcome_store import OutcomeStore
from velaris_agent.velaris.router import PolicyRouter
from velaris_agent.velaris.task_ledger import TaskLedger


class VelarisBizOrchestrator:
    """Velaris 业务场景编排器。"""

    def __init__(
        self,
        router: PolicyRouter | None = None,
        authority_service: AuthorityService | None = None,
        task_ledger: TaskLedger | None = None,
        outcome_store: OutcomeStore | None = None,
    ) -> None:
        """初始化编排器及其依赖。"""
        self.router = router or PolicyRouter()
        self.authority_service = authority_service or AuthorityService()
        self.task_ledger = task_ledger or TaskLedger()
        self.outcome_store = outcome_store or OutcomeStore()

    def execute(
        self,
        query: str,
        payload: dict[str, Any],
        constraints: dict[str, Any] | None = None,
        scenario: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """执行一次完整的 Velaris 业务闭环。"""
        resolved_session_id = session_id or f"session-{uuid4().hex[:12]}"
        plan = build_capability_plan(query=query, constraints=constraints, scenario=scenario)
        routing = self.router.route(plan=plan, query=query)
        authority = self.authority_service.issue_plan(
            required_capabilities=routing.required_capabilities,
            governance=plan["governance"],
        )
        task = self.task_ledger.create_task(
            session_id=resolved_session_id,
            runtime=routing.selected_route.runtime,
            role="biz_executor",
            objective=query,
        )
        self.task_ledger.update_status(task.task_id, "running")

        try:
            scenario_result = run_scenario(plan["scenario"], payload)
        except Exception as exc:
            failed_task = self.task_ledger.update_status(task.task_id, "failed", error=str(exc))
            outcome = self.outcome_store.record(
                session_id=resolved_session_id,
                scenario=plan["scenario"],
                selected_strategy=routing.selected_strategy,
                success=False,
                reason_codes=routing.reason_codes,
                summary=str(exc),
                metrics={"error": str(exc)},
            )
            raise RuntimeError(
                {
                    "session_id": resolved_session_id,
                    "plan": plan,
                    "routing": routing.to_dict(),
                    "authority": authority.to_dict(),
                    "task": failed_task.to_dict() if failed_task is not None else task.to_dict(),
                    "outcome": outcome.to_dict(),
                }
            ) from exc

        completed_task = self.task_ledger.update_status(task.task_id, "completed") or task
        outcome = self.outcome_store.record(
            session_id=resolved_session_id,
            scenario=plan["scenario"],
            selected_strategy=routing.selected_strategy,
            success=True,
            reason_codes=routing.reason_codes,
            summary=str(scenario_result.get("summary", "执行完成")),
            metrics={
                "recommended_id": (scenario_result.get("recommended", {}) or {}).get("id"),
                "feasible": scenario_result.get("feasible"),
                "contract_ready": scenario_result.get("contract_ready"),
            },
        )
        return {
            "session_id": resolved_session_id,
            "plan": plan,
            "routing": routing.to_dict(),
            "authority": authority.to_dict(),
            "task": completed_task.to_dict(),
            "outcome": outcome.to_dict(),
            "result": scenario_result,
        }
