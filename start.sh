#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x backend/.venv/bin/python ]; then
  echo "A virtuális környezet hiányzik. Futtasd: ./install.sh"
  exit 1
fi

if ! backend/.venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info[:2]==(3,14) else 1)'; then
  echo "A venv nem Python 3.14. Futtasd újra: ./install.sh"
  exit 1
fi

exec backend/.venv/bin/python scripts/start_all.py
