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
- Cover the relevant excerpts once: if several passages apply, weave them into one coherent detailed answer.
- For lists: enumerate each distinct matching item found in the excerpts; do not stop after one or two examples.
- Never repeat the same phrase, bullet, clause, section, or list item. If you have no new distinct content, stop immediately.
- Do not pad, loop, or restate the same wording with tiny variations.
- Do not rewrite the same numbered list or section headers multiple times.
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
    "and every distinct matching list item from the excerpts. "
    "Never give a short reply or only a document/book title when the excerpts contain more information. "
    "Never repeat the same phrase or list item; stop when the distinct content ends."
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


def format_document_inventory(
    question: str,
    documents: list[tuple[str, str, int]],
) -> str:
    """Teljes dokumentumlista — nem RAG-ből, hanem az agent DB katalógusából."""
    hungarian = looks_hungarian(question)
    if not documents:
        if hungarian:
            return "Az agent tudásbázisában jelenleg nincs feldolgozott (READY) dokumentum."
        return "This agent currently has no processed (READY) documents."

    if hungarian:
        lines = [
            f"Az agent tudásbázisában jelenleg {len(documents)} feldolgozott dokumentum van:",
            "",
        ]
        for index, (_doc_id, name, chunks) in enumerate(documents, start=1):
            lines.append(f"{index}. {name} ({chunks} chunk)")
        lines.append("")
        lines.append("Ez a teljes lista — minden READY státuszú feltöltött fájl szerepel.")
        return "\n".join(lines)

    lines = [
        f"This agent currently has {len(documents)} processed documents:",
        "",
    ]
    for index, (_doc_id, name, chunks) in enumerate(documents, start=1):
        lines.append(f"{index}. {name} ({chunks} chunks)")
    lines.append("")
    lines.append("This is the complete catalog — every READY uploaded file is included.")
    return "\n".join(lines)


def format_knowledge_catalog(
    question: str,
    documents: list[tuple[str, str, int]],
) -> str:
    """Világok/rendszerek listája a dokumentumnevek alapján (teljes katalógus)."""
    from app.rag.hybrid import group_documents_by_knowledge_label

    hungarian = looks_hungarian(question)
    if not documents:
        if hungarian:
            return "Az agent tudásbázisában jelenleg nincs feldolgozott dokumentum, így világokat/rendszereket sem tudok felsorolni."
        return "This agent has no processed documents, so I cannot list any worlds or systems."

    groups = group_documents_by_knowledge_label(documents)
    if hungarian:
        lines = [
            f"A feltöltött dokumentumok alapján ezeket a szerepjátékos világokat/rendszereket ismerem ({len(groups)}):",
            "",
        ]
        for index, (label, docs) in enumerate(groups, start=1):
            doc_names = ", ".join(name for _id, name, _c in docs)
            if len(docs) == 1:
                lines.append(f"{index}. {label}")
            else:
                lines.append(f"{index}. {label} ({len(docs)} dokumentum)")
            lines.append(f"   Forrás: {doc_names}")
        lines.append("")
        lines.append("Ez a teljes lista a READY dokumentumok fájlnevei alapján — minden fellelhető világ/rendszer szerepel.")
        return "\n".join(lines)

    lines = [
        f"Based on the uploaded documents, I know these RPG worlds/systems ({len(groups)}):",
        "",
    ]
    for index, (label, docs) in enumerate(groups, start=1):
        doc_names = ", ".join(name for _id, name, _c in docs)
        if len(docs) == 1:
            lines.append(f"{index}. {label}")
        else:
            lines.append(f"{index}. {label} ({len(docs)} documents)")
        lines.append(f"   Source: {doc_names}")
    lines.append("")
    lines.append("This is the complete catalog derived from READY document filenames.")
    return "\n".join(lines)
