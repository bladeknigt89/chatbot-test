import logging

import httpx
from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import Base, get_engine
from app.models import SystemSetting, User
from app.security import hash_password

logger = logging.getLogger("local_ai_chatbot.bootstrap")


def ensure_directories(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_db_file.parent.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_db_file.parent.mkdir(parents=True, exist_ok=True)


def create_schema() -> None:
    Base.metadata.create_all(bind=get_engine())
    _ensure_document_progress_column()


def _ensure_document_progress_column() -> None:
    """SQLite create_all nem ad új oszlopot meglévő táblához — pótoljuk."""
    engine = get_engine()
    with engine.begin() as conn:
        rows = conn.execute(sa_text("PRAGMA table_info(documents)")).fetchall()
        columns = {row[1] for row in rows}
        if "progress_percent" not in columns:
            conn.execute(
                sa_text(
                    "ALTER TABLE documents ADD COLUMN progress_percent INTEGER NOT NULL DEFAULT 0"
                )
            )


def seed_admin(db: Session, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    existing = db.query(User).filter(User.username == settings.admin_username).first()
    if existing:
        return
    user = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
    )
    db.add(user)
    db.commit()
    logger.info("Initial admin user created: %s", settings.admin_username)


def seed_settings(db: Session, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    defaults = {
        "CHAT_HISTORY_ENABLED": "true" if settings.chat_history_enabled else "false",
    }
    for key, value in defaults.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if not row:
            db.add(SystemSetting(key=key, value=value))
    db.commit()


def get_setting_bool(db: Session, key: str, default: bool) -> bool:
    row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if not row:
        return default
    return row.value.lower() in {"1", "true", "yes", "on"}


def check_ollama(settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    base = settings.llm_base_url.rstrip("/")
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base}/api/tags")
            response.raise_for_status()
            models = [item.get("name", "") for item in response.json().get("models", [])]
        return {"ok": True, "models": models, "error": None}
    except Exception as exc:
        return {"ok": False, "models": [], "error": str(exc)}


def model_installed(models: list[str], name: str) -> bool:
    short = name.split(":")[0]
    for item in models:
        if item == name or item.startswith(name) or item.split(":")[0] == short and ":" not in name:
            return True
        if item.split(":")[0] == short:
            return True
    return False


def pull_model(name: str, base_url: str) -> None:
    logger.info("Pulling Ollama model: %s", name)
    with httpx.Client(timeout=None) as client:
        with client.stream("POST", f"{base_url.rstrip('/')}/api/pull", json={"name": name}) as response:
            response.raise_for_status()
            for _line in response.iter_lines():
                pass
    logger.info("Model ready: %s", name)


def ensure_llm_ready(settings: Settings | None = None, pull: bool = True) -> None:
    settings = settings or get_settings()
    if settings.llm_skip_check or settings.app_env == "test":
        return
    status = check_ollama(settings)
    if not status["ok"]:
        raise RuntimeError(
            "Az Ollama nem érhető el. Telepítsd és indítsd el: https://ollama.com "
            f"({settings.llm_base_url}). Részlet: {status['error']}"
        )
    needed = []
    if settings.llm_provider == "ollama" and not model_installed(status["models"], settings.llm_model):
        needed.append((settings.llm_model, settings.llm_base_url))
    if settings.embedding_provider == "ollama" and not model_installed(
        status["models"], settings.embedding_model
    ):
        needed.append((settings.embedding_model, settings.embedding_base_url))
    if needed and not pull:
        names = ", ".join(item[0] for item in needed)
        raise RuntimeError(f"Hiányzó Ollama modellek: {names}. Futtasd: ollama pull <modell>")
    for name, base in needed:
        pull_model(name, base)
