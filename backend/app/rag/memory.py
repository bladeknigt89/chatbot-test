"""Agent-szintű öntanuló retrieval memória (query-tő → dokumentum súly)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.rag.hybrid import query_topic_terms
from app.vectorstore.store import VectorMatch


class RetrievalMemory:
    """
    Agentenként elkülönített term→document_id súlyok.
    Sikeres válasz után erősödnek; routingnál bónuszt adnak.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS retrieval_hints (
                    agent_id TEXT NOT NULL,
                    term TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    PRIMARY KEY (agent_id, term, document_id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_hints_agent_term "
                "ON retrieval_hints(agent_id, term)"
            )
            conn.commit()

    def delete_agent(self, agent_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM retrieval_hints WHERE agent_id = ?", (agent_id,))
            conn.commit()

    def delete_document(self, agent_id: str, document_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM retrieval_hints WHERE agent_id = ? AND document_id = ?",
                (agent_id, document_id),
            )
            conn.commit()

    def learn_from_matches(
        self,
        *,
        agent_id: str,
        question: str,
        matches: list[VectorMatch],
        min_score: float = 0.35,
        top_n: int = 6,
    ) -> None:
        """Top találatok + kérdés-tők → súly növelés (csak ezen az agenten)."""
        terms = query_topic_terms(question)
        if not terms or not matches:
            return
        useful = [m for m in matches if float(m.score) >= min_score][:top_n]
        if not useful:
            useful = matches[: min(3, len(matches))]
        rows: list[tuple[str, str, str]] = []
        for match in useful:
            if match.agent_id != agent_id:
                continue
            for term in terms:
                rows.append((agent_id, term, match.document_id))
        if not rows:
            return
        with self._connect() as conn:
            for agent, term, doc_id in rows:
                conn.execute(
                    """
                    INSERT INTO retrieval_hints (agent_id, term, document_id, weight)
                    VALUES (?, ?, ?, 1.0)
                    ON CONFLICT(agent_id, term, document_id)
                    DO UPDATE SET weight = MIN(12.0, weight + 0.35)
                    """,
                    (agent, term, doc_id),
                )
            conn.commit()

    def document_boosts(
        self,
        *,
        agent_id: str,
        question: str,
    ) -> dict[str, float]:
        """document_id → tanult bónusz (0..~1.2), agent-szűrt."""
        terms = query_topic_terms(question)
        if not terms:
            return {}
        placeholders = ",".join("?" for _ in terms)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT document_id, SUM(weight) AS total
                FROM retrieval_hints
                WHERE agent_id = ? AND term IN ({placeholders})
                GROUP BY document_id
                """,
                (agent_id, *terms),
            ).fetchall()
        boosts: dict[str, float] = {}
        for row in rows:
            # Logaritmikus skálázás — ne uraljon egyetlen tanult dokumentum
            total = float(row["total"] or 0.0)
            boosts[str(row["document_id"])] = min(1.2, 0.15 * (total**0.55))
        return boosts


_memory: RetrievalMemory | None = None


def get_retrieval_memory() -> RetrievalMemory:
    global _memory
    if _memory is None:
        from app.config import get_settings

        settings = get_settings()
        # Külön fájl a vector DB mellett — agent törléskor takarítható
        path = Path(settings.vector_db_file).with_name("retrieval_memory.db")
        _memory = RetrievalMemory(path)
    return _memory


def reset_retrieval_memory() -> None:
    global _memory
    _memory = None
