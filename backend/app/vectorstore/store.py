from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class VectorMatch:
    chunk_id: str
    agent_id: str
    document_id: str
    document_name: str
    chunk_index: int
    text: str
    page_number: int | None
    sheet_name: str | None
    score: float


class SqliteVectorStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    document_name TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    page_number INTEGER,
                    sheet_name TEXT,
                    text TEXT NOT NULL,
                    embedding BLOB NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_agent ON chunks(agent_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)"
            )
            conn.commit()

    def add_chunks(
        self,
        *,
        agent_id: str,
        document_id: str,
        document_name: str,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        rows = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            rows.append(
                (
                    chunk["id"],
                    agent_id,
                    document_id,
                    document_name,
                    chunk["chunk_index"],
                    chunk.get("page_number"),
                    chunk.get("sheet_name"),
                    chunk["text"],
                    np.asarray(embedding, dtype=np.float32).tobytes(),
                )
            )
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO chunks (
                    id, agent_id, document_id, document_name, chunk_index,
                    page_number, sheet_name, text, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

    def delete_document(self, agent_id: str, document_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM chunks WHERE agent_id = ? AND document_id = ?",
                (agent_id, document_id),
            )
            conn.commit()

    def delete_agent(self, agent_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM chunks WHERE agent_id = ?", (agent_id,))
            conn.commit()

    def list_chunks(self, agent_id: str) -> list[VectorMatch]:
        """Agent összes chunkja (lexikális hibridhez), score=0."""
        matches: list[VectorMatch] = []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE agent_id = ?",
                (agent_id,),
            ).fetchall()
        for row in rows:
            matches.append(
                VectorMatch(
                    chunk_id=row["id"],
                    agent_id=row["agent_id"],
                    document_id=row["document_id"],
                    document_name=row["document_name"],
                    chunk_index=int(row["chunk_index"]),
                    text=row["text"],
                    page_number=row["page_number"],
                    sheet_name=row["sheet_name"],
                    score=0.0,
                )
            )
        return matches

    def search(
        self,
        query_embedding: list[float],
        *,
        agent_id: str,
        top_k: int,
    ) -> list[VectorMatch]:
        query = np.asarray(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query) or 1.0
        matches: list[VectorMatch] = []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE agent_id = ?",
                (agent_id,),
            ).fetchall()
        for row in rows:
            vector = np.frombuffer(row["embedding"], dtype=np.float32)
            denom = (np.linalg.norm(vector) * query_norm) or 1.0
            score = float(np.dot(vector, query) / denom)
            matches.append(
                VectorMatch(
                    chunk_id=row["id"],
                    agent_id=row["agent_id"],
                    document_id=row["document_id"],
                    document_name=row["document_name"],
                    chunk_index=int(row["chunk_index"]),
                    text=row["text"],
                    page_number=row["page_number"],
                    sheet_name=row["sheet_name"],
                    score=score,
                )
            )
        matches.sort(key=lambda item: item.score, reverse=True)
        if top_k <= 0:
            return matches
        return matches[:top_k]


_store: SqliteVectorStore | None = None


def get_vector_store() -> SqliteVectorStore:
    global _store
    if _store is None:
        from app.config import get_settings

        _store = SqliteVectorStore(get_settings().vector_db_file)
    return _store


def reset_vector_store() -> None:
    global _store
    _store = None
