from app.llm.repetition import StreamRepetitionGuard, collapse_repetition


def test_collapse_repetition_cuts_runaway_phrase():
    unit = "vitelkocka eredmény értéke, "
    text = "A Fallout világában: " + unit * 40
    cleaned, cut = collapse_repetition(text)
    assert cut
    assert cleaned.count("vitelkocka eredmény értéke") <= 3
    assert len(cleaned) < len(text) // 4
    assert cleaned.startswith("A Fallout világában:")


def test_collapse_repetition_cuts_multiline_dark_souls_loop():
    block = (
        "A Dark Souls tárhelyes játék tartalmaz:\n"
        "1. **Karakterkészítés** - különböző képességeket, tulajdonságokat és találkozási lehetőséget.\n"
        "2. **Adventúra**: A hősök közös céllal harcolnak a világban.\n"
    )
    prefix = (
        "A Dark Souls világában a hősök Undead-ek. "
        "A tárhelyes játékban karaktereket készítenek.\n\n"
    )
    text = prefix + block * 25
    cleaned, cut = collapse_repetition(text, max_consecutive=1)
    assert cut
    assert cleaned.count("A Dark Souls tárhelyes játék tartalmaz:") <= 2
    assert "Undead" in cleaned or "karaktereket" in cleaned
    assert len(cleaned) < len(text) // 5


def test_collapse_repetition_keeps_normal_prose():
    text = (
        "A Fallout világ post-apokaliptikus. "
        "A Vault-Tec bunkerjei védték az embereket. "
        "A ghoulok sugárzás miatt alakultak ki."
    )
    cleaned, cut = collapse_repetition(text)
    assert cleaned == text
    assert not cut


def test_stream_guard_stops_on_loop():
    guard = StreamRepetitionGuard(check_every=10, min_buffer=40)
    prefix = "Lista: "
    unit = "vitelkocka eredmény értéke, "
    emitted = []
    for ch in prefix:
        out = guard.push(ch)
        if out:
            emitted.append(out)
    for _ in range(30):
        out = guard.push(unit)
        if out:
            emitted.append(out)
        if guard.triggered:
            break
    assert guard.triggered
    full = "".join(emitted)
    final = guard.finalize(full + unit * 5)
    assert final.count("vitelkocka") <= 4


def test_stream_guard_stops_on_multiline_loop():
    guard = StreamRepetitionGuard(check_every=8, min_buffer=30)
    block = (
        "A Dark Souls tárhelyes játék tartalmaz:\n"
        "1. **Karakterkészítés** - különböző képességeket.\n"
        "2. **Adventúra**: A hősök harcolnak.\n"
    )
    for _ in range(8):
        guard.push(block)
        if guard.triggered:
            break
    assert guard.triggered
