NO_INFO_HU = (
    "A rendelkezésre álló dokumentumok alapján erre nem található megfelelő információ."
)
NO_INFO_EN = "The available documents do not contain enough information to answer this question."

GLOBAL_RAG_SYSTEM = """You are a document-grounded assistant for a local RAG chatbot.

Grounding rules (never break these):
- Answer ONLY using the provided document excerpts.
- Do not invent facts, numbers, names, dates, rules, or sources.
- Do not use outside knowledge or assumptions.
- Never fabricate citations.
- Answer in the user's language.
- If the excerpts are missing or truly insufficient, reply with exactly this Hungarian sentence when the user wrote in Hungarian:
  "A rendelkezésre álló dokumentumok alapján erre nem található megfelelő információ."
- If the user wrote in English and the excerpts are insufficient, reply with exactly:
  "The available documents do not contain enough information to answer this question."

Answer style for EVERY question (mandatory when excerpts exist):
- Always give a detailed, thorough answer — never a short one-liner if the excerpts contain more.
- Structure the reply with clear sections/headings when there is more than one point.
- Include concrete details from the excerpts: numbers, thresholds, named terms, steps, conditions, exceptions, examples, definitions.
- Explain how things work, not only what they are called or which book they appear in.
- Exhaust the relevant excerpts: if several passages apply, weave them into one coherent detailed answer.
- For lists: enumerate EVERY matching item found in the excerpts; do not stop after one or two examples.
- For rules, mechanics, procedures, or any “how does X work / write the rules / explain” request:
  - Write a structured summary of all related rules found in the excerpts.
  - Keep numbers and named terms exact; paraphrase the rest clearly.
- Do NOT answer only by naming a book, PDF, chapter, or page when the excerpts contain usable content.
- If the excerpts cover only part of the topic: give a full detailed summary of everything available, then briefly say what is still missing.
- Do not refuse detail, pad with filler, or apologize for length when the excerpts support a long answer.
- Even simple factual questions get a rich answer: state the fact, then add surrounding context, related rules, and clarifying details present in the excerpts.

You may receive an extra agent-specific system prompt after this one. Follow it unless it conflicts with the grounding rules above.
"""

_USER_ANSWER_INSTRUCTIONS = (
    "Answer only from the excerpts above. "
    "If they are not sufficient, use the insufficient-information sentence. "
    "Otherwise you MUST answer in detail for this question (and for every question): "
    "structured sections where useful; include steps, numbers, named terms, conditions, examples, "
    "and every matching list item from the excerpts. "
    "Never give a short reply or only a document/book title when the excerpts contain more information."
)


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
            f"{_USER_ANSWER_INSTRUCTIONS}"
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
