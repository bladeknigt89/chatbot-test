"""LLM ismétlés / degenerált hurkok levágása."""

from __future__ import annotations

import re


def collapse_repetition(
    text: str,
    *,
    max_consecutive: int = 2,
    min_unit_chars: int = 6,
    max_unit_chars: int = 160,
) -> tuple[str, bool]:
    """
    Levágja a futó ismétléseket (pl. „vitelkocka eredmény értéke,” ×100).
    Vissza: (tisztított szöveg, volt-e vágás).
    """
    if not text or len(text) < min_unit_chars * (max_consecutive + 1):
        return text, False

    original = text
    out = text
    cut = False

    # 1) Szó-n-gram ismétlés a végén (leggyakoribb LLM-hurok)
    words = re.findall(r"\S+", out)
    if len(words) >= 12:
        for n in range(min(12, len(words) // (max_consecutive + 2)), 2, -1):
            unit = words[-n:]
            reps = 1
            i = len(words) - n
            while i >= n and words[i - n : i] == unit:
                reps += 1
                i -= n
            if reps > max_consecutive:
                keep = words[: i + n * max_consecutive]
                out = " ".join(keep)
                cut = True
                break

    # 2) Karakter-egység ismétlés a végén (vesszős / szóközös frázisok)
    if len(out) >= min_unit_chars * (max_consecutive + 1):
        upper = min(max_unit_chars, len(out) // (max_consecutive + 1))
        for unit_len in range(upper, min_unit_chars - 1, -1):
            unit = out[-unit_len:]
            stripped = unit.strip(" \t,;|-")
            if len(stripped) < min_unit_chars:
                continue
            reps = 1
            pos = len(out) - unit_len
            while pos >= unit_len and out[pos - unit_len : pos] == unit:
                reps += 1
                pos -= unit_len
            if reps > max_consecutive:
                out = out[: pos + unit_len * max_consecutive].rstrip(" \t,;|-")
                cut = True
                break

    # 3) „X, X, X, X” minta (ugyanaz a vesszős tag)
    pattern = re.compile(
        r"(?P<head>[\s\S]*?)(?P<item>[^,:\n]{4,80})(?P<rep>(?:\s*,\s*(?P=item)){3,})\s*$",
        re.IGNORECASE,
    )
    m = pattern.search(out)
    if m:
        item = m.group("item").strip()
        head = m.group("head")
        # tarts 2 példányt
        out = f"{head}{item}, {item}".rstrip(" \t,")
        cut = True

    if cut:
        out = re.sub(r"[ \t]{2,}", " ", out)
        out = re.sub(r" ?, {2,}", ", ", out).rstrip(" ,;\t")
    return out, cut or out != original


class StreamRepetitionGuard:
    """Streaming közben figyeli az ismétlést; triggered = állj le."""

    def __init__(self, *, check_every: int = 24, min_buffer: int = 60) -> None:
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
            cleaned, cut = collapse_repetition(self._buf)
            if cut and len(cleaned) < len(self._buf) * 0.85:
                self.triggered = True
                self.trimmed = cleaned
                return ""
        return token

    def finalize(self, full_text: str) -> str:
        cleaned, _ = collapse_repetition(full_text)
        if self.triggered and self.trimmed:
            if len(self.trimmed) <= len(cleaned):
                return self.trimmed
        return cleaned
