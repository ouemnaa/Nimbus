from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def complete(self, prompt: str) -> str:
        raise NotImplementedError
