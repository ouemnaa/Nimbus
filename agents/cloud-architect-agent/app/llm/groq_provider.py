import json
import httpx
from typing import Type, TypeVar
from pydantic import BaseModel
from .base import LLMProvider
from ..core.exceptions import LLMProviderError
from ..core.logging import logger

T = TypeVar("T", bound=BaseModel)

class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str, temperature: float = 0.2):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Type[T]
    ) -> T:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return response_schema.model_validate_json(content)
        except Exception as e:
            logger.error(f"Groq generation failed: {str(e)}")
            raise LLMProviderError(f"Groq error: {str(e)}")
