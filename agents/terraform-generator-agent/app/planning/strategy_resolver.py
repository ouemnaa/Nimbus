"""
StrategyResolver — maps (pattern_id, reasoning_result) to concrete render-time
overrides for TerraformGenerationPlan.

Returns a dict of field overrides to merge into the plan, or raises ValueError
for invalid/unsupported combinations.
"""

from __future__ import annotations

from typing import Any

from app.reasoning.reasoning_schema import TerraformReasoningResult

from .assertions import ASSERTIONS_BY_STRATEGY


class UnsupportedStrategyError(ValueError):
    pass


def resolve_strategy(
    pattern_id: str,
    reasoning: TerraformReasoningResult,
    plan_resources: dict[str, Any],
) -> dict[str, Any]:
    """
    Return a dict of fields to overlay onto TerraformGenerationPlan after
    base pattern.plan() has run.

    Raises UnsupportedStrategyError for combinations we cannot safely render.
    """
    strategy = reasoning.deployment_strategy

    if pattern_id == "ecs_fargate_alb_rds_dev":
        return _resolve_ecs_strategy(strategy, reasoning, plan_resources)

    if pattern_id == "static_site_s3_cloudfront_route53_https":
        return _resolve_static_site(reasoning)

    # Unknown pattern — no overlay needed, pass through
    return {}


def _resolve_ecs_strategy(
    strategy: str | None,
    reasoning: TerraformReasoningResult,
    plan_resources: dict[str, Any],
) -> dict[str, Any]:
    if reasoning.reasoning_status == "NEEDS_INPUT":
        public_subnets = plan_resources.get("public_subnets") or []
        private_subnets = plan_resources.get("private_subnets") or []
        if not public_subnets:
            public_subnets = private_subnets

        if public_subnets:
            fallback_warnings = list(reasoning.warnings)
            fallback_warnings.append(
                "Generated Terraform uses a deterministic fallback: ECS tasks were moved to public subnets with assign_public_ip=true so the stack remains renderable without NAT or VPC endpoints."
            )
            return {
                "generation_mode": "DETERMINISTIC_SUPPORTED",
                "deployment_strategy": "public_ecs_no_nat_low_cost_dev",
                "validation_assertions": ASSERTIONS_BY_STRATEGY["public_ecs_no_nat_low_cost_dev"],
                "runtime_risks": reasoning.runtime_risks,
                "warnings": fallback_warnings,
                "safety_expectations": [
                    "ECS security group allows inbound only from ALB SG, not 0.0.0.0/0.",
                    "RDS publicly_accessible=false.",
                    "ECS tasks run in public subnets with public IPs until NAT Gateway or VPC endpoints are added.",
                ],
                "resources": {
                    **plan_resources,
                    "ecs_subnets": public_subnets,
                    "assign_public_ip": True,
                    "nat_label": None,
                    "private_subnets": private_subnets,
                },
            }

    if strategy == "public_ecs_no_nat_low_cost_dev":
        public_subnets = plan_resources.get("public_subnets") or []
        private_subnets = plan_resources.get("private_subnets") or []
        if not public_subnets:
            # Fallback: if only private subnets exist, use them as public (already flagged by reasoning)
            public_subnets = private_subnets

        return {
            "generation_mode": "DETERMINISTIC_SUPPORTED",
            "deployment_strategy": strategy,
            "validation_assertions": ASSERTIONS_BY_STRATEGY[strategy],
            "runtime_risks": reasoning.runtime_risks,
            "warnings": reasoning.warnings,
            "safety_expectations": [
                "ECS security group allows inbound only from ALB SG, not 0.0.0.0/0.",
                "RDS publicly_accessible=false.",
            ],
            "resources": {
                **plan_resources,
                "ecs_subnets": public_subnets,
                "assign_public_ip": True,
                # Ensure no NAT in context
                "nat_label": None,
                # Private subnets still hold RDS
                "private_subnets": private_subnets,
            },
        }

    if strategy == "private_ecs_with_nat":
        private_subnets = plan_resources.get("private_subnets") or []
        if not private_subnets:
            raise UnsupportedStrategyError(
                "private_ecs_with_nat strategy selected but no private subnets found in architecture."
            )
        if not plan_resources.get("nat_label"):
            raise UnsupportedStrategyError(
                "private_ecs_with_nat strategy requires a NAT Gateway but none was found."
            )
        return {
            "generation_mode": "DETERMINISTIC_SUPPORTED",
            "deployment_strategy": strategy,
            "validation_assertions": ASSERTIONS_BY_STRATEGY[strategy],
            "runtime_risks": reasoning.runtime_risks,
            "warnings": reasoning.warnings,
            "safety_expectations": [
                "Private route table has 0.0.0.0/0 route through NAT Gateway.",
                "RDS publicly_accessible=false.",
            ],
            "resources": {
                **plan_resources,
                "ecs_subnets": private_subnets,
                "assign_public_ip": False,
            },
        }

    if strategy == "private_ecs_with_vpc_endpoints":
        raise UnsupportedStrategyError(
            "private_ecs_with_vpc_endpoints is not yet supported. "
            "Add a NAT Gateway or use the public_ecs_no_nat_low_cost_dev strategy."
        )

    # Reasoning returned unsupported or unknown strategy
    if reasoning.reasoning_status in ("UNSUPPORTED", "FAILED"):
        reasons = reasoning.unsupported_reasons or reasoning.warnings or []
        raise UnsupportedStrategyError(
            "Cannot resolve ECS deployment strategy: " + "; ".join(reasons)
        )

    # No explicit strategy from reasoning — apply safe defaults
    return {}


def _resolve_static_site(reasoning: TerraformReasoningResult) -> dict[str, Any]:
    return {
        "generation_mode": "DETERMINISTIC_SUPPORTED",
        "deployment_strategy": "static_site_s3_cloudfront_route53_https",
        "validation_assertions": ASSERTIONS_BY_STRATEGY["static_site_s3_cloudfront_route53_https"],
        "runtime_risks": reasoning.runtime_risks,
        "warnings": reasoning.warnings,
    }
