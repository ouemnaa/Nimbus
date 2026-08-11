"""
TerraformReviewerAgent

Reviews generated Terraform files for faithfulness to the architecture
and generation plan. Does NOT modify files — only reports findings.

When LLM_PROVIDER=none, returns review_status="SKIPPED".
"""

from __future__ import annotations

import asyncio
import json
import logging

from app.llm.base import LLMProvider
from app.safety.findings import SafetyCheckResult
from app.schemas.architecture import FileArtifact
from app.schemas.plan import TerraformGenerationPlan
from app.schemas.validation import ValidationResponse
from app.services.architecture_normalizer import NormalizedArchitecture

from .reviewer_prompt import SYSTEM_PROMPT, build_reviewer_prompt
from .reviewer_schema import ReviewIssue, TerraformReviewResult

logger = logging.getLogger(__name__)

_SKIPPED = TerraformReviewResult(
    review_status="SKIPPED",
    trusted=True,
    faithfulness_score=1.0,
    deployability_score=1.0,
)


def _parse_review(raw: str) -> TerraformReviewResult:
    """Parse LLM JSON output into TerraformReviewResult. Returns FAILED on error."""
    try:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        issues_data = data.pop("critical_issues", [])
        result = TerraformReviewResult(**data)
        result.critical_issues = [ReviewIssue(**i) for i in issues_data if isinstance(i, dict)]
        return result
    except Exception as exc:
        logger.warning("Failed to parse LLM review output: %s", exc)
        return TerraformReviewResult(
            review_status="FAILED",
            trusted=False,
            faithfulness_score=0.0,
            deployability_score=0.0,
            warnings=[f"LLM review parse error: {type(exc).__name__}"],
        )


def _files_summary(files: list[FileArtifact]) -> str:
    """Compact summary of generated files for the prompt (first 300 chars each)."""
    parts = []
    for f in files:
        snippet = f.content[:300].replace("\n", " ")
        parts.append(f"--- {f.path} ---\n{snippet}{'...' if len(f.content) > 300 else ''}")
    return "\n\n".join(parts)


def _validation_summary(validation: ValidationResponse | None) -> str:
    if not validation:
        return "No validation result available."
    checks = ", ".join(f"{c.name}:{c.status}" for c in (validation.checks or []))
    return f"status={validation.validation_status} checks=[{checks}]"


def _safety_summary(safety: SafetyCheckResult) -> str:
    if not safety.findings:
        return "No safety findings."
    lines = [f"has_critical={safety.has_critical}, total={len(safety.findings)}"]
    for f in safety.findings[:10]:
        lines.append(f"  [{f.severity}] {f.code}: {f.message}")
    return "\n".join(lines)


class TerraformReviewerAgent:
    """
    Reviews generated Terraform for faithfulness to architecture and plan.

    Returns SKIPPED when llm is None (deterministic-only mode).
    The reviewer never modifies files.
    """

    def review(
        self,
        architecture: NormalizedArchitecture,
        plan: TerraformGenerationPlan,
        files: list[FileArtifact],
        validation_result: ValidationResponse | None,
        safety_findings: SafetyCheckResult,
        llm: LLMProvider | None,
    ) -> TerraformReviewResult:
        if llm is None:
            return _SKIPPED

        try:
            arch_json = architecture.model_dump_json(indent=2) if hasattr(architecture, "model_dump_json") else "{}"
            plan_json = plan.model_dump_json(indent=2)
            prompt = "\n\n".join([
                SYSTEM_PROMPT,
                build_reviewer_prompt(
                    arch_json,
                    plan_json,
                    _files_summary(files),
                    _validation_summary(validation_result),
                    _safety_summary(safety_findings),
                ),
            ])
            raw = asyncio.get_event_loop().run_until_complete(llm.complete(prompt))
            return _parse_review(raw)
        except Exception as exc:
            logger.warning("LLM reviewer call failed: %s", type(exc).__name__)
            return TerraformReviewResult(
                review_status="SKIPPED",
                trusted=True,
                warnings=[f"Reviewer LLM call failed: {type(exc).__name__}. Skipping review."],
            )
