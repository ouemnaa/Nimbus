import asyncio

import httpx

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: int = 60, max_retries: int = 2, temperature: float = 0.1) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.temperature = temperature

    async def complete(self, prompt: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": self.temperature},
        }
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, params={"key": self.api_key}, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as exc:  # provider errors are surfaced without secret-bearing details
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(2**attempt)
        raise RuntimeError(f"Gemini request failed after retries: {type(last_error).__name__}")
