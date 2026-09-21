from app.rag.hu_morph import stem_hu, stems_hu, tokenize, tokens_match
from app.rag.hybrid import hybrid_rerank, keyword_score
from app.vectorstore.store import VectorMatch


def _match(text: str, score: float, idx: int = 0) -> VectorMatch:
    return VectorMatch(
        chunk_id=f"c{idx}",
        agent_id="a1",
        document_id="d1",
        document_name="doc.pdf",
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
