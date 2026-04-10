from __future__ import annotations

from threading import Lock
from typing import Any
from uuid import uuid4
from datetime import datetime, timezone

_jobs: list[dict[str, Any]] = []
_lock = Lock()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(job_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    job = {
        "id": str(uuid4()),
        "job_type": job_type,
        "status": "queued",
        "created_at": utc_now_iso(),
        "started_at": None,
        "completed_at": None,
        "payload": payload or {},
        "exports": [],
        "failures": 0,
        "logs": [],
    }
    with _lock:
        _jobs.insert(0, job)
    return job


def append_log(job_id: str, message: str) -> None:
    with _lock:
        for job in _jobs:
            if job["id"] == job_id:
                job["logs"].append({"at": utc_now_iso(), "message": message})
                return


def update_job(job_id: str, **updates: Any) -> None:
    with _lock:
        for job in _jobs:
            if job["id"] == job_id:
                job.update(updates)
                return


def get_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        for job in _jobs:
            if job["id"] == job_id:
                return job.copy()
    return None


def recent_jobs(limit: int = 10) -> list[dict[str, Any]]:
    with _lock:
        return [job.copy() for job in _jobs[:limit]]