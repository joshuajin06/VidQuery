import pytest
from openai import OpenAIError

import routers.summarize as summarize_router
from services.jobs import JobStatus, create_job, get_job

FRONTEND_ORIGIN = "http://localhost:5500"


def stub_summarizer(monkeypatch, summary="a summary"):
    monkeypatch.setattr(summarize_router, "summarize_text", lambda text, on_progress: summary)


# --- run_summarize_text_job: the worker, tested directly (no HTTP involved) ---

def test_worker_marks_job_done_with_summary(monkeypatch):
    stub_summarizer(monkeypatch, summary="the summary")
    job = create_job()

    summarize_router.run_summarize_text_job(job.id, "a pasted transcript")

    result = get_job(job.id)
    assert result.status == JobStatus.DONE
    assert result.summary == "the summary"


def test_worker_uses_given_transcript_as_summarizer_input(monkeypatch):
    monkeypatch.setattr(summarize_router, "summarize_text", lambda text, on_progress: f"summary of: {text}")
    job = create_job()

    summarize_router.run_summarize_text_job(job.id, "raw pasted text")

    assert get_job(job.id).summary == "summary of: raw pasted text"


def test_worker_reports_progress_via_on_progress(monkeypatch):
    def fake_summarize(text, on_progress):
        on_progress(1, 2)
        on_progress(2, 2)
        return "the summary"

    monkeypatch.setattr(summarize_router, "summarize_text", fake_summarize)
    job = create_job()

    summarize_router.run_summarize_text_job(job.id, "a transcript")

    result = get_job(job.id)
    assert result.status == JobStatus.DONE  # final update_job() call wins
    assert result.progress_current == 2
    assert result.progress_total == 2


def test_worker_records_summarizer_failure_as_failed(monkeypatch):
    def raise_exc(text, on_progress):
        raise OpenAIError("upstream exploded")

    monkeypatch.setattr(summarize_router, "summarize_text", raise_exc)
    job = create_job()

    summarize_router.run_summarize_text_job(job.id, "a transcript")

    assert get_job(job.id).status == JobStatus.FAILED


# --- POST /summarize/text: kicks off a job, does not wait for it ---

def test_post_returns_202_and_a_job_id(client, monkeypatch):
    stub_summarizer(monkeypatch)
    response = client.post("/summarize/text", json={"transcript": "some pasted text"})
    assert response.status_code == 202
    assert "job_id" in response.json()


def test_post_job_completes_via_background_task(client, monkeypatch):
    stub_summarizer(monkeypatch, summary="the summary")
    job_id = client.post("/summarize/text", json={"transcript": "some pasted text"}).json()["job_id"]

    result = get_job(job_id)
    assert result.status == JobStatus.DONE
    assert result.summary == "the summary"


# --- request validation ---

def test_missing_transcript_field_returns_422(client):
    response = client.post("/summarize/text", json={})
    assert response.status_code == 422


def test_empty_transcript_returns_422(client):
    response = client.post("/summarize/text", json={"transcript": ""})
    assert response.status_code == 422


def test_non_string_transcript_returns_422(client):
    response = client.post("/summarize/text", json={"transcript": 12345})
    assert response.status_code == 422


# --- GET /summarize/{job_id} works the same regardless of which POST started the job ---

def test_get_reflects_completed_text_job(client, monkeypatch):
    stub_summarizer(monkeypatch, summary="the summary")
    job_id = client.post("/summarize/text", json={"transcript": "some pasted text"}).json()["job_id"]

    response = client.get(f"/summarize/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["summary"] == "the summary"


# --- CORS ---

def test_cors_header_on_text_post(client, monkeypatch):
    stub_summarizer(monkeypatch)
    response = client.post(
        "/summarize/text", json={"transcript": "some text"}, headers={"Origin": FRONTEND_ORIGIN}
    )
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
