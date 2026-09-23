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

    def list_documents(self, agent_id: str) -> list[tuple[str, str]]:
        """(document_id, document_name) párok az agenthez."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT document_id, document_name
                FROM chunks
                WHERE agent_id = ?
                GROUP BY document_id, document_name
                ORDER BY document_name
                """,
                (agent_id,),
            ).fetchall()
        return [(str(row["document_id"]), str(row["document_name"])) for row in rows]

    def list_chunks(self, agent_id: str) -> list[VectorMatch]:
        """Agent összes chunkja (lexikális hibridhez), score=0."""
        matches: list[VectorMatch] = []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM chunks WHERE agent_id = ?",
                (agent_id,),
            ).fetchall()
        for row in rows:
            matches.append(self._row_to_match(row, score=0.0))
        return matches

    def get_chunks_by_indices(
        self,
        *,
        agent_id: str,
        document_id: str,
        indices: list[int],
    ) -> list[VectorMatch]:
        """Adott dokumentum megadott chunk_index értékei — szomszéd-kiterjesztéshez."""
        unique = sorted({int(i) for i in indices if i >= 0})
        if not unique:
            return []
        placeholders = ",".join("?" for _ in unique)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM chunks
                WHERE agent_id = ? AND document_id = ?
                  AND chunk_index IN ({placeholders})
                ORDER BY chunk_index
                """,
                (agent_id, document_id, *unique),
            ).fetchall()
        return [self._row_to_match(row, score=0.0) for row in rows]

    def search_text(
        self,
        *,
        agent_id: str,
        terms: list[str],
        limit: int = 200,
        document_ids: list[str] | None = None,
    ) -> list[VectorMatch]:
        """Gyors lexikális előszűrés SQL LIKE-kal — nem tölti be az összes embeddinget."""
        cleaned = [t.strip().lower() for t in terms if t and len(t.strip()) >= 3][:8]
        if not cleaned:
            return []
        clauses: list[str] = []
        params: list[object] = [agent_id]
        for term in cleaned:
            like = f"%{term}%"
            clauses.append("(lower(document_name) LIKE ? OR lower(text) LIKE ?)")
            params.extend([like, like])
        where = " OR ".join(clauses)
        sql = f"SELECT * FROM chunks WHERE agent_id = ? AND ({where})"
        if document_ids:
            placeholders = ",".join("?" for _ in document_ids)
            sql += f" AND document_id IN ({placeholders})"
            params.extend(document_ids)
        sql += " LIMIT ?"
        params.append(max(1, int(limit)))
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._row_to_match(row, score=0.45) for row in rows]

    def _row_to_match(self, row: sqlite3.Row, *, score: float) -> VectorMatch:
        return VectorMatch(
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

    def search(
        self,
        query_embedding: list[float],
        *,
        agent_id: str,
        top_k: int,
        document_ids: list[str] | None = None,
    ) -> list[VectorMatch]:
        query = np.asarray(query_embedding, dtype=np.float32)
        query_norm = float(np.linalg.norm(query) or 1.0)
        params: list[object] = [agent_id]
        sql = "SELECT * FROM chunks WHERE agent_id = ?"
        if document_ids:
            unique_docs = list(dict.fromkeys(document_ids))
            if not unique_docs:
                return []
            placeholders = ",".join("?" for _ in unique_docs)
            sql += f" AND document_id IN ({placeholders})"
            params.extend(unique_docs)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        if not rows:
            return []

        matrix = np.vstack(
            [np.frombuffer(row["embedding"], dtype=np.float32) for row in rows]
        )
        denom = (np.linalg.norm(matrix, axis=1) * query_norm) + 1e-12
        scores = (matrix @ query) / denom

        if top_k <= 0 or top_k >= len(rows):
            order = np.argsort(-scores)
        else:
            # Részleges rendezés nagy korpuszhoz
            k = min(int(top_k), len(rows))
            part = np.argpartition(-scores, kth=k - 1)[:k]
            order = part[np.argsort(-scores[part])]

        matches: list[VectorMatch] = []
        for idx in order:
            row = rows[int(idx)]
            matches.append(self._row_to_match(row, score=float(scores[int(idx)])))
        return matches


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
