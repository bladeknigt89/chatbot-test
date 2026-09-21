"""Adatbázis, könyvtárak és kezdeti admin inicializálása."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.bootstrap import (  # noqa: E402
    create_schema,
    ensure_directories,
    ensure_llm_ready,
    seed_admin,
    seed_settings,
)
from app.config import get_settings  # noqa: E402
from app.database import configure_engine, get_session_factory  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Local AI Chatbot bootstrap")
    parser.add_argument("--skip-llm", action="store_true")
    args = parser.parse_args()

    env_file = ROOT / ".env"
    example = ROOT / ".env.example"
    if not env_file.exists() and example.exists():
        env_file.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        print("Created .env from .env.example")

    get_settings.cache_clear()
    settings = get_settings()
    ensure_directories(settings)
    configure_engine(settings.database_url)
    create_schema()
    db = get_session_factory()()
    try:
        seed_admin(db, settings)
        seed_settings(db, settings)
    finally:
        db.close()
    print("Database and admin user are ready.")
    if not args.skip_llm:
        ensure_llm_ready(settings, pull=True)
        print("LLM runtime and models are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
