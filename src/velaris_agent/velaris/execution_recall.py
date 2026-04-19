"""Velaris execution 召回与恢复服务。

该模块负责把“按 execution_id 回放出标准化 envelope”这件事收束到 Velaris 内部，
以保证 OpenHarness 只做薄桥接，不拥有恢复语义解释权。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from velaris_agent.persistence.factory import (
    build_audit_store,
    build_execution_repository,
    build_outcome_store,
    build_session_repository,
    build_task_ledger,
)
from velaris_agent.velaris.execution_contract import (
    AuditSummary,
    DecisionExecutionEnvelope,
    GovernanceGateDecision,
)


def _normalize_cwd(cwd: str | Path) -> str:
    """把 cwd 归一化为稳定的绝对路径字符串。"""

    return str(Path(cwd).resolve())


def _ensure_mapping(value: Any) -> dict[str, Any]:
    """将任意对象尽量转换为 dict。"""

    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "items"):
        return dict(value)
    return {}


class ExecutionRecallService:
    """按 execution_id 召回历史执行的最小服务。"""

    def __init__(
        self,
        *,
        cwd: str | Path,
        sqlite_database_path: str | Path | None = None,
    ) -> None:
        resolved_cwd = Path(cwd).resolve()
        resolved_sqlite_path: str | None = str(sqlite_database_path) if sqlite_database_path is not None else None
        if resolved_sqlite_path is None or not str(resolved_sqlite_path).strip():
            from velaris_agent.persistence.sqlite_helpers import get_project_database_path

            resolved_sqlite_path = str(get_project_database_path(resolved_cwd))

        self.cwd = resolved_cwd
        self.sqlite_database_path = resolved_sqlite_path
        self.session_repository = build_session_repository(sqlite_database_path=resolved_sqlite_path)
        self.execution_repository = build_execution_repository(sqlite_database_path=resolved_sqlite_path)
        self.task_ledger = build_task_ledger(sqlite_database_path=resolved_sqlite_path)
        self.outcome_store = build_outcome_store(sqlite_database_path=resolved_sqlite_path)
        self.audit_store = build_audit_store(sqlite_database_path=resolved_sqlite_path)

        if self.session_repository is None or self.execution_repository is None:  # pragma: no cover
            raise RuntimeError("execution/session repository unavailable")

    def list_executions(self, limit: int = 20) -> list[dict[str, Any]]:
        """按 cwd 列出最近的 execution 摘要。"""

        resolved_cwd = _normalize_cwd(self.cwd)
        items: list[dict[str, Any]] = []
        sessions = self.session_repository.list_by_cwd(resolved_cwd)
        for session in sessions:
            executions = list(self.execution_repository.list_by_session(session.session_id))
            executions.reverse()
            for execution in executions:
                items.append(
                    {
                        "execution_id": execution.execution_id,
                        "session_id": execution.session_id,
                        "scenario": execution.scenario,
                        "execution_status": execution.execution_status,
                        "gate_status": execution.gate_status,
                        "effective_risk_level": execution.effective_risk_level,
                        "degraded_mode": execution.degraded_mode,
                        "audit_status": execution.audit_status,
                        "created_at": execution.created_at,
                        "updated_at": execution.updated_at,
                        "session_summary": session.summary,
                    }
                )
                if len(items) >= limit:
                    return items
        return items

    def recall_execution(self, execution_id: str) -> dict[str, Any] | None:
        """按 execution_id 召回执行包络。"""

        execution = self.execution_repository.get(execution_id)
        if execution is None:
            return None

        snapshot_json = self.execution_repository.get_snapshot_json(execution_id)
        plan = _ensure_mapping(snapshot_json.get("plan"))
        routing = _ensure_mapping(snapshot_json.get("routing"))
        authority = _ensure_mapping(snapshot_json.get("authority"))

        gate_decision = self._resolve_gate_decision(
            execution=execution,
            plan=plan,
            authority=authority,
            snapshot_json=snapshot_json,
        )

        tasks: list[dict[str, Any]] = []
        outcome = snapshot_json.get("outcome")
        if outcome is not None and not isinstance(outcome, dict):
            outcome = None
        result = snapshot_json.get("result")
        if result is None or not isinstance(result, dict):
            result = {}

        audit_event_count = 0
        last_event: str | None = None
        session_id = execution.session_id
        if session_id and self.audit_store is not None:
            events = self.audit_store.list_by_session(session_id)
            execution_events = [
                event
                for event in events
                if str((event.payload or {}).get("execution_id", "")) == execution_id
            ]
            if not execution_events:
                # 如果一个 session 只有一个 execution，则允许用 session 级审计作为回放兜底。
                if len(self.execution_repository.list_by_session(session_id)) == 1:
                    execution_events = events
            audit_event_count = len(execution_events)
            if execution_events:
                last_event = execution_events[-1].step_name

            task_id = snapshot_json.get("task_id")
            if not task_id:
                for event in execution_events:
                    if event.step_name == "orchestrator.routed":
                        task_id = (event.payload or {}).get("task_id")
                        if task_id:
                            break
            if task_id:
                task = self.task_ledger.get_task(str(task_id))
                if task is not None:
                    tasks = [task.to_dict()]
            else:
                # 在无法确定 task_id 的情况下，仍保持“单 execution session 可回放”的最小体验。
                if len(self.execution_repository.list_by_session(session_id)) == 1:
                    tasks = [task.to_dict() for task in self.task_ledger.list_by_session(session_id)]

            if outcome is None and len(self.execution_repository.list_by_session(session_id)) == 1:
                outcomes = self.outcome_store.list_by_session(session_id)
                if outcomes:
                    outcome = outcomes[-1].to_dict()

        envelope = DecisionExecutionEnvelope(
            execution=execution,
            plan=plan,
            routing=routing,
            authority=authority,
            gate_decision=gate_decision,
            tasks=tasks,
            outcome=None if outcome is None else dict(outcome),
            result=dict(result),
            audit=AuditSummary(
                audit_required=gate_decision.requires_forced_audit,
                audit_event_count=audit_event_count,
                degraded_mode=execution.degraded_mode,
                audit_status=execution.audit_status,
                last_event=last_event,
            ),
        )
        return envelope.to_tool_payload()

    def _resolve_gate_decision(
        self,
        *,
        execution: Any,
        plan: dict[str, Any],
        authority: dict[str, Any],
        snapshot_json: dict[str, Any],
    ) -> GovernanceGateDecision:
        """尽量从持久化快照中恢复 gate_decision；缺失时用最小规则推断。"""

        gate_snapshot = snapshot_json.get("gate_decision")
        if isinstance(gate_snapshot, dict):
            try:
                return GovernanceGateDecision(
                    gate_status=str(gate_snapshot.get("gate_status", execution.gate_status)),
                    effective_risk_level=str(
                        gate_snapshot.get("effective_risk_level", execution.effective_risk_level)
                    ),
                    requires_forced_audit=bool(gate_snapshot.get("requires_forced_audit", False)),
                    degraded_mode=bool(gate_snapshot.get("degraded_mode", execution.degraded_mode)),
                    reason=str(gate_snapshot.get("reason", "")) or "restored_from_snapshot",
                )
            except Exception:
                # 回退到推断逻辑，避免 snapshot 结构变化导致召回失败。
                pass

        governance = _ensure_mapping(plan.get("governance"))
        requires_audit = bool(governance.get("requires_audit", False))
        approvals_required = bool(authority.get("approvals_required", False))

        if execution.gate_status == "denied":
            return GovernanceGateDecision(
                gate_status="denied",
                effective_risk_level=str(execution.effective_risk_level),
                requires_forced_audit=bool(requires_audit or approvals_required),
                degraded_mode=False,
                reason="scenario profile marked request as high risk",
            )
        if execution.gate_status == "degraded":
            return GovernanceGateDecision(
                gate_status="degraded",
                effective_risk_level=str(execution.effective_risk_level),
                requires_forced_audit=True,
                degraded_mode=True,
                reason="scenario profile requires audited degraded execution",
            )
        return GovernanceGateDecision(
            gate_status="allowed",
            effective_risk_level=str(execution.effective_risk_level),
            requires_forced_audit=requires_audit,
            degraded_mode=False,
            reason="safe to proceed",
        )
