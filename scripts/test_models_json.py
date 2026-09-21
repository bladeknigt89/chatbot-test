import json
from pathlib import Path

from install_ollama import (
    DEFAULT_MODELS_CONFIG,
    load_models_config,
    model_names_to_pull,
    sync_env_from_models,
)


def test_default_models_json_matches_builtin(tmp_path: Path):
    root_json = Path(__file__).resolve().parents[1] / "models.json"
    assert root_json.is_file()
    disk = json.loads(root_json.read_text(encoding="utf-8"))
    assert disk["llm"]["model"] == DEFAULT_MODELS_CONFIG["llm"]["model"]
    assert disk["embedding"]["model"] == DEFAULT_MODELS_CONFIG["embedding"]["model"]
    names = model_names_to_pull(disk)
    assert "qwen2.5:7b" in names
    assert "nomic-embed-text" in names


def test_load_models_config_fallback(tmp_path: Path):
    missing = tmp_path / "missing.json"
    cfg = load_models_config(missing)
    assert cfg["llm"]["model"] == "qwen2.5:7b"
    assert model_names_to_pull(cfg) == ["qwen2.5:7b", "nomic-embed-text"]


def test_sync_env_from_models(tmp_path: Path):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "LLM_MODEL=old\nEMBEDDING_MODEL=old-emb\nSECRET_KEY=keep\n",
        encoding="utf-8",
    )
    cfg = load_models_config(Path(__file__).resolve().parents[1] / "models.json")
    sync_env_from_models(cfg, env_path=env_path)
    text = env_path.read_text(encoding="utf-8")
    assert "LLM_MODEL=qwen2.5:7b" in text
    assert "EMBEDDING_MODEL=nomic-embed-text" in text
    assert "SECRET_KEY=keep" in text
