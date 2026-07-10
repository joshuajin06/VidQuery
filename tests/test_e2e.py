"""True end-to-end tests: real YouTube transcript fetch + real Groq API call.

Excluded from the default run (see pytest.ini). Run explicitly with:

    pytest -m e2e

Requires a working GROQ_API_KEY in .env and network access. These can be
slow and may flake if YouTube rate-limits transcript requests.
"""
import pytest

pytestmark = pytest.mark.e2e

# Sample video previously used for manual testing of this app
KNOWN_GOOD_URL = "https://www.youtube.com/watch?v=MCdUVMBv0o0"
NONEXISTENT_VIDEO_URL = "https://www.youtube.com/watch?v=00000000000"


def test_full_pipeline_returns_real_summary(client):
    response = client.post("/summarize", json={"url": KNOWN_GOOD_URL})
    assert response.status_code == 200
    summary = response.json()["summary"]
    assert isinstance(summary, str)
    assert len(summary) > 50  # a real summary, not an empty or stub response


def test_nonexistent_video_returns_404(client):
    response = client.post("/summarize", json={"url": NONEXISTENT_VIDEO_URL})
    assert response.status_code == 404
    assert response.json()["detail"] == "No transcript is available for this video."
