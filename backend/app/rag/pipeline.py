from dataclasses import dataclass
from collections.abc import Callable
from uuid import uuid4

from app.config import get_settings
from app.documents.chunking import Chunk
from app.embeddings.base import EmbeddingProvider
from app.llm.base import LLMProvider
from app.rag.hybrid import is_detailed_question, is_list_question
from app.rag.prompts import build_messages, no_info_reply
from app.schemas import ChatSource
from app.vectorstore.store import SqliteVectorStore, VectorMatch


@dataclass
class RAGResult:
    answer: str
    sources: list[ChatSource]
    matches: list[VectorMatch]


class RAGPipeline:
    def __init__(
        self,
        embeddings: EmbeddingProvider,
        llm: LLMProvider | None,
        store: SqliteVectorStore,
    ) -> None:
        self.embeddings = embeddings
        self.llm = llm
        self.store = store

    def _llm(self) -> LLMProvider:
        if self.llm is None:
            raise RuntimeError("A helyi LLM nincs inicializálva.")
        return self.llm

    def index_chunks(
        self,
        *,
        agent_id: str,
        document_id: str,
        document_name: str,
        chunks: list[Chunk],
        on_progress: Callable[[int, int, int], None] | None = None,
        batch_size: int = 8,
    ) -> int:
        if not chunks:
            return 0
        total = len(chunks)
        indexed = 0
        size = max(1, batch_size)
        for start in range(0, total, size):
            batch = chunks[start : start + size]
            payload = []
            texts = []
            for chunk in batch:
                payload.append(
                    {
                        "id": str(uuid4()),
                        "chunk_index": chunk.chunk_index,
                        "page_number": chunk.page_number,
                        "sheet_name": chunk.sheet_name,
                        "text": chunk.text,
                    }
                )
                texts.append(chunk.text)
            embeddings = self.embeddings.embed_documents(texts)
            self.store.add_chunks(
                agent_id=agent_id,
                document_id=document_id,
                document_name=document_name,
                chunks=payload,
                embeddings=embeddings,
            )
            indexed += len(batch)
            if on_progress is not None:
                # Embedding szakasz: 35% → 95%
                percent = 35 + int(60 * indexed / total)
                on_progress(min(percent, 95), indexed, total)
        return indexed

    def retrieve(self, *, agent_id: str, question: str, top_k: int | None = None) -> list[VectorMatch]:
        from app.rag.hybrid import (
            diversify_by_document,
            hybrid_rerank,
            keyword_score,
            merge_candidates,
            query_topic_terms,
            rank_documents,
        )

        settings = get_settings()
        k = top_k or settings.top_k
        # Minden kérdéshez bővebb kontextus — a részletes válaszhoz kell.
        k = max(k, 20)
        if is_list_question(question):
            k = max(k, 24)
        if is_detailed_question(question):
            k = max(k, 28)

        catalog = self.store.list_documents(agent_id)
        if not catalog:
            return []

        query_embedding = self.embeddings.embed_query(question)
        terms = query_topic_terms(question)

        # --- 1. szint: dokumentum-routing (ne csak a globális top chunkok fájljai) ---
        coarse_k = max(settings.doc_route_coarse_k, k * 4)
        coarse_vector = self.store.search(
            query_embedding,
            agent_id=agent_id,
            top_k=coarse_k,
        )
        coarse_lexical = self.store.search_text(
            agent_id=agent_id,
            terms=terms,
            limit=max(200, coarse_k),
        )
        # Lexikális találatoknak adjunk alap score-t a keyword_score alapján
        lexical_scored: list[VectorMatch] = []
        for item in coarse_lexical:
            kw = keyword_score(question, f"{item.document_name} {item.text}")
            if kw < 0.08 and not any(t in (item.document_name or "").lower() for t in terms):
                continue
            lexical_scored.append(
                VectorMatch(
                    chunk_id=item.chunk_id,
                    agent_id=item.agent_id,
                    document_id=item.document_id,
                    document_name=item.document_name,
                    chunk_index=item.chunk_index,
                    text=item.text,
                    page_number=item.page_number,
                    sheet_name=item.sheet_name,
                    score=max(0.35, kw),
                )
            )

        route_pool = merge_candidates(coarse_vector, lexical_scored)
        doc_ranked = rank_documents(route_pool, question, document_catalog=catalog)
        route_n = max(settings.doc_route_min_n, min(settings.doc_route_top_n, len(doc_ranked) or 1))
        # Ha a fájlnév erősen egyezik, tartsuk meg az összes ilyen dokumentumot (max route_n*2)
        strong = [d for d in doc_ranked if d[2] >= 0.35]
        if strong:
            routed_ids = [d[0] for d in strong[: max(route_n, min(len(strong), route_n * 2))]]
        else:
            routed_ids = [d[0] for d in doc_ranked[:route_n]]
        if not routed_ids:
            routed_ids = [doc_id for doc_id, _ in catalog[:route_n]]

        # --- 2. szint: mély keresés csak a kiválasztott dokumentumokban ---
        per_doc = max(settings.chunks_per_routed_doc, k)
        deep_vector = self.store.search(
            query_embedding,
            agent_id=agent_id,
            top_k=per_doc * max(1, len(routed_ids)),
            document_ids=routed_ids,
        )
        deep_lexical = self.store.search_text(
            agent_id=agent_id,
            terms=terms,
            limit=max(150, per_doc * 2),
            document_ids=routed_ids,
        )
        deep_lex_scored: list[VectorMatch] = []
        for item in deep_lexical:
            kw = keyword_score(question, f"{item.document_name} {item.text}")
            deep_lex_scored.append(
                VectorMatch(
                    chunk_id=item.chunk_id,
                    agent_id=item.agent_id,
                    document_id=item.document_id,
                    document_name=item.document_name,
                    chunk_index=item.chunk_index,
                    text=item.text,
                    page_number=item.page_number,
                    sheet_name=item.sheet_name,
                    score=max(0.35, kw),
                )
            )

        candidates = merge_candidates(deep_vector, deep_lex_scored, route_pool)
        # Csak a routed dokumentumok chunkjai menjenek tovább (ne szivárogjon be irreleváns top globális)
        routed_set = set(routed_ids)
        candidates = [m for m in candidates if m.document_id in routed_set]
        ranked = hybrid_rerank(question, candidates, top_k=max(k, per_doc))
        diversified = diversify_by_document(
            ranked,
            limit=k,
            max_per_doc=max(4, k // max(1, min(len(routed_ids), 4))),
        )
        max_total = 40 if not is_detailed_question(question) else 48
        return self._expand_neighbors(diversified, window=1, max_total=max_total)

    def _expand_neighbors(
        self,
        matches: list[VectorMatch],
        *,
        window: int = 1,
        max_total: int = 48,
    ) -> list[VectorMatch]:
        """Szomszédos chunkok beemelése — folyamatos szabályszöveghez."""
        if not matches or window <= 0:
            return matches
        by_id = {m.chunk_id: m for m in matches}
        for seed in list(matches):
            if len(by_id) >= max_total:
                break
            indices = [
                seed.chunk_index + offset
                for offset in range(-window, window + 1)
                if seed.chunk_index + offset >= 0
            ]
            neighbors = self.store.get_chunks_by_indices(
                agent_id=seed.agent_id,
                document_id=seed.document_id,
                indices=indices,
            )
            for neighbor in neighbors:
                if neighbor.chunk_id in by_id:
                    continue
                by_id[neighbor.chunk_id] = VectorMatch(
                    chunk_id=neighbor.chunk_id,
                    agent_id=neighbor.agent_id,
                    document_id=neighbor.document_id,
                    document_name=neighbor.document_name,
                    chunk_index=neighbor.chunk_index,
                    text=neighbor.text,
                    page_number=neighbor.page_number,
                    sheet_name=neighbor.sheet_name,
                    score=max(0.0, seed.score - 0.02),
                )
                if len(by_id) >= max_total:
                    break
        # Dokumentumon belüli sorrend: a modell összefüggő szabályt kapjon
        ordered = sorted(
            by_id.values(),
            key=lambda m: (m.document_name, m.chunk_index, -m.score),
        )
        return ordered

    def build_context(self, matches: list[VectorMatch]) -> str:
        parts = []
        for match in matches:
            meta = [f"dokumentum={match.document_name}", f"chunk={match.chunk_index}"]
            if match.page_number is not None:
                meta.append(f"oldal={match.page_number}")
            if match.sheet_name:
                meta.append(f"munkalap={match.sheet_name}")
            parts.append(f"[{', '.join(meta)}]\n{match.text}")
        return "\n\n".join(parts)

    def answer(
        self,
        *,
        agent_id: str,
        question: str,
        agent_system_prompt: str = "",
        include_sources: bool = True,
    ) -> RAGResult:
        matches = self.retrieve(agent_id=agent_id, question=question)
        if not matches:
            reply = no_info_reply(question)
            return RAGResult(answer=reply, sources=[], matches=[])
        context = self.build_context(matches)
        messages = build_messages(
            question=question,
            context=context,
            agent_system_prompt=agent_system_prompt,
            has_context=True,
        )
        settings = get_settings()
        answer = self._llm().generate(messages, temperature=settings.llm_temperature)
        sources = self._sources(matches) if include_sources else []
        return RAGResult(answer=answer.strip(), sources=sources, matches=matches)

    def stream_answer(
        self,
        *,
        agent_id: str,
        question: str,
        agent_system_prompt: str = "",
    ):
        matches = self.retrieve(agent_id=agent_id, question=question)
        if not matches:
            yield no_info_reply(question)
            return
        context = self.build_context(matches)
        messages = build_messages(
            question=question,
            context=context,
            agent_system_prompt=agent_system_prompt,
            has_context=True,
        )
        settings = get_settings()
        yield from self._llm().stream(messages, temperature=settings.llm_temperature)

    def _sources(self, matches: list[VectorMatch]) -> list[ChatSource]:
        unique: dict[tuple, ChatSource] = {}
        for match in matches:
            key = (match.document_id, match.page_number, match.sheet_name, match.chunk_index)
            unique[key] = ChatSource(
                document_id=match.document_id,
                document_name=match.document_name,
                chunk_index=match.chunk_index,
                page_number=match.page_number,
                sheet_name=match.sheet_name,
                score=round(match.score, 4),
            )
        return list(unique.values())
