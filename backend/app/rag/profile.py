"""Agent-szintű tudásprofil: RPG vs általános (egyetem/HR/support) szeparáció."""

from __future__ import annotations

import re
from typing import Literal

from app.rag.hu_morph import fold_accents

KnowledgeProfile = Literal["auto", "general", "rpg"]
EffectiveProfile = Literal["general", "rpg"]

_RPG_FILENAME = re.compile(
    r"("
    r"\brpg\b|\bttrpg\b|\btrpg\b|roleplaying|role\s*playing|"
    r"rulebook|core\s*rules?|quickstart|sourcebook|"
    r"fallout|cyberpunk|blade\s*runner|deadlands|dark\s*souls|"
    r"legend\s+of\s+the\s+five\s+rings|\bl5r\b|avatar\s*legends|"
    r"dragon\s*age|szerepjatek|szerepjáték"
    r")",
    re.IGNORECASE,
)

_GENERAL_FILENAME = re.compile(
    r"("
    r"egyetem|university|campus|szabalyzat|szabályzat|felveteli|felvételi|"
    r"hallgato|kollegium|kollégium|e-?learning|moodle|tanulmanyi|"
    r"munkaszabalyzat|hr\b|handbook|policy|szervezeti|"
    r"oktatas|oktatás|karok|szakok"
    r")",
    re.IGNORECASE,
)


def infer_profile_from_filenames(filenames: list[str]) -> EffectiveProfile:
    """Dokumentumnevek alapján: rpg vagy general (alapértelmezés: general)."""
    if not filenames:
        return "general"
    rpg = 0
    general = 0
    for name in filenames:
        folded = fold_accents(name or "")
        if _RPG_FILENAME.search(folded) or _RPG_FILENAME.search(name or ""):
            rpg += 1
        if _GENERAL_FILENAME.search(folded) or _GENERAL_FILENAME.search(name or ""):
            general += 1
    if rpg == 0 and general == 0:
        return "general"
    if rpg > general and rpg >= max(1, len(filenames) // 3):
        return "rpg"
    return "general"


def resolve_knowledge_profile(
    configured: str | None,
    *,
    document_names: list[str] | None = None,
) -> EffectiveProfile:
    """auto → fájlnevek; egyébként general|rpg."""
    value = (configured or "auto").strip().lower()
    if value == "rpg":
        return "rpg"
    if value == "general":
        return "general"
    return infer_profile_from_filenames(document_names or [])


def allows_knowledge_catalog(profile: EffectiveProfile) -> bool:
    """RPG-katalógus short-circuit csak rpg profilnál."""
    return profile == "rpg"
