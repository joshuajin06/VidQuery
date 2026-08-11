import pytest

import services.embeddings as embeddings_service
from services.embeddings import embed_text, embed_texts


class FakeResponse:
    """Stand-in for requests.Response: returns a deterministic vector per
    text based on its length, so tests don't need to hit the real HF API."""

    def __init__(self, texts):
        self._texts = texts

    def raise_for_status(self):
        pass

    def json(self):
        return [[float(len(t)), 0.0, 1.0] for t in self._texts]


def fake_post(captured_calls):
    def post(url, headers, json):
        captured_calls.append(json["inputs"])
        return FakeResponse(json["inputs"])

    return post


def test_embed_texts_returns_plain_lists(monkeypatch):
    monkeypatch.setattr(embeddings_service.requests, "post", fake_post([]))

    result = embed_texts(["hi", "hello there"])

    assert isinstance(result, list)
    assert all(isinstance(vec, list) for vec in result)
    assert all(isinstance(x, float) for vec in result for x in vec)


def test_embed_texts_preserves_input_order_and_count(monkeypatch):
    monkeypatch.setattr(embeddings_service.requests, "post", fake_post([]))

    result = embed_texts(["a", "bb", "ccc"])

    assert len(result) == 3
    assert [vec[0] for vec in result] == [1.0, 2.0, 3.0]  # length-based fake vector


def test_embed_texts_sends_all_inputs_in_one_request(monkeypatch):
    calls = []
    monkeypatch.setattr(embeddings_service.requests, "post", fake_post(calls))

    embed_texts(["first", "second"])

    assert calls == [["first", "second"]]


def test_embed_text_returns_single_flat_vector(monkeypatch):
    monkeypatch.setattr(embeddings_service.requests, "post", fake_post([]))

    result = embed_text("hello")

    assert isinstance(result, list)
    assert all(isinstance(x, float) for x in result)


def test_embed_text_matches_embed_texts_single_element(monkeypatch):
    monkeypatch.setattr(embeddings_service.requests, "post", fake_post([]))

    assert embed_text("hello") == embed_texts(["hello"])[0]


def test_embed_texts_raises_on_http_error(monkeypatch):
    class FailingResponse(FakeResponse):
        def raise_for_status(self):
            raise Exception("HF API error")

    monkeypatch.setattr(
        embeddings_service.requests,
        "post",
        lambda url, headers, json: FailingResponse(json["inputs"]),
    )

    with pytest.raises(Exception):
        embed_texts(["hi"])
