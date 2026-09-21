from app.config import get_settings
from app.embeddings.factory import get_embedding_provider
from app.rag.pipeline import RAGPipeline
from app.vectorstore.store import get_vector_store, reset_vector_store
from app.llm.factory import get_llm_provider
import httpx

AGENT = "3dd1fd3d-2dce-4e2b-9e36-af5efa75cd96"
reset_vector_store()
store = get_vector_store()
emb = get_embedding_provider()
q = "Mi az egyetem története?"
vec = emb.embed_query(q)
matches = store.search(vec, agent_id=AGENT, top_k=8)
print("matches", len(matches))
for m in matches:
    print("---", round(m.score, 4), m.document_name, "chunk", m.chunk_index, "page", m.page_number)
    print(m.text[:350].replace("\n", " | "))

# keyword scan of all chunks
with __import__("sqlite3").connect(str(get_settings().vector_db_file)) as conn:
    rows = conn.execute(
        "SELECT chunk_index, page_number, substr(text,1,200) FROM chunks WHERE agent_id=? AND (lower(text) LIKE '%tortenet%' OR lower(text) LIKE '%történet%' OR lower(text) LIKE '%alapít%' OR text LIKE '%1998%' OR lower(text) LIKE '%múlt%') LIMIT 20",
        (AGENT,),
    ).fetchall()
    print("keyword hits", len(rows))
    for r in rows:
        print(r)

c = httpx.Client(timeout=300)
c.post("http://127.0.0.1:8000/api/auth/login", json={"username": "ai", "password": "No_comment_123"})
r = c.post(
    f"http://127.0.0.1:8000/api/chat/{AGENT}",
    json={"message": q, "stream": False},
)
print("CHAT", r.status_code)
print(r.json().get("message", r.text)[:1500])
print("sources", r.json().get("sources"))
