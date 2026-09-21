import httpx

from app.embeddings.base import EmbeddingProvider


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        # Új Ollama API: POST /api/embed  {"model", "input": str|list}
        # Legacy fallback: POST /api/embeddings {"model", "prompt"}
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts if len(texts) > 1 else texts[0]},
            )
            if response.status_code == 404:
                return [self._embed_legacy(client, text) for text in texts]
            self._raise_friendly(response)
            data = response.json()
        embeddings = data.get("embeddings")
        if not embeddings:
            raise RuntimeError("Az embedding modell nem adott vissza vektort.")
        if len(embeddings) != len(texts):
            raise RuntimeError(
                f"Az embedding válasz hossza ({len(embeddings)}) nem egyezik a bemenettel ({len(texts)})."
            )
        return [list(vector) for vector in embeddings]

    def _embed_legacy(self, client: httpx.Client, text: str) -> list[float]:
        response = client.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
        )
        self._raise_friendly(response)
        embedding = response.json().get("embedding")
        if not embedding:
            raise RuntimeError("Az embedding modell nem adott vissza vektort.")
        return list(embedding)

    def _raise_friendly(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        detail = ""
        try:
            detail = str(response.json().get("error") or response.text)
        except Exception:
            detail = response.text
        lowered = detail.lower()
        if response.status_code == 404 or "not found" in lowered or "pull" in lowered:
            raise RuntimeError(
                f"Az embedding modell hiányzik vagy nem elérhető: '{self.model}'. "
                f"Futtasd: ollama pull {self.model}. Részlet: {detail}"
            )
        raise httpx.HTTPStatusError(
            f"Ollama embedding hiba ({response.status_code}): {detail}",
            request=response.request,
            response=response,
        )
