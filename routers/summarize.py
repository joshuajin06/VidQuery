from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from openai import OpenAIError
from youtube_transcript_api import CouldNotRetrieveTranscript

from models.schemas import JobCreatedResponse, JobStatusResponse, SummarizeRequest
from services.jobs import JobStatus, create_job, get_job, update_job
from services.summarizer import summarize_text
from services.transcript import fetch_transcript

router = APIRouter()


def run_summarize_job(job_id: str, url: str) -> None:
    update_job(job_id, status=JobStatus.FETCHING_TRANSCRIPT)
    try:
        transcript = fetch_transcript(url)
    except ValueError as exc:
        update_job(job_id, status=JobStatus.FAILED, error=str(exc))
        return
    except CouldNotRetrieveTranscript:
        update_job(job_id, status=JobStatus.FAILED, error="Could Not Retrieve Transcript")
        return

    update_job(job_id, status=JobStatus.SUMMARIZING)

    on_progress = lambda cur, total: update_job(job_id, status=JobStatus.SUMMARIZING_CHUNK, progress_current=cur, progress_total=total)
    try:
        summary = summarize_text(transcript, on_progress)
    except OpenAIError:
        update_job(job_id, status=JobStatus.FAILED, error="Open AI Error")
        return

    update_job(job_id, status=JobStatus.DONE, summary=summary)








@router.post("/summarize", response_model=JobCreatedResponse, status_code=202)
def summarize(request: SummarizeRequest, background_tasks: BackgroundTasks):
    job = create_job()
    background_tasks.add_task(run_summarize_job, job.id, request.url)
    return JobCreatedResponse(job_id=job.id)


@router.get("/summarize/{job_id}", response_model=JobStatusResponse)
def get_summarize_status(job_id: str):
    job = get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail = "Job Not Found")
    
    return JobStatusResponse(**asdict(job))


