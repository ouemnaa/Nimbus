from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import (
    TerraformAgentUnavailableError,
    TerraformGenerationError,
)


@dataclass(frozen=True)
class TerraformGenerationResult:
    status: str
    files: list[dict[str, str]]
    warnings: list[str]
    next_steps: list[str]
    metadata: dict[str, Any]
    supported_resources: list[str]
    unsupported_resources: list[str]
    derived_resources: list[dict[str, Any]]
    repairs: list[dict[str, Any]]
    error: str | None


class TerraformGeneratorAgentClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float = 120.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.terraform_generator_agent_url).rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)

    async def generate(
        self,
        *,
        project_id: str,
        architecture_version_id: str,
        architecture: dict[str, Any],
        options: dict[str, Any],
    ) -> TerraformGenerationResult:
        payload = {
            "project_id": project_id,
            "architecture_version_id": architecture_version_id,
            "architecture_id": architecture.get("architecture_id"),
            "architecture_version": architecture.get("architecture_version"),
            "architecture": architecture,
            "options": options,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/terraform/generate",
                    json=payload,
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
            raise TerraformAgentUnavailableError(self.base_url) from None
        except httpx.HTTPError:
            raise TerraformGenerationError() from None

        if response.status_code < 200 or response.status_code >= 300:
            raise TerraformGenerationError()

        try:
            data = response.json()
        except ValueError:
            raise TerraformGenerationError() from None

        files = data.get("files", [])
        if not isinstance(files, list):
            raise TerraformGenerationError()
        for item in files:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise TerraformGenerationError()
            if not isinstance(item.get("content"), str):
                raise TerraformGenerationError()

        return TerraformGenerationResult(
            status=str(data.get("generation_status", data.get("status", "FAILED"))),
            files=[{"path": item["path"], "content": item["content"]} for item in files],
            warnings=[str(item) for item in data.get("warnings", [])],
            next_steps=[str(item) for item in data.get("next_steps", [])],
            metadata=data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {},
            supported_resources=[
                str(item) for item in data.get("supported_resources", [])
            ],
            unsupported_resources=[
                str(item) for item in data.get("unsupported_resources", [])
            ],
            derived_resources=[
                item for item in data.get("derived_resources", []) if isinstance(item, dict)
            ],
            repairs=[item for item in data.get("repairs", []) if isinstance(item, dict)],
            error=data.get("error") if isinstance(data.get("error"), str) else None,
        )
