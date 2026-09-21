from app.documents.chunking import chunk_document
from app.documents.parsers.base import ExtractedBlock, ExtractedDocument


def test_chunking_keeps_section_headings():
    extracted = ExtractedDocument(
        text="ignored",
        blocks=[
            ExtractedBlock(
                text=(
                    "1. Bevezető Rövid szöveg a bevezetőhöz.\n\n"
                    "2. Az egyetem története A Tesztelek Egyetem jogelődje 1998-ban jött létre. "
                    "Az intézmény később több karral bővült."
                ),
                page_number=1,
            )
        ],
    )
    chunks = chunk_document(extracted, chunk_size=180, chunk_overlap=40)
    assert len(chunks) >= 2
    joined = " ".join(c.text for c in chunks)
    assert "egyetem története" in joined.lower()
    assert "1998" in joined


def test_smaller_chunks_are_more_detailed():
    long = " ".join(f"Mondat {i} a részletes tartalomról." for i in range(80))
    extracted = ExtractedDocument(text=long, blocks=[ExtractedBlock(text=long)])
    coarse = chunk_document(extracted, chunk_size=1000, chunk_overlap=150)
    fine = chunk_document(extracted, chunk_size=500, chunk_overlap=120)
    assert len(fine) >= len(coarse)
