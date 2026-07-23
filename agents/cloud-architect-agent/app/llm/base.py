from typing import Protocol, Dict, Any, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class LLMProvider(Protocol):
    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Type[T]
    ) -> T:
        ...
