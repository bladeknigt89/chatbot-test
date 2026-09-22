#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "=== Local AI Chatbot telepítő (Linux) ==="
echo "Elvárt Python: 3.14"

resolve_python() {
  local candidate
  for candidate in python3.14 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info[:2]==(3,14) else 1)'; then
        echo "$candidate"
        return 0
      fi
    fi
  done
  return 1
}

if ! PYEXE="$(resolve_python)"; then
  echo "Python 3.14 nem található."
  echo "Telepítsd a Python 3.14-et, majd futtasd újra: ./install.sh"
  exit 1
fi

echo "Használt Python: $PYEXE"
"$PYEXE" -c 'import sys; print(sys.version)'

if ! command -v node >/dev/null 2>&1; then
  echo "Node.js 20+ szükséges."
  exit 1
fi

echo
echo "=== Ollama telepítés / indítás + modellek (models.json) ==="
set +e
"$PYEXE" scripts/install_ollama.py --models-json models.json
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

if [ -x backend/.venv/bin/python ]; then
  if ! backend/.venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info[:2]==(3,14) else 1)'; then
    echo "A meglévő venv nem Python 3.14. Újraépítem: backend/.venv"
    rm -rf backend/.venv
  fi
fi

if [ ! -x backend/.venv/bin/python ]; then
  echo "Python 3.14 venv létrehozása..."
  "$PYEXE" -m venv backend/.venv
fi

backend/.venv/bin/python -m pip install --upgrade pip
# Natív csomagokhoz Python 3.14 wheel kötelező (ne forrásból fordítson PyO3-mal).
export PIP_ONLY_BINARY="pydantic-core,orjson,pillow,numpy,greenlet,bcrypt,lxml,httptools,watchfiles,websockets,onnxruntime,opencv-python,shapely,pyclipper"
backend/.venv/bin/python -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
unset PIP_ONLY_BINARY

( cd frontend && npm install && npm run build )

backend/.venv/bin/python scripts/install_ollama.py --skip-install --models-json models.json || true
backend/.venv/bin/python scripts/bootstrap.py
backend/.venv/bin/python scripts/make_sample_docs.py

echo
echo "Telepítés kész (Python 3.14). Indítás: ./start.sh"
echo "Admin: http://localhost:8000  felhasználó: ai  jelszó: No_comment_123"
