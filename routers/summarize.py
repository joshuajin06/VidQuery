from fastapi import APIRouter, HTTPException
from models.schemas import SummarizeRequest, SummarizeResponse

router = APIRouter()

@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(request: SummarizeRequest):
    url = request.url

    # TODO: replace with real transcript fetch
    transcript = f"[transcript for {url}]"

    # TODO: replace with real summarizer call
    summary = f"[summary of transcript for {url}]"

    return SummarizeResponse(summary=summary)
