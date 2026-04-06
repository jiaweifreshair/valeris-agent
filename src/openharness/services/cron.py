"""Local cron-style registry helpers."""

from __future__ import annotations

import json
from typing import Any

from openharness.config.paths import get_cron_registry_path


def load_cron_jobs() -> list[dict[str, Any]]:
    """Load stored cron jobs."""
    path = get_cron_registry_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def save_cron_jobs(jobs: list[dict[str, Any]]) -> None:
    """Persist cron jobs to disk."""
    path = get_cron_registry_path()
    path.write_text(json.dumps(jobs, indent=2) + "\n", encoding="utf-8")


def upsert_cron_job(job: dict[str, Any]) -> None:
    """Insert or replace one cron job."""
    jobs = [existing for existing in load_cron_jobs() if existing.get("name") != job.get("name")]
    jobs.append(job)
    jobs.sort(key=lambda item: str(item.get("name", "")))
    save_cron_jobs(jobs)


def delete_cron_job(name: str) -> bool:
    """Delete one cron job by name."""
    jobs = load_cron_jobs()
    filtered = [job for job in jobs if job.get("name") != name]
    if len(filtered) == len(jobs):
        return False
    save_cron_jobs(filtered)
    return True


def get_cron_job(name: str) -> dict[str, Any] | None:
    """Return one cron job by name."""
    for job in load_cron_jobs():
        if job.get("name") == name:
            return job
    return None
