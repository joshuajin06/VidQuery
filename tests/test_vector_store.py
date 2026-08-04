import pytest

import services.vector_store as vector_store_service
from services.vector_store import (
    delete_video_chunks,
    get_connection,
    init_schema,
    insert_chunks,
    search,
)


class FakeConnection:
    """Stand-in for a psycopg connection: records every SQL statement and
    params passed to execute(), and lets tests control what's "returned"
    from a SELECT without touching a real database."""

    def __init__(self, rows=None):
        self.executed = []  # list of (sql, params)
        self.closed = False
        self._rows = rows or []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        return self._rows

    def close(self):
        self.closed = True


@pytest.fixture
def fake_conn(monkeypatch):
    conn = FakeConnection()
    monkeypatch.setattr(vector_store_service, "get_connection", lambda: conn)
    return conn


# ---- get_connection ----------------------------------------------------

def test_get_connection_connects_with_database_url_and_autocommit(monkeypatch):
    connect_calls = []

    class FakeRawConn:
        pass

    def fake_connect(url, autocommit):
        connect_calls.append((url, autocommit))
        return FakeRawConn()

    register_calls = []
    monkeypatch.setattr(vector_store_service.psycopg, "connect", fake_connect)
    monkeypatch.setattr(
        vector_store_service, "register_vector", lambda c: register_calls.append(c)
    )

    conn = get_connection()

    assert connect_calls == [(vector_store_service.DATABASE_URL, True)]
    assert len(register_calls) == 1
    assert register_calls[0] is conn


def test_get_connection_registers_vector_before_returning(monkeypatch):
    order = []

    class FakeRawConn:
        pass

    monkeypatch.setattr(
        vector_store_service.psycopg,
        "connect",
        lambda url, autocommit: (order.append("connect"), FakeRawConn())[1],
    )
    monkeypatch.setattr(
        vector_store_service, "register_vector", lambda c: order.append("register")
    )

    get_connection()

    assert order == ["connect", "register"]


# ---- init_schema ---------------------------------------------------------

def test_init_schema_creates_extension_table_and_index(fake_conn):
    init_schema()

    statements = [sql for sql, _params in fake_conn.executed]
    assert len(statements) == 3

    assert "CREATE EXTENSION IF NOT EXISTS vector" in statements[0]

    table_sql = statements[1]
    assert "CREATE TABLE IF NOT EXISTS transcript_chunks" in table_sql
    for column in (
        "id SERIAL PRIMARY KEY",
        "video_id TEXT NOT NULL",
        "text TEXT NOT NULL",
        "start_time FLOAT NOT NULL",
        "end_time FLOAT NOT NULL",
        f"embedding VECTOR({vector_store_service.EMBEDDING_DIM})",
    ):
        assert column in table_sql
    # every column must be comma-separated, not accidentally concatenated
    assert "NULLtext" not in table_sql
    assert "NULLstart_time" not in table_sql
    assert "NULLend_time" not in table_sql
    assert "NULLembedding" not in table_sql

    index_sql = statements[2]
    assert "CREATE INDEX IF NOT EXISTS transcript_chunks_embedding_idx" in index_sql
    assert "ON transcript_chunks USING ivfflat (embedding vector_cosine_ops)" in index_sql
    assert "idxON" not in index_sql  # no missing space between clauses


def test_init_schema_closes_connection(fake_conn):
    init_schema()
    assert fake_conn.closed


# ---- delete_video_chunks -------------------------------------------------

def test_delete_video_chunks_runs_parameterized_delete(fake_conn):
    delete_video_chunks("abc123")

    assert len(fake_conn.executed) == 1
    sql, params = fake_conn.executed[0]
    assert sql == "DELETE FROM transcript_chunks WHERE video_id = %s"
    assert params == ("abc123",)


def test_delete_video_chunks_does_not_inline_video_id_into_sql(fake_conn):
    delete_video_chunks("'; DROP TABLE transcript_chunks; --")

    sql, params = fake_conn.executed[0]
    # the raw value must travel as a bound param, never formatted into the SQL string
    assert "DROP TABLE" not in sql
    assert params == ("'; DROP TABLE transcript_chunks; --",)


