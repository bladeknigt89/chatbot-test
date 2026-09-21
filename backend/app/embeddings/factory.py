from functools import lru_cache

from app.config import Settings, get_settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.ollama import OllamaEmbeddingProvider
from app.embeddings.sentence_transformers import SentenceTransformerProvider


def create_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    provider = settings.embedding_provider.lower().strip()
    if provider in {"sentence_transformers", "st", "e5"}:
        return SentenceTransformerProvider(settings.embedding_model)
    return OllamaEmbeddingProvider(settings.embedding_base_url, settings.embedding_model)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return create_embedding_provider()


def reset_embedding_provider() -> None:
    get_embedding_provider.cache_clear()
