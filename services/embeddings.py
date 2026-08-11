import requests

from core.config import HF_API_TOKEN

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
# Same model as before, now called via HF's hosted Inference API instead of
# loading it locally — the local model pulled in torch/transformers (800MB+),
# which doesn't fit the free-tier host's RAM/build-size limits.
API_URL = f"https://router.huggingface.co/hf-inference/models/{MODEL_NAME}/pipeline/feature-extraction"


def embed_texts(texts):
  # texts: list[str] — a batch of strings, e.g. [c["text"] for c in chunks].
  # Pass all chunks in one call rather than looping embed_text() per chunk,
  # so it's one HTTP round trip instead of many.
  response = requests.post(
    API_URL,
    headers={"Authorization": f"Bearer {HF_API_TOKEN}"},
    json={"inputs": texts, "options": {"wait_for_model": True}},
  )
  response.raise_for_status()
  return response.json()


def embed_text(text):
  return embed_texts([text])[0]
