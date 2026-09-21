from abc import ABC, abstractmethod
from collections.abc import Iterator


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, messages: list[dict[str, str]], temperature: float) -> str:
        raise NotImplementedError

    @abstractmethod
    def stream(self, messages: list[dict[str, str]], temperature: float) -> Iterator[str]:
        raise NotImplementedError