def test_delete_video_chunks_closes_connection(fake_conn):
    delete_video_chunks("abc123")
    assert fake_conn.closed


# ---- insert_chunks --------------------------------------------------------

def test_insert_chunks_inserts_one_row_per_chunk(fake_conn):
    chunks = [
        {"text": "hello", "start": 0.0, "end": 1.5, "embedding": [0.1, 0.2]},
        {"text": "world", "start": 1.5, "end": 3.0, "embedding": [0.3, 0.4]},
    ]

    insert_chunks("video1", chunks)

    assert len(fake_conn.executed) == 2
    for (sql, params), chunk in zip(fake_conn.executed, chunks):
        assert sql.strip().startswith("INSERT INTO transcript_chunks")
        assert "VALUES (%s, %s, %s, %s, %s)" in sql
        # no missing space where the two string literals join
        assert "embedding)VALUES" not in sql
        assert params == (
            "video1",
            chunk["text"],
            chunk["start"],
            chunk["end"],
            chunk["embedding"],
        )


def test_insert_chunks_with_empty_list_executes_nothing(fake_conn):
    insert_chunks("video1", [])
    assert fake_conn.executed == []
    assert fake_conn.closed


def test_insert_chunks_closes_connection(fake_conn):
    insert_chunks("video1", [{"text": "hi", "start": 0.0, "end": 1.0, "embedding": [0.1]}])
    assert fake_conn.closed


# ---- search ----------------------------------------------------------------

def test_search_runs_parameterized_cosine_distance_query(monkeypatch):
    conn = FakeConnection(rows=[])
    monkeypatch.setattr(vector_store_service, "get_connection", lambda: conn)

    search("video1", [0.1, 0.2, 0.3], top_k=5)

    assert len(conn.executed) == 1
    sql, params = conn.executed[0]
    assert "embedding <=> %s AS distance" in sql
    assert "FROM transcript_chunks" in sql
    assert "WHERE video_id = %s" in sql
    assert "ORDER BY distance" in sql
    assert "LIMIT %s" in sql
    # guard against missing-space concatenation bugs between clauses
    assert "distanceFROM" not in sql
    assert "chunksWHERE" not in sql
    assert "%sORDER" not in sql
    assert "distanceLIMIT" not in sql
    # params must be bound in the order they appear in the SQL text
    assert params == ([0.1, 0.2, 0.3], "video1", 5)


def test_search_converts_rows_into_dicts_in_order(monkeypatch):
    rows = [
        ("first chunk", 0.0, 1.5, 0.12),
        ("second chunk", 1.5, 3.0, 0.34),
    ]
    conn = FakeConnection(rows=rows)
    monkeypatch.setattr(vector_store_service, "get_connection", lambda: conn)

    result = search("video1", [0.1, 0.2], top_k=2)

    assert result == [
        {"text": "first chunk", "start": 0.0, "end": 1.5, "distance": 0.12},
        {"text": "second chunk", "start": 1.5, "end": 3.0, "distance": 0.34},
    ]


def test_search_returns_empty_list_when_no_matches(monkeypatch):
    conn = FakeConnection(rows=[])
    monkeypatch.setattr(vector_store_service, "get_connection", lambda: conn)

    assert search("video1", [0.1], top_k=5) == []


def test_search_coerces_numeric_fields_to_float(monkeypatch):
    # simulate a driver returning Decimal-like/int values for numeric columns
    conn = FakeConnection(rows=[("chunk", 1, 2, 3)])
    monkeypatch.setattr(vector_store_service, "get_connection", lambda: conn)

    result = search("video1", [0.1], top_k=1)

    assert result == [{"text": "chunk", "start": 1.0, "end": 2.0, "distance": 3.0}]
    assert all(isinstance(v, float) for v in (result[0]["start"], result[0]["end"], result[0]["distance"]))


def test_search_closes_connection(monkeypatch):
    conn = FakeConnection(rows=[])
    monkeypatch.setattr(vector_store_service, "get_connection", lambda: conn)

    search("video1", [0.1], top_k=1)

    assert conn.closed
