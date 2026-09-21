from app.embeddings.base import EmbeddingProvider


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "A sentence-transformers csomag nincs telepítve. "
                "Telepítsd, vagy használd az EMBEDDING_PROVIDER=ollama beállítást."
            ) from exc
        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def embed_query(self, text: str) -> list[float]:
        prefixed = text if "e5" not in self.model_name.lower() else f"query: {text}"
        return self._model.encode(prefixed, normalize_embeddings=True).tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if "e5" in self.model_name.lower():
            texts = [f"passage: {item}" for item in texts]
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]
