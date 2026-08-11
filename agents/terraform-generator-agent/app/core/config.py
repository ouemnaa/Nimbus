from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    terraform_generator_host: str = "0.0.0.0"
    terraform_generator_port: int = 8002
    terraform_binary: str = "terraform"
    generated_artifacts_dir: str = "generated"
    default_aws_region: str = "us-east-1"
    default_project_name: str = "nimbus"
    default_environment: str = "dev"
    validation_enable_terraform_init: bool = True
    validation_enable_terraform_plan: bool = False
    validation_timeout_seconds: int = 120

    # LLM provider — "auto" tries Gemini → Groq → OpenRouter, falls back to none
    llm_provider: Literal["gemini", "groq", "openrouter", "none", "auto"] = "none"

    # Gemini — keep singular key for backward compat; _fast/_strong are optional model tier aliases
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    gemini_model_fast: str | None = None
    gemini_model_strong: str | None = None

    # Groq
    groq_api_key: str | None = None
    groq_model: str | None = None
    groq_model_fast: str | None = None
    groq_model_strong: str | None = None

    # OpenRouter
    openrouter_api_key: str | None = None
    openrouter_model: str | None = None
    openrouter_model_fast: str | None = None
    openrouter_model_strong: str | None = None

    llm_temperature: float = Field(default=0.1, ge=0, le=2)
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2

    generator_version: str = "0.2.0"

    # Feature flags
    terraform_reasoning_enabled: bool = True
    terraform_reviewer_enabled: bool = True
    terraform_llm_draft_fallback_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
