import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    FETCHING_TRANSCRIPT = "fetching_transcript"
    SUMMARIZING = "summarizing"
    SUMMARIZING_CHUNK = "summarizing_chunk"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    id: str
    status: JobStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    progress_current: int | None = None
    progress_total: int | None = None
    summary: str | None = None
    error: str | None = None


_jobs: dict[str, Job] = {}
_lock = threading.Lock()


def create_job() -> Job:
    new_job = Job(str(uuid.uuid4()), JobStatus.PENDING)
    with _lock:
        _jobs[new_job.id] = new_job
    return new_job


def get_job(job_id: str) -> Job | None:
    with _lock:
        job = _jobs.get(job_id)
    return job


def update_job(job_id: str, **fields) -> None:
    with _lock:
        job = _jobs[job_id]
        for key, value in fields.items():
            setattr(job, key, value)
