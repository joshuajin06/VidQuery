from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from models.schemas import IndexRequest, JobCreatedResponse, JobStatusResponse
from services.ingestion import run_ingest_job
from services.jobs import create_job, get_job

router = APIRouter()


@router.post("/index", response_model=JobCreatedResponse, status_code=202)
def index(request: IndexRequest, background_tasks: BackgroundTasks):
    job = create_job()
    background_tasks.add_task(run_ingest_job, job.id, request.url)
    return JobCreatedResponse(job_id=job.id)


@router.get("/index/{job_id}", response_model=JobStatusResponse)
def get_index_status(job_id: str):
    job = get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job Not Found")

    return JobStatusResponse(**asdict(job))
