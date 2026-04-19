"""Path resolution for Velaris/OpenHarness configuration and data directories.

Defaults to ``~/.velaris-agent/`` while keeping legacy OpenHarness paths
readable during migration.
"""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_BASE_DIR = ".velaris-agent"
_LEGACY_BASE_DIR = ".openharness"
_CONFIG_FILE_NAME = "settings.json"


def _first_env_value(*names: str) -> str | None:
    """Return the first non-empty environment variable value."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def _resolve_home_base_dir() -> Path:
    """Resolve the global base directory with legacy fallback."""
    env_dir = _first_env_value("VELARIS_CONFIG_DIR", "OPENHARNESS_CONFIG_DIR")
    if env_dir:
        return Path(env_dir)

    velaris_dir = Path.home() / _DEFAULT_BASE_DIR
    legacy_dir = Path.home() / _LEGACY_BASE_DIR
    if velaris_dir.exists() or not legacy_dir.exists():
        return velaris_dir
    return legacy_dir


def _resolve_project_base_dir(cwd: str | Path) -> Path:
    """Resolve the project-local base directory with legacy fallback."""
    root = Path(cwd).resolve()
    velaris_dir = root / _DEFAULT_BASE_DIR
    legacy_dir = root / _LEGACY_BASE_DIR
    if velaris_dir.exists() or not legacy_dir.exists():
        target = velaris_dir
    else:
        target = legacy_dir
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_config_dir() -> Path:
    """Return the configuration directory, creating it if needed.

    Resolution order:
    1. ``VELARIS_CONFIG_DIR``
    2. ``OPENHARNESS_CONFIG_DIR``
    3. ``~/.velaris-agent/`` or legacy ``~/.openharness/``
    """
    config_dir = _resolve_home_base_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file_path() -> Path:
    """Return the path to the main settings file."""
    return get_config_dir() / _CONFIG_FILE_NAME


def get_data_dir() -> Path:
    """Return the data directory for caches, history, etc.

    Resolution order:
    1. ``VELARIS_DATA_DIR``
    2. ``OPENHARNESS_DATA_DIR``
    3. resolved config dir + ``data/``
    """
    env_dir = _first_env_value("VELARIS_DATA_DIR", "OPENHARNESS_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir)
    else:
        data_dir = get_config_dir() / "data"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_logs_dir() -> Path:
    """Return the logs directory.

    Resolution order:
    1. ``VELARIS_LOGS_DIR``
    2. ``OPENHARNESS_LOGS_DIR``
    3. resolved config dir + ``logs/``
    """
    env_dir = _first_env_value("VELARIS_LOGS_DIR", "OPENHARNESS_LOGS_DIR")
    if env_dir:
        logs_dir = Path(env_dir)
    else:
        logs_dir = get_config_dir() / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_sessions_dir() -> Path:
    """Return the session storage directory."""
    sessions_dir = get_data_dir() / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    return sessions_dir


def get_tasks_dir() -> Path:
    """Return the background task output directory."""
    tasks_dir = get_data_dir() / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir


def get_feedback_dir() -> Path:
    """Return the feedback storage directory."""
    feedback_dir = get_data_dir() / "feedback"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    return feedback_dir


def get_feedback_log_path() -> Path:
    """Return the feedback log file path."""
    return get_feedback_dir() / "feedback.log"


def get_cron_registry_path() -> Path:
    """Return the cron registry file path."""
    return get_data_dir() / "cron_jobs.json"


def get_project_config_dir(cwd: str | Path) -> Path:
    """Return the per-project config directory with legacy fallback."""
    return _resolve_project_base_dir(cwd)


def get_project_issue_file(cwd: str | Path) -> Path:
    """Return the per-project issue context file."""
    return get_project_config_dir(cwd) / "issue.md"


def get_project_pr_comments_file(cwd: str | Path) -> Path:
    """Return the per-project PR comments context file."""
    return get_project_config_dir(cwd) / "pr_comments.md"


def get_project_database_path(cwd: str | Path) -> Path:
    """返回项目内 SQLite 数据库文件路径。

    约定：<project>/.velaris-agent/velaris.db

    注意：该函数只负责计算路径，不负责创建目录或初始化 schema；
    目录创建与 schema bootstrap 由 `velaris_agent.persistence.sqlite_connection`
    / `velaris_agent.persistence.schema.bootstrap_sqlite_schema` 统一处理。
    """

    return Path(cwd).resolve() / _DEFAULT_BASE_DIR / "velaris.db"
