from dataclasses import dataclass
import re

from app.documents.parsers.base import ExtractedBlock, ExtractedDocument

_SECTION_SPLIT = re.compile(
    r"(?:\n\s*\n+|\n(?=\d{1,2}\.\s+\S)|(?<=\.)\s+(?=\d{1,2}\.\s+\S)|(?=\n##\s))"
)


@dataclass
class Chunk:
    text: str
    chunk_index: int
    page_number: int | None = None
    sheet_name: str | None = None
    heading: str | None = None


def chunk_document(
    extracted: ExtractedDocument,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    index = 0
    for block in extracted.blocks or [ExtractedBlock(text=extracted.text)]:
        pieces = _split_text(block.text, chunk_size, chunk_overlap, block.heading)
        for piece, heading in pieces:
            chunks.append(
                Chunk(
                    text=piece,
                    chunk_index=index,
                    page_number=block.page_number,
                    sheet_name=block.sheet_name,
                    heading=heading,
                )
            )
            index += 1
    return chunks


def _split_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    initial_heading: str | None = None,
) -> list[tuple[str, str | None]]:
    raw = text.replace("\x00", "").strip()
    if not raw:
        return []

    parts = _SECTION_SPLIT.split(raw)
    paragraphs = [part.strip() for part in parts if part and part.strip()]
    if not paragraphs:
        cleaned = " ".join(raw.split())
        return (
            [(_with_heading(cleaned, initial_heading), initial_heading)]
            if cleaned
            else []
        )

    results: list[tuple[str, str | None]] = []
    current = ""
    heading = initial_heading

    for paragraph in paragraphs:
        compact = " ".join(paragraph.split())
        if not compact:
            continue
        maybe_heading = _detect_heading(compact)
        if maybe_heading:
            heading = maybe_heading

        # Fő fejezet (pl. „7. Karok áttekintése”) soha ne ragadjon az előző szekció végére.
        major = bool(re.match(r"^\d{1,2}\.\s+\S", compact)) and (
            len(compact) < 180 or compact.lower().startswith(heading.lower() if heading else "___")
        )
        if major and current:
            results.append((_with_heading(current.strip(), heading), heading))
            current = ""

        if len(compact) > chunk_size:
            if current:
                results.append((_with_heading(current.strip(), heading), heading))
                current = ""
            for window in _window_split(compact, chunk_size, chunk_overlap):
                results.append((_with_heading(window, heading), heading))
            continue

        # Rövidebb célchunk: ne olvassunk össze túl sok bekezdést.
        soft_limit = max(int(chunk_size * 0.85), chunk_size - 80)
        candidate = f"{current} {compact}".strip() if current else compact
        if len(candidate) <= soft_limit:
            current = candidate
        else:
            if current:
                results.append((_with_heading(current.strip(), heading), heading))
            current = compact
    if current:
        results.append((_with_heading(current.strip(), heading), heading))
    return results


def _detect_heading(paragraph: str) -> str | None:
    if paragraph.startswith("## "):
        return paragraph[3:].strip()[:120]
    match = re.match(r"^(\d{1,2}\.\s+[^.!?]{3,100})(?:\s|$)", paragraph)
    if match and len(paragraph) < 160:
        return match.group(1).strip()
    return None


def _with_heading(text: str, heading: str | None) -> str:
    if not heading:
        return text
    if heading.lower() in text.lower()[: len(heading) + 40]:
        return text
    return f"{heading}\n{text}"


def _window_split(cleaned: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    if len(cleaned) <= chunk_size:
        return [cleaned]
    overlap = min(chunk_overlap, max(chunk_size // 3, 40))
    results: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + chunk_size, len(cleaned))
        if end < len(cleaned):
            window = cleaned[start:end]
            split_at = max(
                window.rfind(". "),
                window.rfind("? "),
                window.rfind("! "),
                window.rfind("; "),
                window.rfind(", "),
                window.rfind(" "),
            )
            if split_at > chunk_size * 0.35:
                end = start + split_at + 1
        piece = cleaned[start:end].strip()
        if piece:
            results.append(piece)
        if end >= len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return results
