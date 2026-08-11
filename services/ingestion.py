from services.embeddings import embed_texts
from services.jobs import JobStatus, update_job
from services.transcript import extract_video_id, fetch_transcript_chunks
from services.vector_store import delete_video_chunks, insert_chunks

from youtube_transcript_api import CouldNotRetrieveTranscript



def run_ingest_job(job_id, url):
  update_job(job_id, status=JobStatus.FETCHING_TRANSCRIPT)

  try:
    chunks = fetch_transcript_chunks(url)
    if len(chunks) == 0:
      update_job(job_id, status=JobStatus.FAILED, error="No Transcript Found")
      return
  except ValueError as exc:
    update_job(job_id, status=JobStatus.FAILED, error=str(exc))
    return
  except CouldNotRetrieveTranscript:
    update_job(job_id, status=JobStatus.FAILED, error="Could Not Retrieve Transcript")
    return

  update_job(job_id, status=JobStatus.EMBEDDING)
  embedded_txt = embed_texts([c["text"] for c in chunks])
  for embedding, chunk in zip(embedded_txt, chunks):
    chunk["embedding"] = embedding

  update_job(job_id, status=JobStatus.INDEXING)
  video_id = extract_video_id(url)
  delete_video_chunks(video_id)
  insert_chunks(video_id, chunks)

  update_job(job_id, status=JobStatus.DONE)


