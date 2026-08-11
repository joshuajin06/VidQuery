from services.embeddings import embed_texts
from services.jobs import JobStatus, update_job
from services.transcript import extract_video_id, fetch_transcript_chunks
from services.vector_store import delete_video_chunks, insert_chunks

from youtube_transcript_api import CouldNotRetrieveTranscript



def run_ingest_job(job_id, url):
  """Background job: chunk a video's transcript, embed the chunks, and
  upsert them into the vector store so /chat can retrieve over them later.

  This mirrors run_summarize_job in routers/summarize.py — same
  fetch-then-update_job-per-stage shape, just ending in the vector store
  instead of an LLM summary.

  TODO: implement this function.

  Spec:
    1. update_job(job_id, status=JobStatus.FETCHING_TRANSCRIPT).
    2. video_id = extract_video_id(url).
    3. chunks = fetch_transcript_chunks(url). Wrap in the same try/except
       shape as run_summarize_job (ValueError for a bad URL,
       CouldNotRetrieveTranscript for an unavailable transcript) — on
       either, update_job(job_id, status=JobStatus.FAILED, error=...) and
       return early.
    4. update_job(job_id, status=JobStatus.EMBEDDING).
    5. Embed all chunk texts in ONE batch call — embed_texts([c["text"] for
       c in chunks]) — not one embed_text() call per chunk. embed_texts
       loads the model once and batches the encode() call, so it's
       drastically faster than embedding chunks one at a time.
    6. Attach each embedding back onto its chunk dict under the "embedding"
       key (insert_chunks expects chunks shaped like
       {"text", "start", "end", "embedding"} — see services/vector_store.py).
    7. update_job(job_id, status=JobStatus.INDEXING).
    8. delete_video_chunks(video_id) BEFORE inserting — re-ingesting the
       same video (e.g. user hits "index" twice) must not duplicate rows.
       This mirrors why routers/summarize.py always starts a fresh job
       rather than appending to a prior one.
    9. insert_chunks(video_id, chunks).
    10. update_job(job_id, status=JobStatus.DONE).

  Hints:
    - video_id is what /chat will later filter search() by, so it must be
      the same video_id both here and in the future retrieval step —
      extract_video_id(url) is the single source of truth for that, don't
      derive it any other way.
    - If chunks is empty (e.g. a transcript-less video), decide whether
      that should still count as DONE or as FAILED — there's no single
      right answer, but be deliberate about it rather than letting an
      empty insert_chunks([]) call silently "succeed" into a video with no
      searchable content.
    - init_schema() (services/vector_store.py) needs to have been called
      once at app startup before this job can run, since it depends on the
      transcript_chunks table already existing. Check main.py — if there's
      no startup hook calling it yet, that's a prerequisite gap worth
      flagging, not something to route around inside this function.
  """
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


