from app.rag.prompts import GLOBAL_RAG_SYSTEM, build_messages, format_document_inventory


def test_build_messages_asks_for_detailed_structured_answers():
    messages = build_messages(
        question="write me the detailed rules of legend of the five rings",
        context="[dokumentum=Core Rules.pdf]\nRoll Ring + Skill. Raises raise the TN by 5.",
        agent_system_prompt="",
        has_context=True,
    )
    assert messages[0]["role"] == "system"
    assert "EVERY question" in GLOBAL_RAG_SYSTEM
    assert "Always give a detailed, thorough answer" in GLOBAL_RAG_SYSTEM
    user = messages[1]["content"]
    assert "Core Rules.pdf" in user
    assert "MUST answer in detail" in user
    assert "Never give a short reply" in user
    assert "Never repeat the same phrase" in GLOBAL_RAG_SYSTEM
    assert "Never repeat the same phrase" in user


def test_build_messages_requires_detail_for_simple_questions_too():
    messages = build_messages(
        question="Mi a vállalat neve?",
        context="[dokumentum=hr.pdf]\nA vállalat neve: Example Kft. A munkarend H–P 8–16.",
        agent_system_prompt="",
        has_context=True,
    )
    assert "MUST answer in detail for this question (and for every question)" in messages[1]["content"]
    assert "Even simple factual questions get a rich answer" in GLOBAL_RAG_SYSTEM


def test_format_document_inventory_lists_every_file():
    docs = [
        ("1", "Avatar_Legends_The_Roleplaying_Game.pdf", 10),
        ("2", "Cyberpunk Red.pdf", 20),
        ("3", "Legend Of The Five Rings 4e - Core Rules.pdf", 30),
    ]
    hu = format_document_inventory("Milyen dokumentumai vannak?", docs)
    en = format_document_inventory("What documents do you have?", docs)
    for text in (hu, en):
        assert "Avatar_Legends_The_Roleplaying_Game.pdf" in text
        assert "Cyberpunk Red.pdf" in text
        assert "Legend Of The Five Rings 4e - Core Rules.pdf" in text
        assert "3" in text
    assert "teljes lista" in hu.lower()
    assert "complete catalog" in en.lower()


def test_build_messages_no_context_uses_insufficient_rule():
    messages = build_messages(
        question="Anything?",
        context="",
        agent_system_prompt="Be helpful.",
        has_context=False,
    )
    assert "Agent-specific instructions" in messages[0]["content"]
    assert "insufficient-information" in messages[1]["content"]
