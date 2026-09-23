"""LLM ismétlés / degenerált hurkok levágása."""

from __future__ import annotations

import re


def _normalize_ws(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text).strip()


def _trim_to_word_count(text: str, word_count: int) -> str:
    """Szöveg elejét megtartja word_count szóig — sortörésekkel együtt."""
    if word_count <= 0:
        return ""
    seen = 0
    for match in re.finditer(r"\S+", text):
        seen += 1
        if seen >= word_count:
            return text[: match.end()].rstrip()
    return text.rstrip()


def collapse_repetition(
    text: str,
    *,
    max_consecutive: int = 2,
    min_unit_chars: int = 6,
    max_unit_chars: int = 600,
) -> tuple[str, bool]:
    """
    Levágja a futó ismétléseket:
    - rövid frázisok („vitelkocka eredmény értéke,” ×100)
    - többsoros blokkok (ugyanaz a 2 pontos lista újra és újra)
    """
    if not text or len(text) < min_unit_chars * (max_consecutive + 1):
        return text, False

    original = text
    out = text
    cut = False

    # 1) Többsoros / bekezdés-blokk ismétlés a végén
    collapsed, did = _collapse_trailing_line_blocks(out, max_keep=max_consecutive)
    if did:
        out = collapsed
        cut = True

    collapsed, did = _collapse_near_duplicate_paragraphs(out, max_keep=max_consecutive)
    if did:
        out = collapsed
        cut = True

    # 2) Azonos sorok egymás után (pl. ugyanaz a fejléc 20×)
    collapsed, did = _collapse_duplicate_lines(out, max_keep=max_consecutive)
    if did:
        out = collapsed
        cut = True

    # 3) Szó-n-gram ismétlés a végén (ne törje szét a sortöréseket, ha már vágtunk)
    words = re.findall(r"\S+", out)
    if len(words) >= 12:
        max_n = min(40, len(words) // (max_consecutive + 2))
        for n in range(max_n, 2, -1):
            unit = words[-n:]
            reps = 1
            i = len(words) - n
            while i >= n and words[i - n : i] == unit:
                reps += 1
                i -= n
            if reps > max_consecutive:
                # Karakter-szinten vágjuk a szöveg végét, sortörés megmarad
                # Becsüljük a megtartandó szószámot
                keep_word_count = i + n * max_consecutive
                out = _trim_to_word_count(out, keep_word_count)
                cut = True
                break

    # 4) Karakter-egység ismétlés a végén
    if len(out) >= min_unit_chars * (max_consecutive + 1):
        upper = min(max_unit_chars, len(out) // (max_consecutive + 1))
        for unit_len in range(upper, min_unit_chars - 1, -1):
            unit = out[-unit_len:]
            stripped = unit.strip(" \t,;|-\n")
            if len(stripped) < min_unit_chars:
                continue
            # Üres / csak whitespace egység skip
            if not stripped:
                continue
            reps = 1
            pos = len(out) - unit_len
            while pos >= unit_len and out[pos - unit_len : pos] == unit:
                reps += 1
                pos -= unit_len
            if reps > max_consecutive:
                out = out[: pos + unit_len * max_consecutive].rstrip(" \t,;|-\n")
                cut = True
                break

    # 5) „X, X, X, X” minta
    pattern = re.compile(
        r"(?P<head>[\s\S]*?)(?P<item>[^,:\n]{4,80})(?P<rep>(?:\s*,\s*(?P=item)){3,})\s*$",
        re.IGNORECASE,
    )
    m = pattern.search(out)
    if m:
        item = m.group("item").strip()
        head = m.group("head")
        out = f"{head}{item}, {item}".rstrip(" \t,")
        cut = True

    if cut:
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r" ?, {2,}", ", ", out)
        out = re.sub(r"\n{3,}", "\n\n", out).rstrip(" ,;\t\n")
    return out, cut or out != original


def _collapse_trailing_line_blocks(text: str, *, max_keep: int = 1) -> tuple[str, bool]:
    """Egymás utáni azonos többsoros blokkok a szöveg végén."""
    lines = text.split("\n")
    # Záró üres sorok ne törjék el az illesztést
    while lines and not _normalize_ws(lines[-1]):
        lines.pop()
    if len(lines) < 6:
        return text, False

    max_block = min(16, len(lines) // 3)
    for block_len in range(max_block, 0, -1):
        block = lines[-block_len:]
        if not any(_normalize_ws(ln) for ln in block):
            continue
        joined = "\n".join(block)
        if block_len == 1 and len(_normalize_ws(joined)) < 24:
            continue
        reps = 1
        i = len(lines) - block_len
        while i >= block_len and lines[i - block_len : i] == block:
            reps += 1
            i -= block_len
        if reps > max_keep:
            keep = lines[: i + block_len * max_keep]
            return "\n".join(keep).rstrip(), True
    return text, False


def _collapse_near_duplicate_paragraphs(text: str, *, max_keep: int = 1) -> tuple[str, bool]:
    """
    Majdnem azonos bekezdések a végén (whitespace / markdown eltérésekkel).
    """
    parts = re.split(r"\n\s*\n", text)
    if len(parts) < max_keep + 2:
        return text, False

    def key(p: str) -> str:
        t = re.sub(r"[*_`#]+", "", p)
        t = re.sub(r"\s+", " ", t).strip().lower()
        return t

    keys = [key(p) for p in parts]
    if not keys[-1]:
        return text, False
    reps = 1
    i = len(parts) - 1
    while i > 0 and keys[i - 1] == keys[-1] and keys[-1]:
        reps += 1
        i -= 1
    # i most az első ismétlés indexe előtti
    first = len(parts) - reps
    if reps > max_keep and len(keys[-1]) >= 40:
        keep = parts[: first + max_keep]
        return "\n\n".join(keep).rstrip(), True
    return text, False


def _collapse_duplicate_lines(text: str, *, max_keep: int = 2) -> tuple[str, bool]:
    """Ugyanaz a nem-üres sor max_keep-nél többször egymás után → levág."""
    lines = text.split("\n")
    if len(lines) < max_keep + 1:
        return text, False
    out: list[str] = []
    cut = False
    i = 0
    while i < len(lines):
        line = lines[i]
        key = _normalize_ws(line)
        if not key:
            out.append(line)
            i += 1
            continue
        run = 1
        while i + run < len(lines) and _normalize_ws(lines[i + run]) == key:
            run += 1
        keep_n = min(run, max_keep)
        if run > max_keep:
            cut = True
        out.extend(lines[i : i + keep_n])
        i += run
    if not cut:
        return text, False
    return "\n".join(out).rstrip(), True


class StreamRepetitionGuard:
    """Streaming közben figyeli az ismétlést; triggered = állj le."""

    def __init__(self, *, check_every: int = 16, min_buffer: int = 48) -> None:
        self._buf = ""
        self._since_check = 0
        self._check_every = check_every
        self._min_buffer = min_buffer
        self.triggered = False
        self.trimmed = ""

    def push(self, token: str) -> str:
        if self.triggered or not token:
            return ""
        self._buf += token
        self._since_check += len(token)
        if len(self._buf) >= self._min_buffer and self._since_check >= self._check_every:
            self._since_check = 0
            cleaned, cut = collapse_repetition(self._buf, max_consecutive=1)
            # Már 2. ismétlésnél álljunk le streamingnél
            if cut and len(cleaned) < len(self._buf) * 0.92:
                self.triggered = True
                self.trimmed = cleaned
                return ""
        return token

    def finalize(self, full_text: str) -> str:
        cleaned, _ = collapse_repetition(full_text, max_consecutive=1)
        if self.triggered and self.trimmed:
            if len(self.trimmed) <= len(cleaned):
                return self.trimmed
        return cleaned
