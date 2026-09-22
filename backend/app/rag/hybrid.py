"""Hibrid retrieval: vektor + kulcsszó újrarangsorolás (magyar RAG)."""

from __future__ import annotations

import re

from app.rag.hu_morph import (
    expand_query_tokens,
    fold_accents,
    stem_hu,
    stems_hu,
    tokenize,
    tokens_match,
)
from app.vectorstore.store import VectorMatch

_LIST_QUESTION = re.compile(
    r"\b(milyen|melyek|melyik|sorold|felsorol|osszes|összes|listazd|nevez[dz]|mik\b|hany\b|hány\b)",
    re.IGNORECASE,
)

_DETAILED_QUESTION = re.compile(
    r"("
    r"\bdetailed\b|\bfull\b|\bcomplete\b|\bcomprehensive\b|\bexplain\b|\bwrite\s+me\b|"
    r"\brules?\b|\bmechanics?\b|\bhow\s+to\s+play\b|\bstep[- ]by[- ]step\b|"
    r"\breszletes|\brészletes|\bteljes\b|\bmagyaraz|\bmagyaráz|\bszabaly|\bszabály|"
    r"\bismertes|\bfoglald\s+ossze|\bfoglald\s+össze|\bmutasd\s+be\b"
    r")",
    re.IGNORECASE,
)

# Téma-bónusz: kérdés-tő → dokumentum-jelzők (általános, nem csak egy-egy szó).
_TOPIC_MARKERS: tuple[tuple[str, tuple[str, ...], float], ...] = (
    ("tortenet", ("tortenet", "jogelod", "alapit"), 0.4),
    ("alapit", ("alapit", "1998", "jogelod", "letrejott"), 0.25),
    ("felveteli", ("felveteli", "pontszam", "jelentkezes"), 0.3),
    ("kollegium", ("kollegium", "ferhely"), 0.3),
    ("campus", ("campus", "telephely"), 0.25),
    ("szak", ("szak", "kepzes", "alapkepzes", "mesterkepzes"), 0.25),
    ("kar", ("kar", "attekintes", "fakult"), 0.35),
    ("vezet", ("rektor", "dekán", "dekan", "kancellar"), 0.25),
    ("szabalyzat", ("szabalyzat", "rendelkezes"), 0.25),
)


def is_list_question(question: str) -> bool:
    return bool(_LIST_QUESTION.search(fold_accents(question)))


def is_detailed_question(question: str) -> bool:
    """Részletes / szabály / teljes magyarázat kérések — több kontextust igényelnek."""
    return bool(_DETAILED_QUESTION.search(fold_accents(question)))


def document_name_boost(question: str, document_name: str) -> float:
    """Dokumentumnév-együttállás (pl. rules → Core Rules)."""
    q = fold_accents(question.lower())
    name = fold_accents(document_name.lower().replace("_", " ").replace("-", " "))
    boost = 0.0
    wants_rules = any(
        tok in q for tok in ("rule", "rules", "szabal", "szabaly", "mechanics", "how to play")
    )
    if wants_rules:
        if "core rule" in name or ("core" in name and "rule" in name):
            boost += 0.45
        elif "rule" in name and "enemy" not in name and "histor" not in name:
            boost += 0.2
    if "legend of the five rings" in q or re.search(r"\bl5r\b", q):
        if "legend of the five rings" in name or "l5r" in name:
            boost += 0.12
    return boost


def _token_hit(q_tok: str, text_tokens: set[str]) -> bool:
    for text_tok in text_tokens:
        if tokens_match(q_tok, text_tok):
            return True
    return False


def keyword_score(question: str, text: str) -> float:
    q_tokens = tokenize(question)
    if not q_tokens:
        return 0.0
    text_fold = fold_accents(text)
    text_tokens = set(tokenize(text))
    hits = sum(1 for tok in q_tokens if _token_hit(tok, text_tokens))
    score = hits / len(q_tokens)

    q_stems = expand_query_tokens(q_tokens)

    # Általános téma-bónusz a kérdés tövei alapján
    for topic, markers, boost in _TOPIC_MARKERS:
        if topic in q_stems or any(tokens_match(topic, s) for s in q_stems):
            if any(marker in text_fold for marker in markers):
                score += boost

    if "egyetem" in q_stems and any(tokens_match("egyetem", t) for t in text_tokens):
        score += 0.08
    if any(tokens_match("nev", s) for s in q_stems) and (
        "intezmeny neve" in text_fold or "egyetem" in text_fold
    ):
        score += 0.12

    # Többes / listás kérdések: ha a főnévi tő sokszor előfordul a szövegben
    content_stems = [stem_hu(t) for t in q_tokens if len(stem_hu(t)) >= 3]
    for stem in content_stems:
        if stem in {"egyetem", "dokumentum", "szoveg"}:
            continue
        # tő előfordulás a szöveg tokenjeiben
        occ = sum(1 for t in text_tokens if tokens_match(stem, t) or stem in stems_hu(t))
        if occ >= 3:
            score += 0.35
        elif occ >= 2:
            score += 0.18

        # „X áttekintése” / számozott felsorolás a tő körül
        if f"{stem}" in text_fold and ("attekintes" in text_fold or "attekinto" in text_fold):
            score += 0.4

    if is_list_question(question):
        numbered = len(re.findall(r"(?:^|\s)\d{1,2}\.\s+\S", text))
        if numbered >= 3:
            score += 0.35
        elif numbered >= 2:
            score += 0.2

    if is_detailed_question(question):
        # Játékszabály / mechanika jelek
        if any(
            marker in text_fold
            for marker in (
                "roll",
                "dice",
                "skill",
                "ring",
                "tn ",
                "raises",
                "conflict",
                "initiative",
                "damage",
                "trait",
                "dobas",
                "kocka",
                "kepesseg",
                "celertek",
            )
        ):
            score += 0.2

    return min(score, 1.0)


def hybrid_rerank(
    question: str,
    matches: list[VectorMatch],
    *,
    top_k: int,
    keyword_weight: float = 0.55,
) -> list[VectorMatch]:
    if not matches:
        return []
    ranked: list[VectorMatch] = []
    for match in matches:
        kw = keyword_score(question, match.text)
        doc_boost = document_name_boost(question, match.document_name)
        combined = ((1.0 - keyword_weight) * float(match.score)) + (keyword_weight * kw) + doc_boost
        ranked.append(
            VectorMatch(
                chunk_id=match.chunk_id,
                agent_id=match.agent_id,
                document_id=match.document_id,
                document_name=match.document_name,
                chunk_index=match.chunk_index,
                text=match.text,
                page_number=match.page_number,
                sheet_name=match.sheet_name,
                score=combined,
            )
        )
    ranked.sort(key=lambda item: item.score, reverse=True)

    effective_k = max(top_k, min(len(ranked), 20))
    if is_list_question(question):
        effective_k = max(effective_k, min(len(ranked), top_k + 4, 24))
    if is_detailed_question(question):
        effective_k = max(effective_k, min(len(ranked), max(top_k * 3, 28)))
    return ranked[:effective_k]


def merge_candidates(*groups: list[VectorMatch]) -> list[VectorMatch]:
    """Deduplikál chunk_id szerint; a magasabb score marad."""
    best: dict[str, VectorMatch] = {}
    for group in groups:
        for match in group:
            prev = best.get(match.chunk_id)
            if prev is None or match.score > prev.score:
                best[match.chunk_id] = match
    return list(best.values())
