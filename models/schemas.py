from pydantic import BaseModel, Field

from services.jobs import JobStatus


class SummarizeRequest(BaseModel):
    url: str


class SummarizeTextRequest(BaseModel):
    transcript: str = Field(min_length=1)


class IndexRequest(BaseModel):
    url: str


class JobCreatedResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: JobStatus
    progress_current: int | None = None
    progress_total: int | None = None
    summary: str | None = None
    error: str | None = None
