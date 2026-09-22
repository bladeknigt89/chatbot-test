from app.rag.prompts import GLOBAL_RAG_SYSTEM, build_messages


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


def test_build_messages_requires_detail_for_simple_questions_too():
    messages = build_messages(
        question="Mi a vállalat neve?",
        context="[dokumentum=hr.pdf]\nA vállalat neve: Example Kft. A munkarend H–P 8–16.",
        agent_system_prompt="",
        has_context=True,
    )
    assert "MUST answer in detail for this question (and for every question)" in messages[1]["content"]
    assert "Even simple factual questions get a rich answer" in GLOBAL_RAG_SYSTEM


def test_build_messages_no_context_uses_insufficient_rule():
    messages = build_messages(
        question="Anything?",
        context="",
        agent_system_prompt="Be helpful.",
        has_context=False,
    )
    assert "Agent-specific instructions" in messages[0]["content"]
    assert "insufficient-information" in messages[1]["content"]
