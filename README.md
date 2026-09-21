# Local AI Chatbot

Lokális, dokumentumalapú, több-agentes RAG chatbot platform. A rendszer Windows-on és Linuxon is futtatható, az első telepítés után internet nélkül működik, és nem függ felhős LLM API-tól.

## 1. Projekt célja

Adminisztrátorok agenteket hozhatnak létre, agentenként PDF/DOCX/XLSX tudásbázist tölthetnek fel, a rendszer embeddinget készít, lokális vector store-ban tárolja, majd helyi LLM-mel, RAG-gel válaszol. Minden agent tudásbázisa izolált. A chat widget külső oldalba ágyazható, a REST API API kulccsal védhető.

## 2. Architektúra

```
Böngésző / widget / curl
        │
        ▼
 FastAPI (REST, admin UI, OpenAPI, widget JS)
        │
        ├── SQLite (users, agents, documents, keys, audit, jobs, chat)
        ├── Worker (parse → chunk → embed)
        ├── SQLite vector store (cosine + agent_id szűrés)
        └── Ollama (LLM + embedding)
```

A dokumentumfeltöltés 202-t ad vissza, a feldolgozás háttérjobban fut.

## 3. Technológiák

| Réteg | Választás | Indok |
| --- | --- | --- |
| Backend | Python 3.14, FastAPI, SQLAlchemy 2, Alembic | Stabil REST, Windows-barát, PostgreSQL-re migrálható |
| Frontend | React + TypeScript + Vite | Modern, reszponzív admin UI |
| LLM | Ollama + `qwen2.5:7b` | Ingyenes, lokális, CPU/GPU, jó magyar támogatás |
| Embedding | Ollama + `nomic-embed-text` | Ugyanaz a runtime, egyszerű telepítés |
| Vector store | Saját SQLite + NumPy cosine | Nincs extra natív függőség, metadata filter natív |
| Dokumentumok | pypdf, python-docx, openpyxl, xlrd | PDF/DOCX/XLSX/XLS |

## 4. Előfeltételek

- Windows 10/11 vagy Linux
- Python 3.14 (kötelező; az installer / start ellenőrzi)
- Node.js 20+
- Internet az első telepítéshez (függőségek + Ollama + modellek)
- Ajánlott: 16 GB RAM (7B modellhez)

A backend függőségek (pydantic-core, orjson, pillow, numpy stb.) Python 3.14-es előreépített wheel-eket használnak; régi pinelt verziók forrásból fordításkor PyO3 hibával elbukhatnak.

Az Ollama runtime-ot az installer automatikusan telepíti, ha még nincs a gépen.

## 5. Windows telepítés

```bat
install.bat
start.bat
```

Leállítás:

```bat
stop.bat
```

Az `install.bat` sorrendben:

1. ellenőrzi a **Python 3.14** / Node előfeltételeket (`py -3.14` vagy `python`);
2. **telepíti az Ollamát** (`winget` vagy `OllamaSetup.exe`), majd elindítja;
3. létrehozza a `.env` fájlt és a Python **3.14** venv-et (régi venv-et újraépíti, ha nem 3.14);
4. telepíti a backend és frontend függőségeket, lebuildeli az admin UI-t;
5. inicializálja az adatbázist és az `ai` admin felhasználót;
6. a `models.json` alapján letölti a hiányzó LLM / embedding modelleket, és szinkronizálja a `.env`-et.

Docker runtime: `docker/backend.Dockerfile` → `python:3.14-slim`.

Külön Ollama telepítés / újraindítás:

```bat
python scripts\install_ollama.py --models-json models.json
```

## 6. Linux telepítés

```bash
chmod +x install.sh start.sh stop.sh
./install.sh
./start.sh
```

Az `install.sh` a hivatalos `https://ollama.com/install.sh` scripttel telepíti az Ollamát, ha hiányzik, elindítja a szolgáltatást, majd a többi komponenst is felépíti.

Külön:

```bash
python3 scripts/install_ollama.py --models-json models.json
```

## 7. Docker telepítés

Az Ollama a hoston fusson (GPU miatt ez a stabilabb út). Hoston előbb:

```bash
# ha nincs Ollama a hoston:
python3 scripts/install_ollama.py --models-json models.json
```

Majd:

```bash
# A modelleket a telepítő a models.json alapján is letölti.
# Kézi alternatíva:
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
copy .env.example .env   # Windows
# cp .env.example .env   # Linux
docker compose up --build
```

Az admin a `http://localhost:8000` címen érhető el. A compose a host Ollamáját a `host.docker.internal:11434` címen éri el.

