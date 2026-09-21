from collections.abc import Iterator

import httpx

from app.llm.base import LLMProvider


class OllamaLLMProvider(LLMProvider):
    def __init__(self, base_url: str, model: str, timeout: float = 300.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, messages: list[dict[str, str]], temperature: float) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
        message = data.get("message") or {}
        content = message.get("content") or data.get("response") or ""
        if not content:
            raise RuntimeError("A helyi LLM üres választ adott.")
        return content.strip()

    def stream(self, messages: list[dict[str, str]], temperature: float) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }
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
                    if token:
                        yield token
