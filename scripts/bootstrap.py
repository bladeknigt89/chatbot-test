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
    existed = env_file.is_file()
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from merge_env import merge_env_from_example  # noqa: E402

    added = merge_env_from_example()
    if added:
        if not existed:
            print("Created .env from .env.example")
        else:
            print(f"Updated .env with missing keys: {', '.join(added)}")

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
