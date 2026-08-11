from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .openrouter_provider import OpenRouterProvider


class LLMConfigurationError(ValueError):
    pass


def create_provider(settings) -> LLMProvider | None:
    provider = settings.llm_provider
    if provider == "none":
        return None
    if provider == "gemini":
        if not settings.gemini_api_key or not settings.gemini_model:
            raise LLMConfigurationError("Gemini requires GEMINI_API_KEY and GEMINI_MODEL.")
        return GeminiProvider(settings.gemini_api_key, settings.gemini_model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)
    if provider == "groq":
        if not settings.groq_api_key or not settings.groq_model:
            raise LLMConfigurationError("Groq requires GROQ_API_KEY and GROQ_MODEL.")
        return GroqProvider(settings.groq_api_key, settings.groq_model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)
    if provider == "openrouter":
        if not settings.openrouter_api_key or not settings.openrouter_model:
            raise LLMConfigurationError("OpenRouter requires OPENROUTER_API_KEY and OPENROUTER_MODEL.")
        return OpenRouterProvider(settings.openrouter_api_key, settings.openrouter_model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)
    raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")
