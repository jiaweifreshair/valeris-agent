"""SQLite 决策记忆测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from velaris_agent.memory.types import DecisionRecord
from velaris_agent.persistence.schema import bootstrap_sqlite_schema
from velaris_agent.persistence.sqlite_helpers import get_project_database_path
from velaris_agent.persistence.sqlite_memory import SqliteDecisionMemory


def _make_record(
    decision_id: str = "dec-sqlite-001",
    user_id: str = "u-sqlite",
    scenario: str = "travel",
    query: str = "北京到上海机票",
    user_choice: dict[str, Any] | None = None,
    user_feedback: float | None = None,
) -> DecisionRecord:
    """构造一条可持久化的决策记录。"""

    return DecisionRecord(
        decision_id=decision_id,
        user_id=user_id,
        scenario=scenario,
        query=query,
        intent={"origin": "北京", "destination": "上海"},
        options_discovered=[
            {"id": "opt-a", "label": "航班A", "scores": {"price": 0.8, "time": 0.6}},
            {"id": "opt-b", "label": "航班B", "scores": {"price": 0.5, "time": 0.9}},
        ],
        options_after_filter=[],
        scores=[
            {"id": "opt-a", "scores": {"price": 0.8, "time": 0.6}},
            {"id": "opt-b", "scores": {"price": 0.5, "time": 0.9}},
        ],
        weights_used={"price": 0.4, "time": 0.35, "comfort": 0.25},
        tools_called=["search_flights"],
        recommended={"id": "opt-a", "label": "航班A"},
        alternatives=[{"id": "opt-b", "label": "航班B"}],
        explanation="航班A更均衡",
        user_choice=user_choice,
        user_feedback=user_feedback,
        created_at=datetime.now(timezone.utc),
    )


def test_sqlite_decision_memory_roundtrip(tmp_path: Path) -> None:
    """SQLite 决策记忆应完成保存、读取、回填和聚合闭环。"""

    database_path = get_project_database_path(tmp_path)
    bootstrap_sqlite_schema(database_path)

    memory = SqliteDecisionMemory(database_path)
    record = _make_record(decision_id="dec-sqlite-roundtrip", query="北京 上海 机票")

    saved_id = memory.save(record)
    assert saved_id == "dec-sqlite-roundtrip"

    got = memory.get(saved_id)
    assert got is not None
    assert got.decision_id == saved_id

    updated = memory.update_feedback(
        saved_id,
        user_choice={"id": "opt-b", "label": "航班B"},
        user_feedback=4.5,
        outcome_notes="价格更合适",
    )
    assert updated is not None
    assert updated.user_choice["id"] == "opt-b"
    assert updated.user_feedback == 4.5

    listed = memory.list_by_user("u-sqlite", scenario="travel")
    assert [item.decision_id for item in listed] == [saved_id]
    assert memory.count_by_user("u-sqlite", scenario="travel") == 1

    similar = memory.recall_similar("u-sqlite", "travel", "北京 上海 机票")
    assert [item.decision_id for item in similar] == [saved_id]

    agg = memory.aggregate_outcomes("travel", option_field="id", option_value="opt-b")
    assert agg["times_seen"] == 1
    assert agg["times_chosen"] == 1
    assert agg["sample_size"] == 1
    assert agg["avg_satisfaction"] == 4.5


def test_sqlite_decision_memory_recent_order_follows_write_time(tmp_path: Path) -> None:
    """SQLite 后端的最近优先顺序应跟随写入顺序，而不是 payload.created_at。"""

    database_path = get_project_database_path(tmp_path)
    bootstrap_sqlite_schema(database_path)

    memory = SqliteDecisionMemory(database_path)

    future_record = _make_record(
        decision_id="dec-order-a",
        user_id="u-order",
        query="未来时间记录",
    ).model_copy(update={"created_at": datetime(2099, 1, 1, tzinfo=timezone.utc)})
    past_record = _make_record(
        decision_id="dec-order-b",
        user_id="u-order",
        query="过去时间记录",
    ).model_copy(update={"created_at": datetime(1999, 1, 1, tzinfo=timezone.utc)})

    memory.save(future_record)
    memory.save(past_record)

    ordered = memory.list_by_user("u-order", scenario="travel")
    assert [item.decision_id for item in ordered] == ["dec-order-b", "dec-order-a"]

    memory.update_feedback(
        "dec-order-a",
        user_choice={"id": "opt-b", "label": "航班B"},
        user_feedback=4.2,
    )
    ordered_after_feedback = memory.list_by_user("u-order", scenario="travel")
    assert [item.decision_id for item in ordered_after_feedback] == [
        "dec-order-b",
        "dec-order-a",
    ]

    memory.save(
        future_record.model_copy(
            update={
                "query": "未来时间记录-更新后",
                "created_at": datetime(1988, 1, 1, tzinfo=timezone.utc),
            }
        )
    )
    ordered_after_resave = memory.list_by_user("u-order", scenario="travel")
    assert [item.decision_id for item in ordered_after_resave] == [
        "dec-order-a",
        "dec-order-b",
    ]
    assert memory.count_by_user("u-order", scenario="travel") == 2
    assert memory.get("dec-order-a").query == "未来时间记录-更新后"
