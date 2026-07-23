from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Cloud Architect Agent"
    
    # LLM Configuration
    LLM_PROVIDER: Literal["gemini", "groq", "fake"] = "fake"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_RETRIES: int = 2
    LLM_TIMEOUT_SECONDS: int = 60
    
    # Gemini
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-pro"
    
    # Groq
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
