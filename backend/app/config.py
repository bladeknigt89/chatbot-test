from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Local AI Chatbot"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_public_url: str = "http://localhost:8000"
    secret_key: str = "change-this-to-a-long-random-string"
    access_token_expire_minutes: int = 720

    database_url: str = "sqlite:///./storage/app.db"

    llm_provider: str = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434"
    # RAG vázlat + magyar fordítás: llama3.1:8b (RTX 3060 12GB).
    # Opcionális HU modell: puli-llumix (scripts/Modelfile.puli-llumix).
    llm_model: str = "llama3.1:8b"
    llm_temperature: float = 0.15
    llm_num_predict: int = 2048
    llm_repeat_penalty: float = 1.4
    llm_top_p: float = 0.85
    llm_skip_check: bool = False
    llm_polish_enabled: bool = True
    llm_polish_model: str = "llama3.1:8b"
    llm_polish_temperature: float = 0.1

    embedding_provider: str = "ollama"
    embedding_model: str = "nomic-embed-text"
    embedding_base_url: str = "http://127.0.0.1:11434"

    vector_db_path: str = "./storage/vector/vector.db"
    storage_path: str = "./storage/uploads"
    log_path: str = "./storage/logs"

    max_file_size: int = 524_288_000
    chunk_size: int = 500
    chunk_overlap: int = 120
    top_k: int = 20
    # 2-szintű retrieval: először top dokumentumok, aztán chunkok azokból
    doc_route_top_n: int = 12
    doc_route_min_n: int = 3
    doc_route_coarse_k: int = 120
    chunks_per_routed_doc: int = 24

    chat_history_enabled: bool = True
    ocr_enabled: bool = True
    ocr_dpi: int = 160
    ocr_languages: str = "hun+eng"
    tesseract_cmd: str = ""

    login_rate_limit: str = "5/minute"
    chat_rate_limit: str = "30/minute"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8000,http://127.0.0.1:8000,null"
    )

    admin_username: str = "ai"
    admin_password: str = "No_comment_123"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path

    @property
    def storage_dir(self) -> Path:
        return self.resolve_path(self.storage_path)

    @property
    def vector_db_file(self) -> Path:
        return self.resolve_path(self.vector_db_path)

    @property
    def log_dir(self) -> Path:
        return self.resolve_path(self.log_path)

    @property
    def sqlite_db_file(self) -> Path:
        url = self.database_url
        if url.startswith("sqlite:///"):
            raw = url.replace("sqlite:///", "", 1)
            path = Path(raw)
            if not path.is_absolute():
                return ROOT_DIR / path
            return path
        return ROOT_DIR / "storage" / "app.db"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.vector_db_file.parent.mkdir(parents=True, exist_ok=True)
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_db_file.parent.mkdir(parents=True, exist_ok=True)
    return settings
