from functools import lru_cache

from app.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.ollama import OllamaLLMProvider


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider != "ollama":
        raise RuntimeError(f"Nem támogatott LLM provider: {provider}")
    return OllamaLLMProvider(settings.llm_base_url, settings.llm_model)


def create_polish_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Nyelvi javító modell — alapból ugyanaz, mint a fő LLM."""
    settings = settings or get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider != "ollama":
        raise RuntimeError(f"Nem támogatott LLM provider: {provider}")
    model = (settings.llm_polish_model or settings.llm_model).strip()
    return OllamaLLMProvider(settings.llm_base_url, model)


@lru_cache
def get_llm_provider() -> LLMProvider:
    return create_llm_provider()


@lru_cache
def get_polish_llm_provider() -> LLMProvider:
    return create_polish_llm_provider()


def reset_llm_provider() -> None:
    get_llm_provider.cache_clear()
    get_polish_llm_provider.cache_clear()
