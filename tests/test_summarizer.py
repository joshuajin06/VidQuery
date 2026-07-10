from types import SimpleNamespace

import services.summarizer as summarizer
from services.summarizer import split_into_chunks


def fake_response(text):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))])


def capture_calls(monkeypatch, reply="a summary"):
    """Replace the OpenAI/Groq call and record the kwargs of every invocation."""
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return fake_response(reply)

    monkeypatch.setattr(summarizer.client.chat.completions, "create", fake_create)
    return calls


def shrink_limits(monkeypatch, max_chars=100, chunk_chars=60, overlap=10):
    """Lower the size thresholds so map-reduce triggers on small test inputs."""
    monkeypatch.setattr(summarizer, "MAX_TRANSCRIPT_CHARS", max_chars)
    monkeypatch.setattr(summarizer, "CHUNK_CHARS", chunk_chars)
    monkeypatch.setattr(summarizer, "CHUNK_OVERLAP_CHARS", overlap)


def system_prompt(call):
    return call["messages"][0]["content"]


def user_content(call):
    return call["messages"][1]["content"]


# --- short transcripts: single call, unchanged behavior ---

def test_short_transcript_uses_single_call(monkeypatch):
    calls = capture_calls(monkeypatch, reply="the summary")
    assert summarizer.summarize_text("some transcript") == "the summary"
    assert len(calls) == 1
    assert system_prompt(calls[0]) == summarizer.SINGLE_PASS_PROMPT


def test_sends_transcript_as_user_message(monkeypatch):
    calls = capture_calls(monkeypatch)
    summarizer.summarize_text("hello transcript")
    roles = [m["role"] for m in calls[0]["messages"]]
    assert roles == ["system", "user"]
    assert user_content(calls[0]) == "hello transcript"


def test_transcript_at_exact_limit_uses_single_call(monkeypatch):
    calls = capture_calls(monkeypatch)
    summarizer.summarize_text("x" * summarizer.MAX_TRANSCRIPT_CHARS)
    assert len(calls) == 1


def test_empty_transcript_still_calls_model(monkeypatch):
    calls = capture_calls(monkeypatch)
    summarizer.summarize_text("")
    assert user_content(calls[0]) == ""


# --- long transcripts: map-reduce ---

def make_transcript(n_words):
    """Unique numbered words so we can detect any lost content."""
    return " ".join(f"word{i:04d}" for i in range(n_words))


def test_long_transcript_triggers_map_reduce(monkeypatch):
    shrink_limits(monkeypatch)
    calls = capture_calls(monkeypatch)
    summarizer.summarize_text(make_transcript(40))  # ~360 chars > 100-char limit

    assert len(calls) > 1
    map_calls, reduce_call = calls[:-1], calls[-1]
    assert all(system_prompt(c) == summarizer.MAP_PROMPT for c in map_calls)
    assert system_prompt(reduce_call) == summarizer.REDUCE_PROMPT


def test_no_transcript_content_is_lost(monkeypatch):
    shrink_limits(monkeypatch)
    calls = capture_calls(monkeypatch)
    transcript = make_transcript(40)
    summarizer.summarize_text(transcript)

    seen_by_model = " ".join(user_content(c) for c in calls[:-1])
    for word in transcript.split():
        assert word in seen_by_model


def test_chunks_are_labeled_with_position(monkeypatch):
    shrink_limits(monkeypatch)
    calls = capture_calls(monkeypatch)
    summarizer.summarize_text(make_transcript(40))

    # Map calls run concurrently, so the recording order is nondeterministic;
    # assert every expected label exists rather than their order.
    map_calls = calls[:-1]
    n = len(map_calls)
    labels = {user_content(call).split("\n")[0] for call in map_calls}
    assert labels == {f"Part {i} of {n}:" for i in range(1, n + 1)}


def test_reduce_receives_the_part_summaries(monkeypatch):
    shrink_limits(monkeypatch)
    calls = capture_calls(monkeypatch, reply="part summary")
    result = summarizer.summarize_text(make_transcript(40))

    assert "part summary" in user_content(calls[-1])
    assert result == "part summary"  # final reply is returned as-is


def test_collapses_recursively_when_summaries_still_too_long(monkeypatch):
    shrink_limits(monkeypatch)
    # 15-char replies: round one joins ~7 of them (>100 chars), forcing a
    # second collapse round, after which the text fits and reduce runs.
    calls = capture_calls(monkeypatch, reply="s" * 15)
    summarizer.summarize_text(make_transcript(40))

    first_round_chunks = len(split_into_chunks(make_transcript(40), 60, 10))
    assert len(calls) > first_round_chunks + 1


def test_terminates_even_if_summaries_do_not_shrink(monkeypatch):
    shrink_limits(monkeypatch)
    # Pathological model: every "summary" is longer than its input chunk, so
    # collapsing can never converge. The guard should truncate and finish
    # instead of looping (and paying for API calls) forever.
    calls = capture_calls(monkeypatch, reply="s" * 200)
    result = summarizer.summarize_text(make_transcript(40))

    assert result == "s" * 200  # the reduce call's reply
    assert len(calls) < 20  # finite: one map round plus the reduce call


# --- split_into_chunks ---

def test_short_text_is_a_single_chunk():
    assert split_into_chunks("short text", 100, 10) == ["short text"]

def test_chunks_respect_max_size():
    text = make_transcript(100)
    for chunk in split_into_chunks(text, 60, 10):
        assert len(chunk) <= 60


def test_chunks_break_on_word_boundaries():
    text = make_transcript(100)
    words = set(text.split())
    for chunk in split_into_chunks(text, 60, 10):
        for word in chunk.split():
            assert word in words, f"word was cut in half: {word!r}"


def test_every_word_appears_in_some_chunk():
    text = make_transcript(100)
    combined = " ".join(split_into_chunks(text, 60, 10))
    for word in text.split():
        assert word in combined


def test_consecutive_chunks_overlap():
    chunks = split_into_chunks(make_transcript(100), 60, 10)
    assert len(chunks) > 1
    for first, second in zip(chunks, chunks[1:]):
        assert second[:5] in first


def test_text_without_spaces_still_terminates():
    chunks = split_into_chunks("x" * 250, 60, 10)
    assert "".join(c[10:] if i else c for i, c in enumerate(chunks)).startswith("x")
    assert all(len(c) <= 60 for c in chunks)
