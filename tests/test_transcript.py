import pytest

import services.transcript as transcript_service
from services.transcript import extract_video_id, fetch_transcript


class FakeSnippet:
    def __init__(self, text):
        self.text = text


# --- extract_video_id: URLs that should work ---

@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "www.youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_extracts_id_from_standard_urls(url):
    assert extract_video_id(url) == "dQw4w9WgXcQ"


def test_extracts_id_when_other_params_follow():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s") == "dQw4w9WgXcQ"


def test_extracts_id_when_v_is_not_first_param():
    assert extract_video_id("https://www.youtube.com/watch?list=PL123&v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extracts_id_with_dash_and_underscore():
    assert extract_video_id("https://www.youtube.com/watch?v=a-b_c-d_e-f") == "a-b_c-d_e-f"


def test_repeated_v_param_uses_first():
    assert extract_video_id("https://www.youtube.com/watch?v=first_id_01&v=second_id_2") == "first_id_01"


# --- extract_video_id: URLs that should be rejected ---

@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url at all",
        "https://www.youtube.com/",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/watch?v=",  # empty value is dropped by parse_qs
        "https://www.youtube.com/playlist?list=PL123",
        "https://youtu.be/dQw4w9WgXcQ",  # short links unsupported (no v= param)
        "https://example.com/watch?video=dQw4w9WgXcQ",
    ],
)
def test_rejects_urls_without_video_id(url):
    with pytest.raises(ValueError):
        extract_video_id(url)


# --- fetch_transcript ---

def test_joins_snippet_text_with_spaces(monkeypatch):
    snippets = [FakeSnippet("hello"), FakeSnippet("world"), FakeSnippet("again")]
    monkeypatch.setattr(transcript_service.ytt_api, "fetch", lambda video_id: snippets)
    assert fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "hello world again"


def test_empty_transcript_returns_empty_string(monkeypatch):
    monkeypatch.setattr(transcript_service.ytt_api, "fetch", lambda video_id: [])
    assert fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == ""


def test_passes_extracted_id_to_api(monkeypatch):
    seen = {}

    def fake_fetch(video_id):
        seen["video_id"] = video_id
        return [FakeSnippet("x")]

    monkeypatch.setattr(transcript_service.ytt_api, "fetch", fake_fetch)
    fetch_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=99")
    assert seen["video_id"] == "dQw4w9WgXcQ"


def test_invalid_url_raises_before_any_network_call(monkeypatch):
    def explode(video_id):
        raise AssertionError("ytt_api.fetch should not be called for an invalid URL")

    monkeypatch.setattr(transcript_service.ytt_api, "fetch", explode)
    with pytest.raises(ValueError):
        fetch_transcript("https://www.youtube.com/watch")
