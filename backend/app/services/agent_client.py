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


@dataclass(frozen=True)
class AgentFollowUpResult:
    intent: str
    architecture_changed: bool
    answer: str
    change_summary: list[str]
    previous_version: str | None
    new_version: str | None
    architecture: dict[str, Any] | None
    report_markdown: str | None
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

    async def follow_up(
        self,
        *,
        session_id: str,
        current_architecture: dict[str, Any],
        current_report_markdown: str | None,
        conversation_summary: str | None,
        messages: list[dict[str, str]],
        user_message: str,
    ) -> AgentFollowUpResult:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/architectures/follow-up",
                    json={
                        "session_id": session_id,
                        "current_architecture": current_architecture,
                        "current_report_markdown": current_report_markdown,
                        "conversation_summary": conversation_summary,
                        "messages": messages,
                        "user_message": user_message,
                    },
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

        intent = payload.get("intent")
        architecture_changed = payload.get("architecture_changed")
        if architecture_changed is None:
            architecture_changed = payload.get("architectureChanged")
        answer = payload.get("answer")
        change_summary = payload.get("change_summary", payload.get("changeSummary", []))
        architecture = payload.get("architecture")
        report_markdown = payload.get("report_markdown", payload.get("reportMarkdown"))
        metadata = payload.get("metadata", {})

        if intent not in {"EXPLAIN", "MODIFY", "CLARIFY", "UNSUPPORTED"}:
            raise AgentResponseError()
        if not isinstance(architecture_changed, bool):
            raise AgentResponseError()
        if not isinstance(answer, str):
            raise AgentResponseError()
        if not isinstance(change_summary, list):
            raise AgentResponseError()
        if architecture_changed and not isinstance(architecture, dict):
            raise AgentResponseError()
        if architecture_changed and not isinstance(report_markdown, str):
            raise AgentResponseError()
        if not isinstance(metadata, dict):
            raise AgentResponseError()

        return AgentFollowUpResult(
            intent=intent,
            architecture_changed=architecture_changed,
            answer=answer,
            change_summary=[str(item) for item in change_summary],
            previous_version=payload.get("previous_version", payload.get("previousVersion")),
            new_version=payload.get("new_version", payload.get("newVersion")),
            architecture=architecture if isinstance(architecture, dict) else None,
            report_markdown=report_markdown if isinstance(report_markdown, str) else None,
            metadata=metadata,
        )
