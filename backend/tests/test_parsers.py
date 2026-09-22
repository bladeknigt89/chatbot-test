from pathlib import Path

import pytest

from tests.conftest import HR_DOC, make_docx, make_image_pdf, make_pdf, make_xlsx


def test_pdf_parser(tmp_path: Path):
    from app.documents.parsers.pdf import parse_pdf

    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf(HR_DOC))
    extracted = parse_pdf(path)
    assert "Example Kft" in extracted.text
    assert extracted.blocks[0].page_number == 1


def test_image_pdf_uses_ocr(tmp_path: Path, monkeypatch):
    from app.documents.ocr import page_needs_ocr
    from app.documents.parsers import pdf as pdf_parser

    assert page_needs_ocr("")
    assert page_needs_ocr("12")
    assert not page_needs_ocr(HR_DOC)

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ocr_page(self, _page: int) -> str:
            return "Example Kft szkennelt oldal"

    monkeypatch.setattr(pdf_parser, "PdfOcrSession", lambda _path: FakeSession())
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_image_pdf("Example Kft"))
    extracted = pdf_parser.parse_pdf(path)
    assert "Example Kft" in extracted.text
    assert extracted.blocks[0].page_number == 1


def test_image_pdf_without_ocr_fails(tmp_path: Path, monkeypatch):
    from app.documents.parsers import pdf as pdf_parser

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def ocr_page(self, _page: int) -> str:
            return ""

    monkeypatch.setattr(pdf_parser, "PdfOcrSession", lambda _path: FakeSession())
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_image_pdf("Example Kft"))
    with pytest.raises(ValueError, match="OCR"):
        pdf_parser.parse_pdf(path)


def test_scanned_pdf_live_ocr(tmp_path: Path, monkeypatch):
    from app.config import get_settings
    from app.documents.parsers.pdf import parse_pdf

    monkeypatch.setenv("OCR_ENABLED", "true")
    get_settings.cache_clear()
    path = tmp_path / "scan.pdf"
    path.write_bytes(make_image_pdf("Example Kft"))
    extracted = parse_pdf(path)
    assert "Example" in extracted.text


def test_docx_parser(tmp_path: Path):
    from app.documents.parsers.docx_parser import parse_docx

    path = tmp_path / "doc.docx"
    path.write_bytes(
        make_docx(
            ["Bevezetés", "A vállalat neve: Example Kft."],
            [[["Név", "Beosztás"], ["Kiss Péter", "Fejlesztő"]]],
        )
    )
    extracted = parse_docx(path)
    assert "Example Kft" in extracted.text
    assert "Kiss Péter" in extracted.text


def test_xlsx_parser(tmp_path: Path):
    from app.documents.parsers.excel import parse_excel

    path = tmp_path / "doc.xlsx"
    path.write_bytes(
        make_xlsx({"Dolgozók": [["Név", "Beosztás", "Fizetés"], ["Nagy Anna", "Projektvezető", "900000"]]})
    )
    extracted = parse_excel(path)
    assert "Dolgozók" in extracted.text
    assert "Nagy Anna" in extracted.text
    assert extracted.blocks[0].sheet_name == "Dolgozók"
