"""Egyszerű magyar szótő-közelítés RAG kulcsszó-egyezéshez.

Nem teljes morfológiai elemző: atomikus toldalékok iteratív levágása
(többes + rag + birtokos), majd tőegyeztetés.
"""

from __future__ import annotations

import re
import unicodedata

_RAW_SUFFIXES: tuple[str, ...] = (
    "jaink",
    "jeink",
    "jaitok",
    "jeitek",
    "jaik",
    "jeik",
    "aink",
    "eink",
    "aitok",
    "eitek",
    "aik",
    "eik",
    "jaim",
    "jeim",
    "jaid",
    "jeid",
    "jai",
    "jei",
    "aim",
    "eim",
    "aid",
    "eid",
    "ait",
    "eit",
    "okat",
    "eket",
    "akat",
    "ai",
    "ei",
    "junk",
    "juk",
    "unk",
    "ja",
    "je",
    "kent",
    "ban",
    "ben",
    "nak",
    "nek",
    "val",
    "vel",
    "ert",
    "hoz",
    "hez",
    "rol",
    "tol",
    "nal",
    "nel",
    "abol",
    "ebol",
    "bol",
    "ba",
    "be",
    "ra",
    "re",
    "ig",
    "ul",
    "va",
    "ve",
    "in",
    "ok",
    "ek",
    "ak",
    "abb",
    "ebb",
    "sag",
    "seg",
    "lag",
    "leg",
    "an",
    "en",
    "on",
    "at",
    "et",
    "ot",
)

# Csak a szó végén, első lépésben engedélyezett „könnyű” ragok (tárgyrag stb.).
_LIGHT_SUFFIXES = frozenset({"at", "et", "ot", "an", "en", "on", "in", "ul", "va", "ve"})

_SEEN: set[str] = set()
_ORDERED: list[str] = []
for _s in _RAW_SUFFIXES:
    _f = "".join(
        ch
        for ch in unicodedata.normalize("NFD", _s.lower())
        if unicodedata.category(ch) != "Mn"
    )
    if _f and _f not in _SEEN:
        _SEEN.add(_f)
        _ORDERED.append(_f)
_SUFFIXES = tuple(sorted(_ORDERED, key=len, reverse=True))

_STOPWORDS = {
    "a",
    "az",
    "egy",
    "es",
    "és",
    "vagy",
    "hogy",
    "van",
    "volt",
    "lesz",
    "mi",
    "mit",
    "milyen",
    "melyik",
    "melyek",
    "mikor",
    "hol",
    "ki",
    "kik",
    "kit",
    "kiket",
    "mennyi",
    "hany",
    "hány",
    "the",
    "and",
    "or",
    "is",
    "are",
    "what",
    "when",
    "where",
    "who",
    "how",
    "please",
    "foglald",
    "ossze",
    "össze",
    "roviden",
    "röviden",
    "sorold",
    "felsorol",
    "felsorold",
    "listazd",
    "neveld",
    "nevezd",
    "fel",
    "osszes",
    "összes",
    "mind",
    "ilyen",
    "olyan",
    "ez",
    "azt",
    "ezt",
    "itt",
    "ott",
    "mar",
    "már",
    "meg",
    "csak",
    "nem",
    "igen",
    "kell",
    "lehet",
}


def fold_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _min_stem_for(suf: str) -> int:
    if suf in {"ok", "ek", "ak", "okat", "eket", "akat"}:
        return 2
    if suf in _LIGHT_SUFFIXES:
        return 4
    if len(suf) <= 2:
        return 5
    if len(suf) == 3:
        return 4
    return 3


def strip_one_suffix(token: str, *, allow_light: bool = True) -> tuple[str, str] | None:
    for suf in _SUFFIXES:
        if not allow_light and suf in _LIGHT_SUFFIXES:
            continue
        if not token.endswith(suf):
            continue
        # Rövid töveken ne bontsuk tovább a többest (szak → sz).
        if suf in {"ok", "ek", "ak"} and len(token) <= 4:
            continue
        stem = token[: -len(suf)]
        if len(stem) >= _min_stem_for(suf):
            return stem, suf
    return None


def stem_hu(token: str, *, max_steps: int = 5) -> str:
    """hallgatóknak → hallgatók → hallgat(o); karokat → kar; történetet → történet."""
    token = fold_accents(token)
    if len(token) <= 2:
        return token
    for step in range(max_steps):
        # Könnyű rag csak az első lépésben (különben szabályzat → szabályz).
        stripped = strip_one_suffix(token, allow_light=(step == 0))
        if not stripped:
            break
        nxt, _suf = stripped
        if nxt == token:
            break
        token = nxt
    return token


def stems_hu(token: str) -> set[str]:
    folded = fold_accents(token)
    out = {folded, stem_hu(folded)}
    cur = folded
    for step in range(5):
        stripped = strip_one_suffix(cur, allow_light=(step == 0))
        if not stripped:
            break
        nxt, _suf = stripped
        if nxt == cur:
            break
        out.add(nxt)
        cur = nxt
    for form in list(out):
        if form.endswith("i") and len(form) > 3:
            out.add(form[:-1])
        # Magánhangzós tő többes: hallgatók → hallgató (folded: hallgatok → hallgato)
        if form.endswith("ok") and len(form) > 4 and form[-3] in "aeiou":
            # ha C+V+k alak, a V a tő része lehet
            pass
        if len(form) >= 5 and form[-1] == "k" and form[-2] in "aeiou" and form[-3] not in "aeiou":
            out.add(form[:-1])
    return {s for s in out if len(s) >= 2}


def tokenize(value: str) -> list[str]:
    folded = fold_accents(value)
    tokens = re.findall(r"[a-z0-9]+", folded)
    return [tok for tok in tokens if len(tok) > 2 and tok not in _STOPWORDS]


def longest_common_prefix(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def tokens_match(a: str, b: str) -> bool:
    if not a or not b:
        return False
    a, b = fold_accents(a), fold_accents(b)
    if a == b:
        return True
    stems_a = stems_hu(a)
    stems_b = stems_hu(b)
    if stems_a & stems_b:
        return True
    for sa in stems_a:
        for sb in stems_b:
            lcp = longest_common_prefix(sa, sb)
            if lcp < 3:
                continue
            shorter = min(len(sa), len(sb))
            if lcp >= max(3, int(shorter * 0.7)):
                if (len(sa) - lcp) <= 4 and (len(sb) - lcp) <= 4:
                    return True
    return False


def expand_query_tokens(tokens: list[str]) -> set[str]:
    out: set[str] = set()
    for tok in tokens:
        out |= stems_hu(tok)
    return out
