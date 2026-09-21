#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Local AI Chatbot telepítő (Linux) ==="

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11+ szükséges."
  exit 1
fi
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js 20+ szükséges."
  exit 1
fi

echo
echo "=== Ollama telepítés / indítás + modellek (models.json) ==="
set +e
python3 scripts/install_ollama.py --models-json models.json
OLLAMA_RC=$?
set -e
if [ "$OLLAMA_RC" -ne 0 ]; then
  echo
  echo "FIGYELEM: Az Ollama telepítése, indítása vagy a modell letöltés nem sikerült teljesen."
  echo "Ha most települt, indítsd újra a terminált / rendszert, majd futtasd újra: ./install.sh"
  echo
  echo "Folytatás a többi komponenssel..."
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo ".env létrehozva."
fi

if [ ! -x backend/.venv/bin/python ]; then
  python3 -m venv backend/.venv
fi

backend/.venv/bin/python -m pip install --upgrade pip
backend/.venv/bin/python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt

( cd frontend && npm install && npm run build )

backend/.venv/bin/python scripts/install_ollama.py --skip-install --models-json models.json || true
backend/.venv/bin/python scripts/bootstrap.py
backend/.venv/bin/python scripts/make_sample_docs.py

echo
echo "Telepítés kész. Indítás: ./start.sh"
echo "Admin: http://localhost:8000  felhasználó: ai  jelszó: No_comment_123"
