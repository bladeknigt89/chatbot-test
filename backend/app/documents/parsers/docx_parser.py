from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.documents.parsers.base import ExtractedBlock, ExtractedDocument


def parse_docx(path: Path) -> ExtractedDocument:
    document = Document(str(path))
    blocks: list[ExtractedBlock] = []
    parts: list[str] = []

    for item in _iter_block_items(document):
        if isinstance(item, Paragraph):
            text = item.text.strip()
            if not text:
                continue
            style = item.style.name if item.style is not None else ""
            heading = style if style.lower().startswith("heading") else None
            formatted = f"## {text}" if heading else text
            blocks.append(ExtractedBlock(text=formatted, heading=heading))
            parts.append(formatted)
        elif isinstance(item, Table):
            table_text = _table_to_text(item)
            if table_text:
                blocks.append(ExtractedBlock(text=table_text))
                parts.append(table_text)

    joined = "\n\n".join(parts).strip()
    if not joined:
        raise ValueError("A DOCX fájl nem tartalmaz kinyerhető szöveget.")
    return ExtractedDocument(text=joined, blocks=blocks)


def _iter_block_items(parent):
    from docx.oxml.ns import qn

    body = parent.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            yield Table(child, parent)


def _table_to_text(table: Table) -> str:
    rows: list[str] = []
    for row in table.rows:
        cells = [" ".join(cell.text.split()) for cell in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)
