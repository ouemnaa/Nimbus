from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import (
    AgentRequestError,
    AgentResponseError,
    AgentUnavailableError,
)


@dataclass(frozen=True)
class AgentAnalysisResult:
    architecture: dict[str, Any]
    report_markdown: str
    metadata: dict[str, Any]


class SolutionArchitectAgentClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float = 60.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.solution_architect_agent_url).rstrip("/")
        self.timeout = httpx.Timeout(timeout_seconds)

    async def analyze_requirement(
        self, requirement: str, context: dict[str, Any]
    ) -> AgentAnalysisResult:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/architectures/analyze",
                    json={"requirement": requirement, "context": context},
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout):
            raise AgentUnavailableError(self.base_url) from None
        except httpx.HTTPError:
            raise AgentRequestError() from None

        if response.status_code < 200 or response.status_code >= 300:
            raise AgentRequestError()

        try:
            payload = response.json()
        except ValueError:
            raise AgentResponseError() from None

        architecture = payload.get("architecture")
        report_markdown = payload.get("report_markdown", payload.get("reportMarkdown"))
        metadata = payload.get("metadata", {})

        if not isinstance(architecture, dict) or not architecture:
            raise AgentResponseError()
        if not isinstance(report_markdown, str):
            raise AgentResponseError()
        if not isinstance(metadata, dict):
            raise AgentResponseError()

        return AgentAnalysisResult(
            architecture=architecture,
            report_markdown=report_markdown,
            metadata=metadata,
        )
