import pytest
from fastapi.testclient import TestClient
from openai import OpenAIError
from youtube_transcript_api import TranscriptsDisabled, VideoUnavailable

import routers.summarize as summarize_router
from main import app

VALID_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
FRONTEND_ORIGIN = "http://localhost:5500"


def stub_services(monkeypatch, transcript="a transcript", summary="a summary"):
    monkeypatch.setattr(summarize_router, "fetch_transcript", lambda url: transcript)
    monkeypatch.setattr(summarize_router, "summarize_text", lambda text: summary)


# --- happy path ---

def test_summarize_success(client, monkeypatch):
    stub_services(monkeypatch, summary="the summary")
    response = client.post("/summarize", json={"url": VALID_URL})
    assert response.status_code == 200
    assert response.json() == {"summary": "the summary"}


def test_summary_is_built_from_fetched_transcript(client, monkeypatch):
    monkeypatch.setattr(summarize_router, "fetch_transcript", lambda url: "raw transcript")
    monkeypatch.setattr(summarize_router, "summarize_text", lambda text: f"summary of: {text}")
    response = client.post("/summarize", json={"url": VALID_URL})
    assert response.json() == {"summary": "summary of: raw transcript"}


def test_root_health_check(client):
    response = client.get("/")
    assert response.status_code == 200


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


# --- error translation ---

def test_url_without_video_id_returns_400(client, monkeypatch):
    # summarize_text must not be reached; fetch_transcript raises ValueError itself
    monkeypatch.setattr(summarize_router, "summarize_text", lambda text: pytest.fail("should not be called"))
    response = client.post("/summarize", json={"url": "https://www.youtube.com/playlist?list=PL123"})
    assert response.status_code == 400
    assert "video ID" in response.json()["detail"]


@pytest.mark.parametrize("exc", [TranscriptsDisabled("dQw4w9WgXcQ"), VideoUnavailable("dQw4w9WgXcQ")])
def test_unavailable_transcript_returns_404(client, monkeypatch, exc):
    def raise_exc(url):
        raise exc

    monkeypatch.setattr(summarize_router, "fetch_transcript", raise_exc)
    response = client.post("/summarize", json={"url": VALID_URL})
    assert response.status_code == 404
    assert response.json()["detail"] == "No transcript is available for this video."


def test_summarizer_failure_returns_502(client, monkeypatch):
    def raise_exc(text):
        raise OpenAIError("upstream exploded")

    monkeypatch.setattr(summarize_router, "fetch_transcript", lambda url: "a transcript")
    monkeypatch.setattr(summarize_router, "summarize_text", raise_exc)
    response = client.post("/summarize", json={"url": VALID_URL})
    assert response.status_code == 502


def test_unexpected_error_returns_500(monkeypatch):
    def raise_exc(url):
        raise RuntimeError("bug we did not anticipate")

    monkeypatch.setattr(summarize_router, "fetch_transcript", raise_exc)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/summarize", json={"url": VALID_URL})
    assert response.status_code == 500


# --- CORS: the original "Failed to fetch" regression ---
# The browser can only read a cross-origin response if it carries
# access-control-allow-origin, so these headers must be present on
# success AND on handled errors.

def test_cors_header_on_success(client, monkeypatch):
    stub_services(monkeypatch)
    response = client.post("/summarize", json={"url": VALID_URL}, headers={"Origin": FRONTEND_ORIGIN})
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


def test_cors_header_on_handled_error(client, monkeypatch):
    def raise_exc(url):
        raise TranscriptsDisabled("dQw4w9WgXcQ")

    monkeypatch.setattr(summarize_router, "fetch_transcript", raise_exc)
    response = client.post("/summarize", json={"url": VALID_URL}, headers={"Origin": FRONTEND_ORIGIN})
    assert response.status_code == 404
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
