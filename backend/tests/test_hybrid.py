from app.rag.hu_morph import stem_hu, stems_hu, tokenize, tokens_match
from app.rag.hybrid import (
    document_name_boost,
    hybrid_rerank,
    is_detailed_question,
    is_document_inventory_question,
    keyword_score,
)
from app.vectorstore.store import VectorMatch


def _match(text: str, score: float, idx: int = 0, name: str = "doc.pdf") -> VectorMatch:
    return VectorMatch(
        chunk_id=f"c{idx}",
        agent_id="a1",
        document_id="d1",
        document_name=name,
        chunk_index=idx,
        text=text,
        page_number=1,
        sheet_name=None,
        score=score,
    )


def test_stem_hu_plurals_and_cases():
    assert stem_hu("karok") == "kar"
    assert stem_hu("karokat") == "kar"
    assert stem_hu("egyetemen") == "egyetem"
    assert stem_hu("egyetemeknek") == "egyetem"
    # Magánhangzós tő: hallgatóknak → hallgat (ékezet nélkül); egyezés hallgató-val
    assert stem_hu("hallgatoknak") in {"hallgato", "hallgat"}
    assert tokens_match("hallgatoknak", "hallgato")
    assert stem_hu("szabalyzatabol") == "szabalyzat"
    assert stem_hu("kollegiumokban") == "kollegium"
    assert stem_hu("tortenetet") == "tortenet"
    assert stem_hu("szakokon") == "szak"
    assert "kar" in stems_hu("kari")
    assert tokens_match("karokat", "karok")
    assert tokens_match("egyetemekrol", "egyetem")
    assert tokens_match("dokumentumaiban", "dokumentum")
    assert tokens_match("felvetelin", "felveteli")
    assert tokens_match("szakokon", "szak")
    assert tokens_match("telephelyeken", "telephely")
    assert tokens_match("kollegiumai", "kollegium")
    assert tokens_match("szabalyzatait", "szabalyzat")
    assert tokens_match("kampuszokon", "kampusz")
    assert tokens_match("tortenetet", "tortenete")
    assert tokens_match("kepzeseiben", "kepzes")
    assert tokens_match("hallgatoknak", "hallgato")
    assert tokens_match("egyetemi", "egyetem")




def test_tokens_match_across_inflection():
    pairs = [
        ("karok", "kar"),
        ("karokon", "kari"),
        ("egyetemen", "egyetem"),
        ("tortenetet", "tortenet"),
        ("felvetelin", "felveteli"),
        ("dokumentumokban", "dokumentum"),
        ("szakok", "szak"),
        ("telephelyeken", "telephely"),
        ("kollegiumai", "kollegium"),
    ]
    for left, right in pairs:
        assert tokens_match(left, right), f"{left} !~ {right}"


def test_keyword_score_boosts_history_heading():
    history = "2. Az egyetem története A Tesztelek Egyetem jogelőd intézménye 1998-ban alakult."
    other = "A hallgatók történelmi tárgyakat vehetnek fel a karokon."
    question = "Mi az egyetem története?"
    assert keyword_score(question, history) > keyword_score(question, other)


def test_keyword_score_matches_inflected_faculty_question():
    overview = (
        "7. Karok áttekintése A Tesztelek Egyetem négy nagy karral működik: "
        "1. Informatikai és Műszaki Kar 2. Gazdaságtudományi és Menedzsment Kar "
        "3. Bölcsészet- és Társadalomtudományi Kar 4. Egészségtudományi Kar"
    )
    campus = "6. Telephelyek és campusok A Tesztelek Egyetem több campusból áll."
    question = "Milyen karok vannak az egyetemen?"
    assert keyword_score(question, overview) > keyword_score(question, campus)


def test_hybrid_rerank_promotes_history_chunk():
    question = "Mi az egyetem története?"
    matches = [
        _match("A karok történelem szakot is indítanak.", 0.82, 0),
        _match("A könyvtárban történelmi kötetek találhatók.", 0.80, 1),
        _match("2. Az egyetem története A Tesztelek Egyetem 1998-ban jött létre.", 0.67, 2),
        _match("A sportélet a campuson aktív.", 0.75, 3),
        _match("A nemzetközi kapcsolatok széleskörűek.", 0.74, 4),
        _match("A kollégiumi férőhelyek száma korlátozott.", 0.73, 5),
    ]
    ranked = hybrid_rerank(question, matches, top_k=5)
    assert "egyetem története" in ranked[0].text.lower()
    assert "1998" in ranked[0].text


def test_hybrid_rerank_promotes_faculty_overview():
    question = "Milyen karokat sorol fel a dokumentum?"
    matches = [
        _match("A campus sportpályákat és tornacsarnokot tartalmaz.", 0.85, 0),
        _match("A minőségbiztosítás hallgatói visszajelzéseken alapul.", 0.84, 1),
        _match(
            "7. Karok áttekintése négy kar: Informatikai és Műszaki Kar, "
            "Gazdaságtudományi és Menedzsment Kar, Bölcsészet- és Társadalomtudományi Kar, "
            "Egészségtudományi Kar",
            0.55,
            2,
        ),
        _match("A rektor Dr. Varga Áron.", 0.80, 3),
    ]
    ranked = hybrid_rerank(question, matches, top_k=3)
    assert "karok áttekintése" in ranked[0].text.lower()


