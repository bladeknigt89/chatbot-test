NO_INFO_HU = (
    "A rendelkezésre álló dokumentumok alapján erre nem található megfelelő információ."
)
NO_INFO_EN = "The available documents do not contain enough information to answer this question."

GLOBAL_RAG_SYSTEM = """You are a document-grounded assistant for a local RAG chatbot.

Rules you MUST follow:
- Answer ONLY using the provided document context.
- Do not invent facts, numbers, names, dates, or sources.
- Do not add assumptions or outside knowledge.
- If the context is missing or insufficient, reply with exactly this sentence when the user wrote in Hungarian:
  "A rendelkezésre álló dokumentumok alapján erre nem található megfelelő információ."
- If the user wrote in English and the context is insufficient, reply with exactly:
  "The available documents do not contain enough information to answer this question."
- Answer in the user's language.
- When you use information, stay faithful to the documents.
- Never fabricate citations.
- If the user asks for a list (e.g. faculties, departments, items), enumerate EVERY matching item found in the excerpts. Do not stop after one or two examples.

You may receive an extra agent-specific system prompt after this one.
"""


def build_messages(
    *,
    question: str,
    context: str,
    agent_system_prompt: str,
    has_context: bool,
) -> list[dict[str, str]]:
    extra = agent_system_prompt.strip()
    system = GLOBAL_RAG_SYSTEM
    if extra:
        system += "\n\nAgent-specific instructions:\n" + extra
    if not has_context:
        user = (
            "No document excerpts were retrieved for this question.\n"
            f"User question:\n{question}\n\n"
            "Follow the insufficient-information rule."
        )
    else:
        user = (
            "Document excerpts:\n"
            f"{context}\n\n"
            f"User question:\n{question}\n\n"
            "Answer only from the excerpts. If they are not sufficient, use the insufficient-information sentence. "
            "If the question asks to list items, include every matching item present in the excerpts."
        )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def looks_hungarian(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "á", "é", "í", "ó", "ö", "ő", "ú", "ü", "ű",
        " mi ", " mennyi", " milyen", " hol ", " mikor",
        " foglald", " szerződés", " szabadság", " dokumentum",
    ]
    return any(marker in lowered for marker in markers) or any(
        ch in text for ch in "áéíóöőúüűÁÉÍÓÖŐÚÜŰ"
    )


def no_info_reply(question: str) -> str:
    return NO_INFO_HU if looks_hungarian(question) else NO_INFO_EN
