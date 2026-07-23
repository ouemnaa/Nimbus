import time
from typing import Dict, Any
from ..llm.base import LLMProvider
from ..schemas.architecture import ArchitectureSpecification
from ..schemas.requests import AnalyzeResponse, GenerationMetadata
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
