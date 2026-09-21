from pathlib import Path

import httpx
from pypdf import PdfReader

PDF = Path(r"C:\Users\Blade's_MSI\Downloads\Tesztelek Egyetem.pdf")

c = httpx.Client(timeout=60)
c.post("http://127.0.0.1:8000/api/auth/login", json={"username": "ai", "password": "No_comment_123"})
agents = c.get("http://127.0.0.1:8000/api/agents").json()
target = None
for a in agents:
    print("AGENT", a["id"], a["name"], a["status"], "docs", a["document_count"])
    docs = c.get(f"http://127.0.0.1:8000/api/agents/{a['id']}/documents").json()
    for d in docs:
        print(
            "  DOC",
            d["id"],
            d["original_filename"],
            d["status"],
            d["processing_stage"],
            "chunks=",
            d["chunk_count"],
            "err=",
            d.get("error_message"),
        )
    if "pte" in a["name"].lower() or "teszt" in a["name"].lower():
        target = a

print("PDF exists", PDF.exists(), "size", PDF.stat().st_size if PDF.exists() else None)
if PDF.exists():
    reader = PdfReader(str(PDF))
    print("pages", len(reader.pages))
    for i, page in enumerate(reader.pages[:5], 1):
        text = page.extract_text() or ""
        print(f"--- page {i} chars={len(text)}")
        print(text[:600].replace("\n", " | "))

if target:
    print("TARGET", target["name"], target["id"])
    r = c.post(
        f"http://127.0.0.1:8000/api/chat/{target['id']}",
        json={"message": "Mi az egyetem története?", "stream": False},
    )
    print("chat status", r.status_code)
    print(r.text[:2000])
