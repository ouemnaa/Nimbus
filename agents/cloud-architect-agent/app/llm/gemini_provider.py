import json
import google.generativeai as genai
from typing import Any, Type, TypeVar
from pydantic import BaseModel
from .base import LLMProvider
from ..core.exceptions import LLMProviderError
from ..core.logging import logger

T = TypeVar("T", bound=BaseModel)


def _sanitize_schema_for_prompt(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            if key in {"default", "title"}:
                continue
            cleaned[key] = _sanitize_schema_for_prompt(item)
        return cleaned
    if isinstance(value, list):
        return [_sanitize_schema_for_prompt(item) for item in value]
    return value


def _extract_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped

class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str, temperature: float = 0.2):
        if not api_key:
            raise LLMProviderError("Gemini API key is required")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={"temperature": temperature}
        )

    async def generate_structured_output(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Type[T]
    ) -> T:
        try:
            schema_for_prompt = _sanitize_schema_for_prompt(
                response_schema.model_json_schema()
            )
            full_prompt = (
                f"{system_prompt}\n\n"
                f"User Requirement: {user_prompt}\n\n"
                "You must return exactly one valid JSON object.\n"
                "Use the exact property names from the schema below.\n"
                "Do not invent alternate keys.\n"
                "Do not wrap the JSON in markdown fences.\n\n"
                "Required JSON schema:\n"
                f"{json.dumps(schema_for_prompt, indent=2)}"
            )
            
            # Ask Gemini for JSON and validate it locally with Pydantic.
            # Passing the raw Pydantic schema can fail because Gemini rejects
            # some JSON Schema fields such as "default".
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json"
                )
            )

            return response_schema.model_validate(
                json.loads(_extract_json_text(response.text))
            )
        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            raise LLMProviderError(f"Gemini error: {str(e)}")
