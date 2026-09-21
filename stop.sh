#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -x backend/.venv/bin/python ]; then
  backend/.venv/bin/python scripts/stop_all.py
else
  echo "Nincs virtuális környezet."
fi