## 8. LLM telepítés

1. Az `install.bat` / `install.sh` automatikusan telepíti és indítja az Ollamát.
2. Windows: `winget install Ollama.Ollama`, ha a winget nem elérhető, `OllamaSetup.exe` letöltése.
3. Linux: hivatalos `curl https://ollama.com/install.sh | sh` alapú telepítés.
4. A modellek listáját a gyökérbeli `models.json` adja meg (default: `qwen2.5:7b` + `nomic-embed-text`).
5. Ellenőrzés: `ollama list` vagy `python scripts/check_llm.py`
6. A bootstrap / start script automatikusan húzza a hiányzó modelleket.

## 9. Választott modellek

A forrás: `models.json` (LLM + embedding + pull lista). Csere: szerkeszd a JSON-t, futtasd újra:

```bat
python scripts\install_ollama.py --models-json models.json
```

### LLM: `qwen2.5:7b`

- Méret: kb. 4,7 GB (Q4_K_M, Ollama default)
- Miért: erős többnyelvű instruction-following, magyar RAG-re jól használható, 7B kategória, CPU-n is fut, GPU-n gyors
- RAM: legalább 8 GB, ajánlott 16 GB
- VRAM: 6 GB+ ha GPU-t használsz

### Embedding: `nomic-embed-text`

- Méret: kb. 274 MB
- Miért: Ollamán keresztül telepíthető, nem kell külön PyTorch a venv-be, metadata-s RAG-hez megfelelő
- Magyar: működik; ha erősebb magyar retrieval kell, válts `EMBEDDING_PROVIDER=sentence_transformers` és `EMBEDDING_MODEL=intfloat/multilingual-e5-small` értékre (külön `sentence-transformers` telepítés kell)

Letöltés kézzel:

```bat
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

Frissítés:

```bat
ollama pull qwen2.5:7b
```

Csere: szerkeszd a `models.json` fájlt (és opcionálisan a `.env`-et), majd futtasd:
`python scripts/install_ollama.py --models-json models.json`. A kód nem hardcode-olja a modellnevet.

## 10. Adatbázis inicializálás

Az `install.bat` / `scripts/bootstrap.py` létrehozza a táblákat (SQLAlchemy metadata + Alembic migráció a `backend/alembic` alatt). A bináris dokumentumok a `storage/uploads` mappában vannak, az embeddingek a `storage/vector/vector.db` fájlban.

Kézi bootstrap:

```bat
backend\.venv\Scripts\python.exe scripts\bootstrap.py
```

## 11. Első indítás

```bat
start.bat
```

Nyisd meg: [http://localhost:8000](http://localhost:8000)

Swagger: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

## 12. Admin belépés

- Felhasználónév: `ai`
- Jelszó: `No_comment_123`

A jelszó a Profil oldalon módosítható. Soha nincs plain textben tárolva (bcrypt).

## 13. Agent létrehozás

Admin → Agentek → név, leírás, system prompt. Az agentek tudásbázisa egymástól el van zárva; a vector keresés kötelezően `agent_id` szerint szűr.

## 14. Dokumentum feltöltés

Támogatott: PDF, DOCX, XLSX, XLS. Feltöltés után státuszok: `UPLOADED` → `PROCESSING` (parsing / chunking / embedding) → `READY` vagy `ERROR`.

Szkennelt PDF-hez opcionális OCR: telepíts Tesseractet, `pip install pytesseract pdf2image`, `OCR_ENABLED=true`.

## 15. Chatbot használata

Az agent részletező oldalán próba chat van. A válaszok forráshivatkozást is mutathatnak, kizárólag a retrieval metadata alapján.

Ha nincs releváns rész:

`A rendelkezésre álló dokumentumok alapján erre nem található megfelelő információ.`

## 16. Widget beágyazása

```html
<script>
window.ChatWidgetConfig = {
  primaryColor: "#c45c26",
  title: "HR Segéd",
  position: "right",
  welcomeMessage: "Üdvözlöm! Miben segíthetek?"
};
</script>
<script
  src="http://localhost:8000/chat-widget.js"
  data-agent="AGENT_ID"
  data-api-key="API_KEY">
</script>
```

A widget nem tölti be az admin UI-t. Agentenkénti színek, cím, pozíció és üdvözlés az agent szerkesztőben is beállítható.

## 17. API kulcs

Admin → API kulcsok. A teljes kulcs csak létrehozáskor látszik. Tárolás: SHA-256 hash. Visszavonható és törölhető.

## 18. API használat

```bat
curl -X POST http://localhost:8000/api/agents ^
  -H "Authorization: Bearer YOUR_API_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"HR Agent\",\"description\":\"HR dokumentumok\"}"