def test_tokenize_skips_stopwords():
    assert "milyen" not in tokenize("Milyen karok vannak?")
    assert "karok" in tokenize("Milyen karok vannak?")


def test_is_detailed_question_detects_rules_requests():
    assert is_detailed_question("write me the detailed rules of legend of the five rings")
    assert is_detailed_question("Ismertesd a részletes szabályokat")
    assert not is_detailed_question("Mi a vállalat neve?")


def test_is_document_inventory_question():
    assert is_document_inventory_question("milyen dokumentumai vannak az agentnek?")
    assert is_document_inventory_question("What documents do you have?")
    assert is_document_inventory_question("Sorold fel a feltöltött könyveket")
    assert is_document_inventory_question("how many files are available?")
    assert not is_document_inventory_question("Mi a próbaidő a munkaszabályzatban?")
    assert not is_document_inventory_question("write me the detailed rules of legend of the five rings")


def test_is_knowledge_catalog_question():
    from app.rag.hybrid import is_knowledge_catalog_question, knowledge_label_from_filename

    assert is_knowledge_catalog_question("milyen szerepjátékos világokat/rendszereket ismersz?")
    assert is_knowledge_catalog_question("What RPG worlds and systems do you know?")
    assert is_knowledge_catalog_question("Sorold fel a világokat")
    assert not is_knowledge_catalog_question("mit tudsz a fallout világáról?")
    assert not is_knowledge_catalog_question("Mi a próbaidő a munkaszabályzatban?")
    assert not is_knowledge_catalog_question("milyen dokumentumai vannak?")

    assert knowledge_label_from_filename("Fallout Core Rulebook Digital Release - February 2023.pdf") == "Fallout"
    assert knowledge_label_from_filename("Cyberpunk Red.pdf") == "Cyberpunk"
    assert (
        knowledge_label_from_filename("Legend Of The Five Rings 4e - Core Rules.pdf")
        == "Legend of the Five Rings"
    )
    assert knowledge_label_from_filename("blade-runner-rpg-core-rules.pdf") == "Blade Runner"
    assert knowledge_label_from_filename("Dragonage Core Rulebook.pdf") == "Dragon Age"


def test_document_name_boost_prefers_core_rules():
    question = "write me the detailed rules of legend of the five rings"
    core = document_name_boost(question, "Legend Of The Five Rings 4e - Core Rules.pdf")
    history = document_name_boost(question, "Legend Of The Five Rings 4e - Imperial Histories.pdf")
    assert core > history


def test_filename_topic_score_routes_fallout():
    from app.rag.hybrid import filename_topic_score, rank_documents

    question = "mit tudsz a fallout világáról?"
    fallout = filename_topic_score("Fallout - Core Rulebook.pdf", question)
    l5r = filename_topic_score("Legend Of The Five Rings 4e - Core Rules.pdf", question)
    assert fallout > 0.5
    assert fallout > l5r

    fo = VectorMatch(
        chunk_id="fo1",
        agent_id="a1",
        document_id="d-fo",
        document_name="Fallout - Core Rulebook.pdf",
        chunk_index=0,
        text="The Great War left the world in ashes. Vault-Tec built vaults.",
        page_number=1,
        sheet_name=None,
        score=0.55,
    )
    l5 = VectorMatch(
        chunk_id="l51",
        agent_id="a1",
        document_id="d-l5r",
        document_name="Legend Of The Five Rings 4e - Core Rules.pdf",
        chunk_index=0,
        text="Roll Ring + Skill Keep Trait.",
        page_number=1,
        sheet_name=None,
        score=0.95,
    )
    ranked = rank_documents(
        [l5, fo],
        question,
        document_catalog=[
            ("d-l5r", "Legend Of The Five Rings 4e - Core Rules.pdf"),
            ("d-fo", "Fallout - Core Rulebook.pdf"),
            ("d-other", "Some Other RPG.pdf"),
        ],
    )
    assert ranked[0][0] == "d-fo"
    assert "Fallout" in ranked[0][1]


def test_hybrid_rerank_raises_top_k_for_detailed_rules():
    question = "write me the detailed rules of legend of the five rings"
    matches = [
        _match("History of the Emerald Empire.", 0.9, 0, "Imperial Histories.pdf"),
        _match("Clan politics overview.", 0.88, 1, "The Great Clans.pdf"),
        _match("Roll Ring + Skill Keep Trait. Raises increase the TN by 5.", 0.55, 2, "Core Rules.pdf"),
        _match("Dice pools and TN basics for skill rolls.", 0.54, 3, "Core Rules.pdf"),
        _match("Conflict rounds and initiative order.", 0.53, 4, "Core Rules.pdf"),
    ]
    # Pad with filler so top_k expansion has room
    for i in range(5, 40):
        matches.append(_match(f"Flavor text {i} about clans.", 0.4, i, "Emerald Empire.pdf"))
    ranked = hybrid_rerank(question, matches, top_k=8)
    assert len(ranked) >= 24
    assert any("Core Rules" in m.document_name for m in ranked[:5])
    assert any("Ring + Skill" in m.text or "Dice pools" in m.text for m in ranked[:5])
