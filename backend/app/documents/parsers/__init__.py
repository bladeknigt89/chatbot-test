from pathlib import Path
from collections.abc import Callable

from app.documents.parsers.base import ExtractedDocument
from app.documents.parsers.docx_parser import parse_docx
from app.documents.parsers.excel import parse_excel
from app.documents.parsers.pdf import parse_pdf

ProgressCallback = Callable[[int, int], None]


def parse_document(
    path: Path,
    mime_type: str,
    on_progress: ProgressCallback | None = None,
) -> ExtractedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf" or mime_type == "application/pdf":
        return parse_pdf(path, on_progress=on_progress)
    if suffix == ".docx" or mime_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    }:
        return parse_docx(path)
    if suffix in {".xlsx", ".xls"} or mime_type in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
    }:
        return parse_excel(path)
    raise ValueError("Nem támogatott fájlformátum.")
