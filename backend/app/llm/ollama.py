from collections.abc import Iterator

import httpx

from app.config import get_settings
from app.llm.base import LLMProvider
from app.llm.repetition import StreamRepetitionGuard, collapse_repetition


class OllamaLLMProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _options(self, temperature: float) -> dict:
        settings = get_settings()
        options: dict = {"temperature": temperature}
        if settings.llm_num_predict and settings.llm_num_predict > 0:
            options["num_predict"] = settings.llm_num_predict
        # Qwen/kis modellek gyakran ismétlésbe esnek hosszú RAG válaszoknál
        options["repeat_penalty"] = float(settings.llm_repeat_penalty)
        if settings.llm_top_p > 0:
            options["top_p"] = float(settings.llm_top_p)
        return options

    def generate(self, messages: list[dict[str, str]], temperature: float) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": self._options(temperature),
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        message = data.get("message") or {}
        content = message.get("content") or data.get("response") or ""
        if not content:
            raise RuntimeError("A helyi LLM üres választ adott.")
        cleaned, _ = collapse_repetition(content.strip())
        return cleaned

    def stream(self, messages: list[dict[str, str]], temperature: float) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": self._options(temperature),
        }
        guard = StreamRepetitionGuard()
        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    import json

                    data = json.loads(line)
                    if data.get("done"):
                        break
                    message = data.get("message") or {}
                    token = message.get("content") or data.get("response") or ""
                    if not token:
                        continue
                    out = guard.push(token)
                    if out:
                        yield out
                    if guard.triggered:
                        break
