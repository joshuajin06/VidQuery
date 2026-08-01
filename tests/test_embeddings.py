import numpy as np
import pytest

import services.embeddings as embeddings_service
from services.embeddings import embed_text, embed_texts, get_model


class FakeModel:
    """Stand-in for SentenceTransformer: returns a deterministic vector per
    text based on its length, so tests don't need to load real weights."""

    def __init__(self):
        self.calls = []

    def encode(self, texts):
        self.calls.append(texts)
        return np.array([[float(len(t)), 0.0, 1.0] for t in texts])


@pytest.fixture(autouse=True)
def reset_model_cache(monkeypatch):
    # get_model() caches into the module-level _model global; reset it before
    # and after each test so tests don't leak state into each other.
    monkeypatch.setattr(embeddings_service, "_model", None)
    yield
    monkeypatch.setattr(embeddings_service, "_model", None)


def test_get_model_returns_same_instance_across_calls(monkeypatch):
    created = []

    def fake_constructor(name):
        created.append(name)
        return FakeModel()

    monkeypatch.setattr(embeddings_service, "SentenceTransformer", fake_constructor)

    first = get_model()
    second = get_model()

    assert first is second
    assert created == [embeddings_service.MODEL_NAME]  # only constructed once


def test_embed_texts_returns_plain_lists_not_numpy(monkeypatch):
    monkeypatch.setattr(embeddings_service, "SentenceTransformer", lambda name: FakeModel())

    result = embed_texts(["hi", "hello there"])

    assert isinstance(result, list)
    assert all(isinstance(vec, list) for vec in result)
    assert all(isinstance(x, float) for vec in result for x in vec)


def test_embed_texts_preserves_input_order_and_count(monkeypatch):
    monkeypatch.setattr(embeddings_service, "SentenceTransformer", lambda name: FakeModel())

    result = embed_texts(["a", "bb", "ccc"])

    assert len(result) == 3
    assert [vec[0] for vec in result] == [1.0, 2.0, 3.0]  # FakeModel encodes length


def test_embed_texts_uses_cached_model_not_a_new_one_each_call(monkeypatch):
    instances = []

    def fake_constructor(name):
        model = FakeModel()
        instances.append(model)
        return model

    monkeypatch.setattr(embeddings_service, "SentenceTransformer", fake_constructor)

    embed_texts(["first call"])
    embed_texts(["second call"])

    assert len(instances) == 1


def test_embed_text_returns_single_flat_vector(monkeypatch):
    monkeypatch.setattr(embeddings_service, "SentenceTransformer", lambda name: FakeModel())

    result = embed_text("hello")

    assert isinstance(result, list)
    assert all(isinstance(x, float) for x in result)


def test_embed_text_matches_embed_texts_single_element(monkeypatch):
    monkeypatch.setattr(embeddings_service, "SentenceTransformer", lambda name: FakeModel())

    assert embed_text("hello") == embed_texts(["hello"])[0]
