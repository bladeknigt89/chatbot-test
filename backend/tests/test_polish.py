from app.rag.polish import TRANSLATE_SYSTEM, build_polish_messages, polish_answer, should_polish
from app.rag.prompts import GLOBAL_RAG_SYSTEM, build_messages


def test_should_polish_hungarian_questions_only():
    assert should_polish("Foglald össze a Dark Souls világát", "Draft text")
    assert not should_polish("Summarize the Dark Souls world", "Draft text")


def test_build_polish_messages_are_translator_prompt():
    messages = build_polish_messages(
        question="Hogyan sajátítsam el a Blendert?",
        draft="Blender is free and used in game development.",
    )
    assert messages[0]["role"] == "system"
    assert "English → Hungarian" in TRANSLATE_SYSTEM
    assert "English draft:" in messages[1]["content"]
    assert "Blender is free" in messages[1]["content"]


def test_build_messages_hu_asks_for_english_draft():
    messages = build_messages(
        question="Hogyan sajátítsam el a Blendert?",
        context="[dokumentum=Blender.pdf]\nBlender is free. Start with beginner tutorials.",
        agent_system_prompt="",
        has_context=True,
    )
    user = messages[1]["content"]
    assert "English only" in user
    assert "dedicated translator" in user
    assert "Do NOT write Hungarian" in user


def test_polish_answer_translates_with_stub():
    class Stub:
        def generate(self, messages, temperature: float) -> str:
            draft = messages[-1]["content"].split("English draft:")[-1]
            draft = draft.split("Translate into correct Hungarian.")[0].strip()
            return (
                draft.replace("Blender is free", "A Blender ingyenes")
                .replace("game development", "játékfejlesztés")
            )

    out = polish_answer(
        Stub(),
        question="Hogyan sajátítsam el a Blendert?",
        draft="Blender is free and used in game development.",
    )
    assert "A Blender ingyenes" in out
    assert "játékfejlesztés" in out
