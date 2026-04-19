"""Tests for session persistence."""

from __future__ import annotations

from pathlib import Path

from openharness.api.usage import UsageSnapshot
from openharness.config.paths import get_project_database_path
from openharness.engine.messages import ConversationMessage, TextBlock
from velaris_agent.persistence.schema import bootstrap_sqlite_schema
from openharness.services.session_storage import (
    export_session_markdown,
    get_project_session_dir,
    list_session_snapshots,
    load_session_by_id,
    load_session_snapshot,
    save_session_snapshot,
)


def test_save_and_load_session_snapshot(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    project = tmp_path / "repo"
    project.mkdir()
    database_path = get_project_database_path(project)
    bootstrap_sqlite_schema(database_path)

    sid = save_session_snapshot(
        cwd=project,
        model="claude-test",
        system_prompt="system",
        messages=[ConversationMessage(role="user", content=[TextBlock(text="hello")])],
        usage=UsageSnapshot(input_tokens=1, output_tokens=2),
    )

    assert sid
    snapshot = load_session_snapshot(project)
    assert snapshot is not None
    assert snapshot["session_id"] == sid
    assert snapshot["model"] == "claude-test"
    assert snapshot["usage"]["output_tokens"] == 2
    assert list_session_snapshots(project)[0]["session_id"] == sid
    assert load_session_by_id(project, sid) is not None

    # 旧 JSON session 文件不再写入。
    session_dir = get_project_session_dir(project)
    assert not (session_dir / "latest.json").exists()
    assert not list(session_dir.glob("session-*.json"))


def test_export_session_markdown(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("OPENHARNESS_DATA_DIR", str(tmp_path / "data"))
    project = tmp_path / "repo"
    project.mkdir()

    path = export_session_markdown(
        cwd=project,
        messages=[
            ConversationMessage(role="user", content=[TextBlock(text="hello")]),
            ConversationMessage(role="assistant", content=[TextBlock(text="world")]),
        ],
    )

    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "OpenHarness Session Transcript" in content
    assert "hello" in content
    assert "world" in content
