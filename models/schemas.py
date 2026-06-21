from pydantic import BaseModel

class SummarizeRequest(BaseModel):
    url: str

class SummarizeResponse(BaseModel):
    summary: str
