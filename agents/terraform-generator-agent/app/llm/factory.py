from .base import LLMProvider
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .openrouter_provider import OpenRouterProvider


class LLMConfigurationError(ValueError):
    pass


def _resolve_model(primary: str | None, fast: str | None, strong: str | None) -> str | None:
    """Return the best available model name from the given priority list."""
    return primary or fast or strong


def create_provider(settings) -> LLMProvider | None:
    """
    Create an LLM provider from settings.

    LLM_PROVIDER=auto tries Gemini → Groq → OpenRouter and returns the first
    fully-configured provider. Returns None if none are configured.

    Never logs or raises exceptions that expose API key values.
    """
    provider = settings.llm_provider

    if provider == "none":
        return None

    if provider == "gemini":
        model = _resolve_model(settings.gemini_model, settings.gemini_model_fast, settings.gemini_model_strong)
        if not settings.gemini_api_key or not model:
            raise LLMConfigurationError("Gemini requires GEMINI_API_KEY and GEMINI_MODEL (or GEMINI_MODEL_FAST/STRONG).")
        return GeminiProvider(settings.gemini_api_key, model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)

    if provider == "groq":
        model = _resolve_model(settings.groq_model, settings.groq_model_fast, settings.groq_model_strong)
        if not settings.groq_api_key or not model:
            raise LLMConfigurationError("Groq requires GROQ_API_KEY and GROQ_MODEL (or GROQ_MODEL_FAST/STRONG).")
        return GroqProvider(settings.groq_api_key, model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)

    if provider == "openrouter":
        model = _resolve_model(settings.openrouter_model, settings.openrouter_model_fast, settings.openrouter_model_strong)
        if not settings.openrouter_api_key or not model:
            raise LLMConfigurationError("OpenRouter requires OPENROUTER_API_KEY and OPENROUTER_MODEL (or OPENROUTER_MODEL_FAST/STRONG).")
        return OpenRouterProvider(settings.openrouter_api_key, model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)

    if provider == "auto":
        # Try Gemini → Groq → OpenRouter — first fully configured wins
        gemini_model = _resolve_model(settings.gemini_model, settings.gemini_model_fast, settings.gemini_model_strong)
        if settings.gemini_api_key and gemini_model:
            return GeminiProvider(settings.gemini_api_key, gemini_model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)

        groq_model = _resolve_model(settings.groq_model, settings.groq_model_fast, settings.groq_model_strong)
        if settings.groq_api_key and groq_model:
            return GroqProvider(settings.groq_api_key, groq_model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)

        openrouter_model = _resolve_model(settings.openrouter_model, settings.openrouter_model_fast, settings.openrouter_model_strong)
        if settings.openrouter_api_key and openrouter_model:
            return OpenRouterProvider(settings.openrouter_api_key, openrouter_model, settings.llm_timeout_seconds, settings.llm_max_retries, settings.llm_temperature)

        # No provider configured — operate in deterministic-only mode
        return None

    raise LLMConfigurationError(f"Unsupported LLM provider: {provider}")
