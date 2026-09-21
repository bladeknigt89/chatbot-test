from pathlib import Path
import re

from pypdf import PdfReader

from app.config import get_settings
from app.documents.parsers.base import ExtractedBlock, ExtractedDocument

_SECTION_START = re.compile(r"(?m)^(?=\d{1,2}\.\s+\S)")


def parse_pdf(path: Path) -> ExtractedDocument:
    reader = PdfReader(str(path))
    blocks: list[ExtractedBlock] = []
    parts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = _clean(raw)
        if not text:
            text = _ocr_page(path, index)
        if not text:
            continue
        page_blocks = _page_sections(text, index)
        blocks.extend(page_blocks)
        parts.append(f"[Oldal {index}]\n{text}")
    joined = "\n\n".join(parts).strip()
    if not joined:
        raise ValueError(
            "A PDF-ből nem sikerült szöveget kinyerni. "
            "Ha a dokumentum szkennelt, telepítse a Tesseract OCR-t és állítsa OCR_ENABLED=true értékre."
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


def _ocr_page(path: Path, page_number: int) -> str:
    settings = get_settings()
    if not settings.ocr_enabled:
        return ""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        return ""
    try:
        images = convert_from_path(str(path), first_page=page_number, last_page=page_number)
        if not images:
            return ""
        return _clean(pytesseract.image_to_string(images[0], lang="hun+eng"))
    except Exception:
        return ""


def _clean(value: str) -> str:
    lines = [line.strip() for line in value.replace("\x00", "").splitlines()]
    return "\n".join(line for line in lines if line)
