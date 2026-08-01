import pytest

import services.transcript as transcript_service
from services.transcript import extract_video_id, fetch_transcript, fetch_transcript_chunks


class FakeSnippet:
    def __init__(self, text):
        self.text = text


class FakeTimedSnippet:
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration


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


# --- fetch_transcript_chunks ---

def test_single_chunk_when_under_window(monkeypatch):
    snippets = [
        FakeTimedSnippet("hello", start=0, duration=10),
        FakeTimedSnippet("world", start=10, duration=10),
    ]
    monkeypatch.setattr(transcript_service.ytt_api, "fetch", lambda video_id: snippets)

    chunks = fetch_transcript_chunks("https://www.youtube.com/watch?v=dQw4w9WgXcQ", window_seconds=45)

    assert len(chunks) == 1
    assert chunks[0] == {"text": "hello world", "start": 0, "end": 20}


def test_splits_into_multiple_chunks_once_window_exceeded(monkeypatch):
    # window=10: each 10s snippet individually pushes elapsed time to exactly
    # its own duration, which is not > 10, so nothing flushes... except each
    # snippet's own duration equals the window, so each one flushes solo.
    snippets = [
        FakeTimedSnippet("a", start=0, duration=10),
        FakeTimedSnippet("b", start=10, duration=10),
        FakeTimedSnippet("c", start=20, duration=10),
    ]
    monkeypatch.setattr(transcript_service.ytt_api, "fetch", lambda video_id: snippets)

    chunks = fetch_transcript_chunks("https://www.youtube.com/watch?v=dQw4w9WgXcQ", window_seconds=15)

    assert len(chunks) == 2
    assert chunks[0] == {"text": "a b", "start": 0, "end": 20}
    assert chunks[1] == {"text": "c", "start": 20, "end": 30}


def test_single_snippet_longer_than_window_flushes_alone(monkeypatch):
    snippets = [
        FakeTimedSnippet("a", start=0, duration=100),  # duration alone exceeds window
        FakeTimedSnippet("b", start=100, duration=5),
        FakeTimedSnippet("c", start=105, duration=5),
    ]
    monkeypatch.setattr(transcript_service.ytt_api, "fetch", lambda video_id: snippets)

    chunks = fetch_transcript_chunks("https://www.youtube.com/watch?v=dQw4w9WgXcQ", window_seconds=45)

    assert len(chunks) == 2
    assert chunks[0] == {"text": "a", "start": 0, "end": 100}
    assert chunks[1] == {"text": "b c", "start": 100, "end": 110}


def test_empty_transcript_returns_no_chunks(monkeypatch):
    monkeypatch.setattr(transcript_service.ytt_api, "fetch", lambda video_id: [])

    chunks = fetch_transcript_chunks("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert chunks == []


def test_chunks_preserve_start_and_end_timestamps(monkeypatch):
    snippets = [
        FakeTimedSnippet("intro", start=5.5, duration=2.5),
        FakeTimedSnippet("more", start=8.0, duration=3.0),
    ]
    monkeypatch.setattr(transcript_service.ytt_api, "fetch", lambda video_id: snippets)

    chunks = fetch_transcript_chunks("https://www.youtube.com/watch?v=dQw4w9WgXcQ", window_seconds=45)

    assert chunks[0]["start"] == 5.5
    assert chunks[0]["end"] == 11.0
