from fastapi import APIRouter, HTTPException
from openai import OpenAIError
from youtube_transcript_api import CouldNotRetrieveTranscript

from models.schemas import SummarizeRequest, SummarizeResponse
from services.summarizer import summarize_text
from services.transcript import fetch_transcript

router = APIRouter()


@router.post("/summarize", response_model=SummarizeResponse)
def summarize(request: SummarizeRequest):
    try:
        transcript = fetch_transcript(request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except CouldNotRetrieveTranscript:
        raise HTTPException(status_code=404, detail="No transcript is available for this video.")

    try:
        summary = summarize_text(transcript)
    except OpenAIError:
        raise HTTPException(status_code=502, detail="Summarization failed — check the API key.")

    return SummarizeResponse(summary=summary)
