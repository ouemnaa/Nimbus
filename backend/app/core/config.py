from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    mongodb_uri: str | None = Field(default=None, alias="MONGODB_URI")
    mongodb_db_name: str = Field(default="nimbus_dev", alias="MONGODB_DB_NAME")
    backend_host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")
    frontend_url: str = Field(
        default="http://localhost:3000", alias="FRONTEND_URL"
    )
    solution_architect_agent_url: str = Field(
        default="http://localhost:8001", alias="SOLUTION_ARCHITECT_AGENT_URL"
    )
    terraform_generator_agent_url: str = Field(
        default="http://localhost:8002", alias="TERRAFORM_GENERATOR_AGENT_URL"
    )

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
