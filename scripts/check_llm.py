"""Ollama és a models.json-ban megadott modellek ellenőrzése / letöltése."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.bootstrap import ensure_llm_ready  # noqa: E402
from app.config import get_settings  # noqa: E402
from install_ollama import ensure_ollama, load_models_config, model_names_to_pull  # noqa: E402


def main() -> int:
    models_json = ROOT / "models.json"
    config = load_models_config(models_json)
    print("Konfigurált modellek (models.json):")
    for name in model_names_to_pull(config):
        print(f"  - {name}")

    rc = ensure_ollama(
        base_url=str(config.get("base_url") or "http://127.0.0.1:11434"),
        skip_install=False,
        models_json=models_json,
        skip_models=False,
        sync_env=True,
    )
    if rc != 0:
        return rc

    get_settings.cache_clear()
    settings = get_settings()
    ensure_llm_ready(settings, pull=True)
    print(f"LLM: {settings.llm_provider} / {settings.llm_model}")
    print(f"Embedding: {settings.embedding_provider} / {settings.embedding_model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
