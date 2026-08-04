import psycopg
from pgvector.psycopg import register_vector

from core.config import DATABASE_URL

EMBEDDING_DIM = 384  # all-MiniLM-L6-v2's output size, from services/embeddings.py


def get_connection():
  conn = psycopg.connect((DATABASE_URL), autocommit=True)
  register_vector(conn)
  return conn

def init_schema():
  conn = get_connection()

  conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
  conn.execute(
      "CREATE TABLE IF NOT EXISTS transcript_chunks ("
      "id SERIAL PRIMARY KEY, "
      "video_id TEXT NOT NULL, "
      "text TEXT NOT NULL, "
      "start_time FLOAT NOT NULL, "
      "end_time FLOAT NOT NULL, "
      f"embedding VECTOR({EMBEDDING_DIM}));"
  )

  conn.execute(
      "CREATE INDEX IF NOT EXISTS transcript_chunks_embedding_idx "
      "ON transcript_chunks USING ivfflat (embedding vector_cosine_ops);"
  )

  conn.close()


def delete_video_chunks(video_id):
  conn = get_connection()
  conn.execute("DELETE FROM transcript_chunks WHERE video_id = %s", (video_id, ))
  conn.close()


def insert_chunks(video_id, chunks):
  """Insert timestamped, embedded chunks for a video.

  Args:
    video_id: str
    chunks: list of dicts, each shaped like:
      {
        "text": str,
        "start": float,
        "end": float,
        "embedding": list[float],  # from services.embeddings.embed_text(s)
      }

  TODO: implement this function.

  Spec:
    1. Get a connection.
    2. For each chunk in chunks, run a parameterized INSERT:
         INSERT INTO transcript_chunks (video_id, text, start_time, end_time, embedding)
         VALUES (%s, %s, %s, %s, %s)
       with params (video_id, chunk["text"], chunk["start"], chunk["end"], chunk["embedding"]).
    3. Close the connection when done.

  Hints:
    - This is a straightforward loop + conn.execute(...) per chunk. Since
      get_connection() has autocommit=True, each insert lands immediately —
      no need to call conn.commit() yourself.
  """
  conn = get_connection()

  for chunk in chunks:
    conn.execute(
        "INSERT INTO transcript_chunks (video_id, text, start_time, end_time, embedding) "
        "VALUES (%s, %s, %s, %s, %s)",
        (video_id, chunk["text"], chunk["start"], chunk["end"], chunk["embedding"]),
    )

  conn.close()


def search(video_id, query_embedding, top_k=5):
  conn = get_connection()
  data = conn.execute(
      "SELECT text, start_time, end_time, embedding <=> %s AS distance "
      "FROM transcript_chunks "
      "WHERE video_id = %s "
      "ORDER BY distance "
      "LIMIT %s",
      (query_embedding, video_id, top_k),
  )
  res = []
  for t, s, e, d in data:
    res.append({"text": t, "start": float(s), "end": float(e), "distance": float(d)})

  conn.close()
  return res
