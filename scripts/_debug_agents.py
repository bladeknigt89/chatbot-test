import httpx
from pathlib import Path

c = httpx.Client(timeout=60)
c.post("http://127.0.0.1:8000/api/auth/login", json={"username": "ai", "password": "No_comment_123"})
agents = c.get("http://127.0.0.1:8000/api/agents").json()
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
            d["chunk_count"],
            d.get("error_message"),
        )
