"""
TerraformPlanBuilder

Builds an enriched TerraformGenerationPlan by:
1. Running pattern.plan() to get the base plan.
2. Applying strategy overrides from TerraformReasoningAgent output.
3. Merging validation_assertions, runtime_risks, warnings, and safety_expectations.
"""

from __future__ import annotations

import logging

from app.reasoning.reasoning_schema import TerraformReasoningResult
from app.schemas.architecture import GenerateOptions
from app.schemas.plan import TerraformGenerationPlan
from app.core.config import Settings
from app.services.architecture_normalizer import NormalizedArchitecture

from .strategy_resolver import UnsupportedStrategyError, resolve_strategy

logger = logging.getLogger(__name__)


class TerraformPlanBuilder:
    """
    Enriches a base TerraformGenerationPlan with reasoning-driven strategy.

    The base plan is produced by pattern.plan() (existing deterministic logic).
    This builder then overlays the deployment strategy, subnet selection,
    assign_public_ip, validation assertions, and risk fields from reasoning.
    """

    def build(
        self,
        architecture: NormalizedArchitecture,
        pattern,  # ArchitecturePattern protocol
        reasoning: TerraformReasoningResult,
        options: GenerateOptions,
        settings: Settings,
    ) -> TerraformGenerationPlan:
        # 1. Build base plan via existing pattern logic
        base_plan = pattern.plan(architecture, options, settings)

        # 2. Resolve strategy overrides
        try:
            overrides = resolve_strategy(
                base_plan.pattern_id,
                reasoning,
                base_plan.resources,
            )
        except UnsupportedStrategyError as exc:
            logger.info("Strategy resolution returned unsupported: %s", exc)
            # Return plan with NEEDS_INPUT status so caller can handle
            return base_plan.model_copy(update={
                "generation_mode": "UNSUPPORTED",
                "deployment_strategy": reasoning.deployment_strategy,
                "validation_assertions": [],
                "runtime_risks": reasoning.runtime_risks,
                "warnings": [*base_plan.warnings, *reasoning.warnings, str(exc)],
            })

        if not overrides:
            # No strategy-specific overrides — enrich with reasoning metadata only
            return base_plan.model_copy(update={
                "deployment_strategy": reasoning.deployment_strategy,
                "validation_assertions": reasoning.validation_assertions,
                "runtime_risks": reasoning.runtime_risks,
                "warnings": _merge_unique(base_plan.warnings, reasoning.warnings),
            })

        # 3. Apply resource overrides
        merged_resources = {**base_plan.resources, **overrides.pop("resources", {})}

        # 4. Merge warnings and runtime_risks (deduplicated)
        merged_warnings = _merge_unique(base_plan.warnings, overrides.pop("warnings", []))
        merged_risks = _merge_unique(base_plan.runtime_risks, overrides.pop("runtime_risks", []))

        # 5. Build final enriched plan
        update_fields = {
            "resources": merged_resources,
            "warnings": merged_warnings,
            "runtime_risks": merged_risks,
            **overrides,
        }
        return base_plan.model_copy(update=update_fields)


def _merge_unique(a: list[str], b: list[str]) -> list[str]:
    """Merge two lists, preserving order and removing duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for item in [*a, *b]:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
