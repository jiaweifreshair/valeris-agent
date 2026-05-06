"""SQLite 版决策记忆。

该实现严格复用 `DecisionMemory` 的查询语义：
- 完整记录落到 `decision_records.payload_json`；
- 最近优先扫描通过 `created_at` 排序实现（跟随写入顺序）；
- 不依赖 SQLite JSON1，所有过滤与解析在 Python 层完成。
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from velaris_agent.memory.decision_memory import (
    DecisionMemory,
    build_decision_index_entry,
    deserialize_decision_record,
    serialize_decision_record,
)
from velaris_agent.memory.types import DecisionRecord
from velaris_agent.persistence.sqlite import sqlite_connection


def _dump_json(payload: dict[str, Any]) -> str:
    """把 payload 序列化为 JSON 字符串。"""

    return json.dumps(payload, ensure_ascii=False)


def _load_json(value: Any) -> dict[str, Any] | None:
    """把 SQLite 返回的 JSON 字符串还原为字典。"""

    if value in (None, ""):
        return None
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, (bytes, bytearray)):
        text = value.decode("utf-8", errors="ignore")
    else:
        text = str(value)
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(loaded, dict):
        return dict(loaded)
    return None


class SqliteDecisionMemory(DecisionMemory):
    """把决策记录持久化到 SQLite 的最小后端。"""

    def __init__(
        self,
        database_path: str | Path,
        base_dir: str | Path | None = None,
    ) -> None:
        """初始化 SQLite 决策记忆。

        Args:
            database_path: SQLite 数据库文件路径
            base_dir: 与 `DecisionMemory` 兼容的参数；SQLite 后端不使用该目录，但保留签名便于迁移期复用。
        """

        self._database_path = str(database_path)
        self._base_dir = Path(base_dir) if base_dir is not None else None
        # 父类 DecisionMemory.recall_similar 依赖此属性
        self._semantic_engine = None

    def save(self, record: DecisionRecord) -> str:
        """把决策记录写入 SQLite，并返回决策 ID。"""

        payload = serialize_decision_record(record)
        created_at = datetime.now(timezone.utc).isoformat()
        with sqlite_connection(self._database_path) as connection:
            connection.execute(
                """
                insert into decision_records (record_id, created_at, payload_json)
                values (?, ?, ?)
                on conflict (record_id) do update set
                  created_at = excluded.created_at,
                  payload_json = excluded.payload_json
                """,
                (record.decision_id, created_at, _dump_json(payload)),
            )
        return record.decision_id

    def get(self, decision_id: str) -> DecisionRecord | None:
        """按 ID 读取完整决策记录。"""

        with sqlite_connection(self._database_path) as connection:
            row = connection.execute(
                """
                select payload_json
                from decision_records
                where record_id = ?
                """,
                (decision_id,),
            ).fetchone()
        if row is None:
            return None
        payload = _load_json(row[0])
        if payload is None:
            return None
        return deserialize_decision_record(payload)

    def update_feedback(
        self,
        decision_id: str,
        user_choice: dict[str, Any] | None = None,
        user_feedback: float | None = None,
        outcome_notes: str | None = None,
    ) -> DecisionRecord | None:
        """回填用户选择和满意度，并把更新后的 payload 重新写入数据库。"""

        record = self.get(decision_id)
        if record is None:
            return None

        updates: dict[str, Any] = {}
        if user_choice is not None:
            updates["user_choice"] = user_choice
        if user_feedback is not None:
            updates["user_feedback"] = user_feedback
        if outcome_notes is not None:
            updates["outcome_notes"] = outcome_notes

        updated = record.model_copy(update=updates)
        with sqlite_connection(self._database_path) as connection:
            connection.execute(
                """
                update decision_records
                set payload_json = ?
                where record_id = ?
                """,
                (_dump_json(serialize_decision_record(updated)), decision_id),
            )
        return updated

    def _scan_index_reversed(self) -> list[dict[str, Any]]:
        """从 SQLite 读取最近优先的轻量索引视图。"""

        rows: list[dict[str, Any]] = []
        with sqlite_connection(self._database_path) as connection:
            for row in connection.execute(
                """
                select payload_json
                from decision_records
                order by created_at desc, record_id desc
                """
            ).fetchall():
                payload = _load_json(row[0])
                if payload is None:
                    continue
                record = deserialize_decision_record(payload)
                rows.append(build_decision_index_entry(record))
        return rows
