"""Velaris 原生 Outcome 存储。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class OutcomeRecord:
    """业务执行结果记录。"""

    session_id: str
    scenario: str
    selected_strategy: str
    success: bool
    reason_codes: list[str]
    summary: str
    metrics: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """把 outcome 记录转换为 JSON 友好的字典。"""
        return asdict(self)


class OutcomeStore:
    """Outcome 存储服务。"""

    def __init__(self) -> None:
        """初始化空 outcome 存储。"""
        self._records: list[OutcomeRecord] = []

    def record(
        self,
        session_id: str,
        scenario: str,
        selected_strategy: str,
        success: bool,
        reason_codes: list[str],
        summary: str,
        metrics: dict[str, Any] | None = None,
    ) -> OutcomeRecord:
        """写入一条 outcome 记录。"""
        record = OutcomeRecord(
            session_id=session_id,
            scenario=scenario,
            selected_strategy=selected_strategy,
            success=success,
            reason_codes=reason_codes,
            summary=summary,
            metrics=metrics or {},
            created_at=datetime.now(UTC).isoformat(),
        )
        self._records.append(record)
        return record

    def list_by_session(self, session_id: str) -> list[OutcomeRecord]:
        """按会话检索 outcome。"""
        return [record for record in self._records if record.session_id == session_id]
