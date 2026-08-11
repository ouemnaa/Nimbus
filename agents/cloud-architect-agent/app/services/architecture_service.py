import json
import time
from typing import Any, Dict, Iterable
from ..llm.base import LLMProvider
from ..schemas.architecture import ArchitectureSpecification
from ..schemas.requests import AnalyzeResponse, FollowUpRequest, FollowUpResponse, GenerationMetadata
from ..renderers.markdown_renderer import MarkdownRenderer
from ..renderers.mermaid_renderer import MermaidRenderer
from ..prompts.solution_architect_prompt import SOLUTION_ARCHITECT_SYSTEM_PROMPT
from ..core.config import settings

class ArchitectureService:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.markdown_renderer = MarkdownRenderer()
        self.mermaid_renderer = MermaidRenderer()

    async def analyze_requirement(
        self, 
        requirement: str, 
        context: Dict[str, Any] | None = None
    ) -> AnalyzeResponse:
        start_time = time.time()
        
        # Add context to user prompt if available
        user_prompt = requirement
        if context:
            user_prompt += f"\n\nAdditional Context: {context}"

        # Generate structured output from LLM
        architecture = await self.llm_provider.generate_structured_output(
            system_prompt=SOLUTION_ARCHITECT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=ArchitectureSpecification
        )

        # Generate diagrams and report deterministically
        diagrams = self.mermaid_renderer.render(architecture)
        report_markdown = self.markdown_renderer.render(architecture, diagrams)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        metadata = GenerationMetadata(
            provider=settings.LLM_PROVIDER,
            model=getattr(settings, f"{settings.LLM_PROVIDER.upper()}_MODEL", "unknown"),
            generation_duration_ms=duration_ms
        )

        return AnalyzeResponse(
            architecture=architecture,
            report_markdown=report_markdown,
            metadata=metadata
        )

    async def follow_up(self, request: FollowUpRequest) -> FollowUpResponse:
        start_time = time.time()
        intent = self._classify_follow_up(request.user_message)
        previous_version = str(
            request.current_architecture.get("architecture_version", "1.0.0")
        )
        new_version = self._next_minor_version(previous_version)

        if intent != "MODIFY":
            duration_ms = int((time.time() - start_time) * 1000)
            return FollowUpResponse(
                intent=intent,
                architecture_changed=False,
                answer=self._answer_for_intent(
                    intent=intent,
                    message=request.user_message,
                    architecture=request.current_architecture,
                    conversation_summary=request.conversation_summary,
                ),
                previous_version=previous_version,
                metadata={
                    "provider": settings.LLM_PROVIDER,
                    "model": getattr(
                        settings,
                        f"{settings.LLM_PROVIDER.upper()}_MODEL",
                        "unknown",
                    ),
                    "generation_duration_ms": duration_ms,
                },
            )

        user_prompt = (
            "Revise the current cloud architecture according to the user's "
            "requested change. Preserve valid existing decisions unless the "
            "change requires updating them.\n\n"
            f"Current architecture JSON:\n{json.dumps(request.current_architecture)}\n\n"
            f"Current report markdown:\n{request.current_report_markdown or ''}\n\n"
            "Recent conversation:\n"
            f"{json.dumps([message.model_dump() for message in request.messages])}\n\n"
            f"User requested change:\n{request.user_message}"
        )
        architecture = await self.llm_provider.generate_structured_output(
            system_prompt=SOLUTION_ARCHITECT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_schema=ArchitectureSpecification,
        )
        architecture.architecture_version = new_version
        diagrams = self.mermaid_renderer.render(architecture)
        report_markdown = self.markdown_renderer.render(architecture, diagrams)
        duration_ms = int((time.time() - start_time) * 1000)

        return FollowUpResponse(
            intent="MODIFY",
            architecture_changed=True,
            answer=f"Created draft architecture version {new_version}.",
            change_summary=[request.user_message],
            previous_version=previous_version,
            new_version=new_version,
            architecture=architecture,
            report_markdown=report_markdown,
            metadata={
                "provider": settings.LLM_PROVIDER,
                "model": getattr(
                    settings,
                    f"{settings.LLM_PROVIDER.upper()}_MODEL",
                    "unknown",
                ),
                "generation_duration_ms": duration_ms,
            },
        )

    @staticmethod
    def _classify_follow_up(message: str) -> str:
        text = message.lower()
        unsupported_keywords = ("terraform", "kubernetes manifests", "billing export")
        clarify_keywords = ("make it better", "improve it", "change it", "update it")
        modify_keywords = (
            "add",
            "remove",
            "replace",
            "change",
            "switch",
            "use",
            "move",
            "enable",
            "disable",
        )

        if any(keyword in text for keyword in unsupported_keywords):
            return "UNSUPPORTED"
        if text.strip() in clarify_keywords:
            return "CLARIFY"
        if any(keyword in text for keyword in modify_keywords):
            return "MODIFY"
        return "EXPLAIN"

    @staticmethod
    def _answer_for_intent(
        *,
        intent: str,
        message: str,
        architecture: Dict[str, Any],
        conversation_summary: str | None,
    ) -> str:
        if intent == "CLARIFY":
            return "\n".join(
                [
                    "I can refine the design, but I need one more detail to make the change safely.",
                    "What part of the architecture should change?",
                    "Do you want a cost, reliability, or scalability adjustment?",
                ]
            )
        if intent == "UNSUPPORTED":
            return "\n".join(
                [
                    "That request is outside the current Nimbus architecture scope.",
                    "I can still help with AWS architecture decisions, tradeoffs, and revisions.",
                ]
            )

        lines = ["Here is the reasoning behind the current design:"]

        solution = architecture.get("solution")
        if isinstance(solution, str) and solution.strip():
            lines.append(f"- Solution summary: {solution.strip()}")

        cloud = architecture.get("cloud")
        if isinstance(cloud, dict):
            region = cloud.get("region")
            rationale = cloud.get("region_rationale")
            if isinstance(region, str) and isinstance(rationale, str):
                lines.append(f"- Region choice: {region} because {rationale}")

        decisions = architecture.get("decisions")
        if isinstance(decisions, list):
            for decision in self._iter_decision_rationales(decisions):
                lines.append(f"- {decision}")
                if len(lines) >= 4:
                    break

        if conversation_summary:
            lines.append(f"- Conversation context: {conversation_summary}")

        lines.append(f"- Your question: {message}")
        return "\n".join(lines)

    @staticmethod
    def _iter_decision_rationales(decisions: Iterable[Any]) -> Iterable[str]:
        for item in decisions:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            rationale = item.get("rationale")
            if isinstance(title, str) and isinstance(rationale, str):
                yield f"Decision on {title}: {rationale}"

    @staticmethod
    def _next_minor_version(version: str) -> str:
        parts = version.split(".")
        if len(parts) != 3:
            return "1.1.0"
        try:
            major = int(parts[0])
            minor = int(parts[1])
        except ValueError:
            return "1.1.0"
        return f"{major}.{minor + 1}.0"
