from pathlib import Path

from tests.conftest import HR_DOC, make_docx, make_pdf, make_xlsx


def test_pdf_parser(tmp_path: Path):
    from app.documents.parsers.pdf import parse_pdf

    path = tmp_path / "doc.pdf"
    path.write_bytes(make_pdf(HR_DOC))
    extracted = parse_pdf(path)
    assert "Example Kft" in extracted.text
    assert extracted.blocks[0].page_number == 1


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
