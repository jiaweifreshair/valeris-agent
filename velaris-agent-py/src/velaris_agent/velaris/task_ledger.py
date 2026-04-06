"""Velaris 原生任务账本。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


@dataclass
class TaskLedgerRecord:
    """任务账本记录。"""

    task_id: str
    session_id: str
    runtime: str
    role: str
    objective: str
    status: str
    depends_on: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """把任务记录转换为 JSON 友好的字典。"""
        return asdict(self)


class TaskLedger:
    """任务账本服务。"""

    def __init__(self) -> None:
        """初始化空账本。"""
        self._tasks: dict[str, TaskLedgerRecord] = {}

    def create_task(
        self,
        session_id: str,
        runtime: str,
        role: str,
        objective: str,
        depends_on: list[str] | None = None,
    ) -> TaskLedgerRecord:
        """创建一个账本任务。"""
        timestamp = datetime.now(UTC).isoformat()
        task = TaskLedgerRecord(
            task_id=f"task-{uuid4().hex[:12]}",
            session_id=session_id,
            runtime=runtime,
            role=role,
            objective=objective,
            status="queued",
            depends_on=depends_on or [],
            created_at=timestamp,
            updated_at=timestamp,
        )
        self._tasks[task.task_id] = task
        return task

    def update_status(self, task_id: str, status: str, error: str | None = None) -> TaskLedgerRecord | None:
        """更新任务状态。"""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        task.status = status
        task.error = error
        task.updated_at = datetime.now(UTC).isoformat()
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> TaskLedgerRecord | None:
        """读取单个任务。"""
        return self._tasks.get(task_id)

    def list_by_session(self, session_id: str) -> list[TaskLedgerRecord]:
        """按会话列出任务。"""
        return [task for task in self._tasks.values() if task.session_id == session_id]
