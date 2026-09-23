"""Magyar fordítás / nyelvi javítás a RAG válasz után."""

from __future__ import annotations

import re

from app.llm.base import LLMProvider
from app.rag.prompts import looks_hungarian

TRANSLATE_SYSTEM = """You are a professional translator: English → Hungarian (Hungary).

Translate the draft into ONE short, fluent, grammatically correct Hungarian answer.

Rules:
- Keep every fact and meaning; do not invent URLs, salaries, or extra topics.
- Natural Hungarian (correct cases, conjugations, agreement). Prefer clear everyday wording.
- Keep product names unchanged when usual (Blender, Discord, Dark Souls…).
- No preamble, no „Kérdésedre válaszolva”, no repeated paragraphs.
- Output only the Hungarian translation, then stop.
"""

POLISH_SYSTEM = TRANSLATE_SYSTEM


def build_translate_messages(*, question: str, draft: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": TRANSLATE_SYSTEM},
        {
            "role": "user",
            "content": (
                "User question (tone only):\n"
                f"{question}\n\n"
                "English draft:\n"
                f"{draft}\n\n"
                "Translate into correct Hungarian. One answer only. Stop when finished."
            ),
        },
    ]


def build_polish_messages(*, question: str, draft: str) -> list[dict[str, str]]:
    return build_translate_messages(question=question, draft=draft)


def should_polish(question: str, draft: str) -> bool:
    if not draft or not draft.strip():
        return False
    return looks_hungarian(question)


def _strip_meta(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(
        r"^(here is|here's|translation|fordítás|javított válasz|kérdésedre válaszolva)\s*:?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Ha a modell többször újraindítja ugyanazt a választ
    marker = "Kérdésedre válaszolva"
    if marker in cleaned:
        cleaned = cleaned.split(marker)[0].strip()
    return cleaned.strip()


def polish_answer(
    llm: LLMProvider,
    *,
    question: str,
    draft: str,
    temperature: float = 0.1,
) -> str:
    """Angol (vagy hibás) vázlat → helyes magyar."""
    if not should_polish(question, draft):
        return draft.strip()
    messages = build_translate_messages(question=question, draft=draft.strip())
    polished = llm.generate(messages, temperature=temperature)
    return _strip_meta(polished or draft)
