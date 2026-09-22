from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import logging
import re

from pypdf import PdfReader

from app.documents.ocr import PdfOcrSession, page_needs_ocr
from app.documents.parsers.base import ExtractedBlock, ExtractedDocument

logger = logging.getLogger("local_ai_chatbot.pdf")

_SECTION_START = re.compile(r"(?m)^(?=\d{1,2}\.\s+\S)")
ProgressCallback = Callable[[int, int], None]


def parse_pdf(path: Path, on_progress: ProgressCallback | None = None) -> ExtractedDocument:
    reader = PdfReader(str(path))
    total = len(reader.pages)
    page_texts: list[tuple[int, str, bool]] = []
    for index, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = _clean(raw)
        page_texts.append((index, text, page_needs_ocr(text)))
        if on_progress and (index == 1 or index == total or index % 10 == 0):
            on_progress(index, total)

    needs_ocr = [index for index, text, flag in page_texts if flag]
    if needs_ocr:
        logger.info("OCR needed for %s/%s pages in %s", len(needs_ocr), total, path.name)
        with PdfOcrSession(path) as session:
            for i, (index, text, flag) in enumerate(page_texts):
                if not flag:
                    continue
                ocr_text = session.ocr_page(index)
                if ocr_text and len(ocr_text) > len(text):
                    page_texts[i] = (index, ocr_text, flag)
                if on_progress:
                    on_progress(index, total)

    blocks: list[ExtractedBlock] = []
    parts: list[str] = []
    for index, text, _flag in page_texts:
        if not text:
            continue
        page_blocks = _page_sections(text, index)
        blocks.extend(page_blocks)
        parts.append(f"[Oldal {index}]\n{text}")

    try:
        close = getattr(reader, "close", None)
        if callable(close):
            close()
    except Exception:
        pass
    del reader
    del page_texts

    joined = "\n\n".join(parts).strip()
    if not joined:
        raise ValueError(
            "A PDF-ből nem sikerült szöveget kinyerni. "
            "A szkennelt (kép) oldalakat OCR-rel olvassuk; ellenőrizze, hogy az OCR_ENABLED=true, "
            "és a RapidOCR vagy a Tesseract telepítve van."
        )
    return ExtractedDocument(text=joined, blocks=blocks)


def _page_sections(text: str, page_number: int) -> list[ExtractedBlock]:
    """Számozott fejezetekre bontja az oldalt — részletesebb chunkoláshoz."""
    pieces = [part.strip() for part in _SECTION_START.split(text) if part and part.strip()]
    if len(pieces) <= 1:
        return [ExtractedBlock(text=text, page_number=page_number)]

    blocks: list[ExtractedBlock] = []
    for piece in pieces:
        heading = None
        first_line = piece.split("\n", 1)[0].strip()
        match = re.match(r"^(\d{1,2}\.\s+.{3,100})$", first_line)
        if match and len(first_line) < 140:
            heading = match.group(1).strip()
        blocks.append(ExtractedBlock(text=piece, page_number=page_number, heading=heading))
    return blocks


def _clean(value: str) -> str:
    lines = [line.strip() for line in value.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line)
