import pytest
from openai import OpenAIError
from youtube_transcript_api import TranscriptsDisabled, VideoUnavailable

import routers.summarize as summarize_router
from services.jobs import JobStatus, create_job, get_job

VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
FRONTEND_ORIGIN = "http://localhost:5500"


def stub_services(monkeypatch, transcript="a transcript", summary="a summary"):
    monkeypatch.setattr(summarize_router, "fetch_transcript", lambda url: transcript)
    monkeypatch.setattr(summarize_router, "summarize_text", lambda text: summary)


# --- run_summarize_job: the worker, tested directly (no HTTP involved) ---

def test_worker_marks_job_done_with_summary(monkeypatch):
    stub_services(monkeypatch, summary="the summary")
    job = create_job()

    summarize_router.run_summarize_job(job.id, VALID_URL)

    result = get_job(job.id)
    assert result.status == JobStatus.DONE
    assert result.summary == "the summary"


def test_worker_uses_fetched_transcript_as_summarizer_input(monkeypatch):
    monkeypatch.setattr(summarize_router, "fetch_transcript", lambda url: "raw transcript")
    monkeypatch.setattr(summarize_router, "summarize_text", lambda text: f"summary of: {text}")
    job = create_job()

    summarize_router.run_summarize_job(job.id, VALID_URL)

    assert get_job(job.id).summary == "summary of: raw transcript"


def test_worker_records_bad_url_as_failed(monkeypatch):
    # summarize_text must never be reached: fetch_transcript raises ValueError itself
    monkeypatch.setattr(summarize_router, "summarize_text", lambda text: pytest.fail("should not be called"))
    job = create_job()

    summarize_router.run_summarize_job(job.id, "https://www.youtube.com/playlist?list=PL123")

    result = get_job(job.id)
    assert result.status == JobStatus.FAILED
    assert "video ID" in result.error


@pytest.mark.parametrize("exc", [TranscriptsDisabled("dQw4w9WgXcQ"), VideoUnavailable("dQw4w9WgXcQ")])
def test_worker_records_unavailable_transcript_as_failed(monkeypatch, exc):
    def raise_exc(url):
        raise exc

    monkeypatch.setattr(summarize_router, "fetch_transcript", raise_exc)
    job = create_job()

    summarize_router.run_summarize_job(job.id, VALID_URL)

    assert get_job(job.id).status == JobStatus.FAILED


def test_worker_records_summarizer_failure_as_failed(monkeypatch):
    def raise_exc(text):
        raise OpenAIError("upstream exploded")

    monkeypatch.setattr(summarize_router, "fetch_transcript", lambda url: "a transcript")
    monkeypatch.setattr(summarize_router, "summarize_text", raise_exc)
    job = create_job()

    summarize_router.run_summarize_job(job.id, VALID_URL)

    assert get_job(job.id).status == JobStatus.FAILED


# --- POST /summarize: kicks off a job, does not wait for it ---

def test_post_returns_202_and_a_job_id(client, monkeypatch):
    stub_services(monkeypatch)
    response = client.post("/summarize", json={"url": VALID_URL})
    assert response.status_code == 202
    assert "job_id" in response.json()


def test_post_job_completes_via_background_task(client, monkeypatch):
    # TestClient runs background tasks to completion before .post() returns,
    # so the job is already DONE by the time we get the response back.
    stub_services(monkeypatch, summary="the summary")
    job_id = client.post("/summarize", json={"url": VALID_URL}).json()["job_id"]

    result = get_job(job_id)
    assert result.status == JobStatus.DONE
    assert result.summary == "the summary"


# --- request validation (handled by FastAPI/Pydantic before our code runs) ---

def test_missing_url_field_returns_422(client):
    response = client.post("/summarize", json={})
    assert response.status_code == 422


def test_non_string_url_returns_422(client):
    response = client.post("/summarize", json={"url": 12345})
    assert response.status_code == 422


def test_malformed_json_body_returns_422(client):
    response = client.post(
        "/summarize", content="not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422


# --- GET /summarize/{job_id} ---

def test_get_unknown_job_returns_404(client):
    response = client.get("/summarize/does-not-exist")
    assert response.status_code == 404


def test_get_reflects_completed_job(client, monkeypatch):
    stub_services(monkeypatch, summary="the summary")
    job_id = client.post("/summarize", json={"url": VALID_URL}).json()["job_id"]

    response = client.get(f"/summarize/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["summary"] == "the summary"


def test_get_reflects_failed_job(client, monkeypatch):
    def raise_exc(url):
        raise TranscriptsDisabled("dQw4w9WgXcQ")

    monkeypatch.setattr(summarize_router, "fetch_transcript", raise_exc)
    job_id = client.post("/summarize", json={"url": VALID_URL}).json()["job_id"]

    response = client.get(f"/summarize/{job_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["error"]


# --- CORS: the original "Failed to fetch" regression ---
# The browser can only read a cross-origin response if it carries
# access-control-allow-origin, so these headers must be present on
# both endpoints, success and error alike.

def test_cors_header_on_post(client, monkeypatch):
    stub_services(monkeypatch)
    response = client.post("/summarize", json={"url": VALID_URL}, headers={"Origin": FRONTEND_ORIGIN})
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_cors_header_on_get(client, monkeypatch):
    stub_services(monkeypatch)
    job_id = client.post("/summarize", json={"url": VALID_URL}).json()["job_id"]
    response = client.get(f"/summarize/{job_id}", headers={"Origin": FRONTEND_ORIGIN})
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_cors_header_on_get_404(client):
    response = client.get("/summarize/does-not-exist", headers={"Origin": FRONTEND_ORIGIN})
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_cors_preflight_allows_post(client):
    response = client.options(
        "/summarize",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_root_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
