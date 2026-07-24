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
    """Runs in the background, after the POST response has already been sent.
    Same fetch -> summarize logic as before, but failures update the job
    record instead of raising HTTPException (there's no request to answer)."""
    # TODO:
    # 1. update_job(job_id, status=JobStatus.FETCHING_TRANSCRIPT)
    # 2. call fetch_transcript(url), catching ValueError and
    #    CouldNotRetrieveTranscript -- on failure, update_job(..., status=
    #    JobStatus.FAILED, error="...") and `return` (don't fall through to
    #    the summarizing step with no transcript).
    # 3. update_job(job_id, status=JobStatus.SUMMARIZING)
    # 4. call summarize_text(transcript), catching OpenAIError the same way.
    # 5. on success: update_job(job_id, status=JobStatus.DONE, summary=summary)
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

    try:
        summary = summarize_text(transcript)
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
    # TODO: look the job up with get_job(job_id). If it's None, raise
    # HTTPException(status_code=404, detail="Job not found."). Otherwise
    # turn the Job dataclass into a JobStatusResponse -- dataclasses.asdict()
    # (already imported above) converts it to a dict you can ** into the
    # response model, same trick as **fields in update_job but in reverse.
    job = get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail = "Job Not Found")
    
    return JobStatusResponse(**asdict(job))

