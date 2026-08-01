from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"

_model = None


def get_model():
  global _model
  if _model is None:
    _model = SentenceTransformer(MODEL_NAME)

  return _model


def embed_texts(texts):
  model = get_model()
  return model.encode(texts).tolist()


def embed_text(text):
  return embed_texts([text])[0]