```

Dokumentum feltöltés:

```bat
curl -X POST http://localhost:8000/api/agents/AGENT_ID/documents ^
  -H "Authorization: Bearer YOUR_API_KEY" ^
  -F "file=@tests/sample_docs/munkaszabalyzat.pdf"
```

Dokumentum törlés:

```bat
curl -X DELETE http://localhost:8000/api/agents/AGENT_ID/documents/DOCUMENT_ID ^
  -H "Authorization: Bearer YOUR_API_KEY"
```

Chat:

```bat
curl -X POST http://localhost:8000/api/chat/AGENT_ID ^
  -H "Authorization: Bearer YOUR_API_KEY" ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Mi a vállalat neve?\",\"stream\":false}"
```

API kulcs kezelés (admin cookie vagy login után):

```bat
curl -X POST http://localhost:8000/api/keys ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"widget\"}" --cookie "lac_session=..."
```

Linux/macOS példák ugyanazok, a `^` helyett `\` sortöréssel.

## 19. Swagger

[http://localhost:8000/api/docs](http://localhost:8000/api/docs)

Minden végpontnál: autentikáció, request/response sémák, hibakódok. Authorize: Bearer API kulcs.

## 20. Tesztek

```bat
cd backend
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check app tests

cd ..\frontend
npm test
npm run build
```

A backend tesztek fake embedding/LLM double-t használnak, a parser, a feltöltés, az agent izoláció és a security valós kódon fut. Production módban nincs mock AI válasz.

## 21. Konfiguráció

Másold az `.env.example` fájlt `.env` névre. Fontosabb kulcsok:

```
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
EMBEDDING_MODEL=nomic-embed-text
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K=5
MAX_FILE_SIZE=26214400
CHAT_HISTORY_ENABLED=true
```

Titkokat ne commitolj. A `SECRET_KEY`-t élesben cseréld le.

## 22. Hibaelhárítás

| Tünet | Teendő |
| --- | --- |
| Ollama nem érhető el | Futtasd: `python scripts/install_ollama.py --models-json models.json`, vagy indítsd: `ollama serve`. Ellenőrizd: `LLM_BASE_URL=http://127.0.0.1:11434` |
| Ollama winget msstore hiba | A telepítő `--source winget` forrást használ. Ha ez sem megy, automatikusan `OllamaSetup.exe`-t tölt le. |
| OllamaSetup.exe letöltés elakad | Ellenőrizd a hálózatot / tűzfalat, vagy töltsd le kézzel: https://ollama.com/download |
| Hiányzó modell | `ollama pull qwen2.5:7b` és `ollama pull nomic-embed-text` |
| Dokumentum ERROR, kép-PDF | Tesseract + `OCR_ENABLED=true` |
| Frontend 404 a gyökéren | `cd frontend && npm run build`, majd indítsd újra a backendet |
| Port foglalt | `APP_PORT` módosítása a `.env`-ben |
| Worker nem dolgoz | `start.bat` indítja; log: `storage/logs/worker.log` |

## 23. Hardverkövetelmények

- CPU-only 7B: 16 GB RAM, lassú, de működik
- GPU: 6 GB+ VRAM a 7B-hez
- 14B modellhez (`qwen2.5:14b`): 24 GB RAM / 10 GB+ VRAM
- Lemez: ~8 GB a modelleknek + a dokumentumoknak

## 24. Ismert korlátozások

- Az alap embedding (`nomic-embed-text`) angol-központú, magyarul használható, de az `e5-small` pontosabb retrieval-t adhat.
- Az SQLite vector search memóriában számol cosine-t agentenként; százezres chunk-skálán PostgreSQL + pgvector a következő lépés.
- Az OCR nem kötelező komponens, Tesseract nélkül a kép-PDF-ek hibára futnak.
- A Docker-összeállítás az LLM-et a host Ollamára bízza, hogy a GPU-t ne kelljen konténerben külön kezelni.

## Gyors RAG próba

1. Hozz létre egy HR agentet.
2. Töltsd fel a `tests/sample_docs/munkaszabalyzat.pdf` fájlt (az `install` legenerálja).
3. Kérdezd: „Mi a vállalat neve?”, „Mikor van a munkaidő?”, „Hány nap szabadság jár?”
4. Ellenőrző kérdés, amire nem szabad kitalálnia: „Mennyi a vállalat éves árbevétele?”
