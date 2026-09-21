#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x backend/.venv/bin/python ]; then
  echo "Előbb futtasd: ./install.sh"
  exit 1
fi
exec backend/.venv/bin/python scripts/start_all.py
