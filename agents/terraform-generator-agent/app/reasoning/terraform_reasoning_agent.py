"""
TerraformReasoningAgent

Reviews the canonical architecture and produces a structured Terraform strategy
(deployment strategy, networking rules, validation assertions, runtime risks).

It does NOT write HCL.

When LLM_PROVIDER=none, falls back to deterministic reasoning rules derived from
the detected pattern and architecture topology.
"""

from __future__ import annotations

import json
import logging

from app.llm.base import LLMProvider
from app.schemas.plan import TerraformGenerationPlan
from app.services.architecture_normalizer import NormalizedArchitecture, resource_cfg
from app.utils.asyncio_utils import run_awaitable

from .reasoning_prompt import SYSTEM_PROMPT, build_reasoning_prompt
from .reasoning_schema import NetworkingStrategy, TerraformReasoningResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deterministic reasoning rules (used when LLM_PROVIDER=none)
# ---------------------------------------------------------------------------

def _has_nat(architecture: NormalizedArchitecture) -> bool:
    return bool(architecture.first("aws_nat_gateway"))


def _has_only_public_subnets(architecture: NormalizedArchitecture) -> bool:
    subnets = architecture.by_type("aws_subnet")
    if not subnets:
        return False
    for subnet in subnets:
        value = resource_cfg(subnet, "public", "is_public", default=None)
        tier = str(resource_cfg(subnet, "subnet_type", "network_tier", "tier", default=""))
        is_public = bool(value) if value is not None else (
            "public" in tier.lower()
            or "public" in subnet.id.lower()
            or "public" in subnet.name.lower()
        )
        if not is_public:
            return False
    return True


def _has_private_subnets(architecture: NormalizedArchitecture) -> bool:
    subnets = architecture.by_type("aws_subnet")
    for subnet in subnets:
        value = resource_cfg(subnet, "public", "is_public", default=None)
        tier = str(resource_cfg(subnet, "subnet_type", "network_tier", "tier", default=""))
        is_public = bool(value) if value is not None else (
            "public" in tier.lower()
            or "public" in subnet.id.lower()
            or "public" in subnet.name.lower()
        )
        if not is_public:
            return True
    return False


def _deterministic_ecs_reasoning(
    architecture: NormalizedArchitecture,
) -> TerraformReasoningResult:
    has_nat = _has_nat(architecture)
    only_public = _has_only_public_subnets(architecture)
    has_private = _has_private_subnets(architecture)

    if only_public and not has_nat:
        # Low-cost public ECS strategy
        return TerraformReasoningResult(
            reasoning_status="SUCCESS",
            pattern_id="ecs_fargate_alb_rds_dev",
            deployment_strategy="public_ecs_no_nat_low_cost_dev",
            terraform_strategy_summary=(
                "ECS Fargate tasks run in public subnets with assign_public_ip=true. "
                "No NAT Gateway is required, reducing cost. Inbound traffic is restricted "
                "to the ALB security group. RDS remains in private subnets (or only public "
                "subnets if none defined) with publicly_accessible=false."
            ),
            networking_strategy=NetworkingStrategy(
                ecs_subnets="public",
                ecs_assign_public_ip=True,
                rds_subnets="private",
                rds_publicly_accessible=False,
                nat_gateway_required=False,
                vpc_endpoints_required=False,
            ),
            validation_assertions=[
                "ECS service must use public subnets for low-cost no-NAT strategy.",
                "ECS assign_public_ip must be true when no NAT or VPC endpoints exist.",
                "RDS must remain publicly_accessible=false.",
                "RDS security group must allow PostgreSQL only from ECS security group.",
                "ECS security group must allow inbound only from ALB security group.",
            ],
            warnings=[
                "ECS tasks have public IPs — ensure ALB security group restricts inbound to prevent direct access.",
                "This is a low-cost dev strategy. For production, move ECS to private subnets with NAT Gateway or VPC endpoints.",
            ],
            runtime_risks=[
                "Public ECS IPs are reachable if security groups are misconfigured.",
            ],
        )

    if has_private and has_nat:
        return TerraformReasoningResult(
            reasoning_status="SUCCESS",
            pattern_id="ecs_fargate_alb_rds_dev",
            deployment_strategy="private_ecs_with_nat",
            terraform_strategy_summary=(
                "ECS Fargate tasks run in private subnets with assign_public_ip=false. "
                "A NAT Gateway in the public subnet provides outbound internet access for "
                "image pulls, secrets, and logs."
            ),
            networking_strategy=NetworkingStrategy(
                ecs_subnets="private",
                ecs_assign_public_ip=False,
                rds_subnets="private",
                rds_publicly_accessible=False,
                nat_gateway_required=True,
                vpc_endpoints_required=False,
            ),
            validation_assertions=[
                "ECS service must use private subnets.",
                "ECS assign_public_ip must be false.",
                "Private route table must have a default route through the NAT Gateway.",
                "RDS must remain publicly_accessible=false.",
                "RDS security group must allow PostgreSQL only from ECS security group.",
            ],
            warnings=[
                "NAT Gateway incurs hourly and data-transfer costs (~$32+/month). "
                "Consider public ECS strategy for low-cost dev workloads.",
            ],
        )

    if has_private and not has_nat:
        # CRITICAL: private ECS with no NAT and no VPC endpoints
        return TerraformReasoningResult(
            reasoning_status="NEEDS_INPUT",
            pattern_id="ecs_fargate_alb_rds_dev",
            deployment_strategy=None,
            terraform_strategy_summary=(
                "Architecture has private subnets but no NAT Gateway and no VPC endpoints. "
                "ECS tasks in private subnets cannot pull images, write logs, or read secrets. "
                "This configuration passes terraform validate but FAILS at runtime."
            ),
            validation_assertions=[],
            warnings=[
                "CRITICAL: Private ECS subnets without NAT Gateway or VPC endpoints "
                "will fail at runtime. ECS tasks cannot reach ECR, CloudWatch Logs, or Secrets Manager.",
            ],
            runtime_risks=[
                "ECS tasks in private subnets without outbound internet access "
                "will fail to start: cannot pull Docker images from ECR.",
                "ECS tasks will fail to write logs to CloudWatch Logs.",
                "ECS tasks will fail to read secrets from Secrets Manager.",
            ],
            required_inputs=[
                "Add a NAT Gateway in a public subnet, OR",
                "Add VPC endpoints for ecr.api, ecr.dkr, logs, secretsmanager, and s3 (gateway).",
            ],
            unsupported_reasons=[
                "Private ECS with no NAT and no VPC endpoints is not a safe deployable configuration.",
            ],
        )

    # Default: try public strategy
    return TerraformReasoningResult(
        reasoning_status="SUCCESS",
        pattern_id="ecs_fargate_alb_rds_dev",
        deployment_strategy="public_ecs_no_nat_low_cost_dev",
        terraform_strategy_summary=(
            "Defaulting to public ECS no-NAT strategy: no private subnets detected."
        ),
        networking_strategy=NetworkingStrategy(
            ecs_subnets="public",
            ecs_assign_public_ip=True,
            rds_subnets="private",
            rds_publicly_accessible=False,
            nat_gateway_required=False,
        ),
        validation_assertions=[
            "ECS service must use public subnets.",
            "ECS assign_public_ip must be true.",
            "RDS must remain publicly_accessible=false.",
        ],
        warnings=[
            "No private subnets detected — ECS will run in public subnets. Suitable for dev only.",
        ],
    )


def _deterministic_static_site_reasoning() -> TerraformReasoningResult:
    return TerraformReasoningResult(
        reasoning_status="SUCCESS",
        pattern_id="static_site_s3_cloudfront_route53_https",
        deployment_strategy="static_site_s3_cloudfront_route53_https",
        terraform_strategy_summary=(
            "S3 private bucket, CloudFront OAC, ACM certificate in us-east-1, "
            "Route53 alias record. Terraform does not upload assets."
        ),
        validation_assertions=[
            "S3 bucket must have public access block enabled.",
            "CloudFront OAC must be configured — bucket policy allows only CloudFront distribution ARN.",
            "ACM certificate must use provider alias aws.us_east_1 (CloudFront requirement).",
            "Route53 hosted zone must be looked up via data.aws_route53_zone.",
            "domain_name, hosted_zone_name, and bucket_name are required user inputs.",
        ],
        warnings=[
            "Terraform does not upload website assets. Use aws s3 sync after infrastructure is created.",
            "CloudFront cache invalidation is required after each deployment.",
        ],
    )


def _deterministic_generic_pattern_reasoning(pattern_id: str) -> TerraformReasoningResult:
    return TerraformReasoningResult(
        reasoning_status="SUCCESS",
        pattern_id=pattern_id,
        deployment_strategy=pattern_id,
        terraform_strategy_summary=(
            "Nimbus matched this architecture to a trusted deterministic pattern and preserved the selected AWS services while adding only required Terraform wiring resources."
        ),
        validation_assertions=[
            "Generated Terraform must preserve the architecture's selected provider services.",
            "Derived resources must exist only for required wiring, IAM, observability, networking, or secret handling.",
            "Generated Terraform must pass terraform fmt, init -backend=false, and validate when Terraform CLI is available.",
        ],
        warnings=[],
    )


# ---------------------------------------------------------------------------
# LLM reasoning parser
# ---------------------------------------------------------------------------

def _parse_llm_reasoning(raw: str, pattern_id: str | None) -> TerraformReasoningResult:
    """Parse LLM JSON output into TerraformReasoningResult. Falls back to FAILED on error."""
    try:
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        # Parse networking_strategy sub-dict if present
        ns_data = data.pop("networking_strategy", None)
        result = TerraformReasoningResult(**data)
        if ns_data and isinstance(ns_data, dict):
            result.networking_strategy = NetworkingStrategy(**ns_data)
        return result
    except Exception as exc:
        logger.warning("Failed to parse LLM reasoning output: %s", exc)
        return TerraformReasoningResult(
            reasoning_status="FAILED",
            pattern_id=pattern_id,
            terraform_strategy_summary="LLM reasoning output could not be parsed.",
            warnings=[f"LLM reasoning parse error: {type(exc).__name__}"],
        )


# ---------------------------------------------------------------------------
# Main agent
# ---------------------------------------------------------------------------

class TerraformReasoningAgent:
    """
    Reviews canonical architecture and produces a structured Terraform strategy.

    Does NOT write HCL. When llm is None, uses deterministic pattern rules.
    """

    def reason(
        self,
        architecture: NormalizedArchitecture,
        detected_pattern_id: str | None,
        supported_patterns: list[str],
        current_plan: TerraformGenerationPlan | None = None,
        options: dict | None = None,
        llm: LLMProvider | None = None,
    ) -> TerraformReasoningResult:
        options = options or {}

        # --- Deterministic path (no LLM) ---
        if llm is None:
            return self._deterministic_reason(architecture, detected_pattern_id)

        # --- LLM path ---
        try:
            arch_json = architecture.model_dump_json(indent=2) if hasattr(architecture, "model_dump_json") else "{}"
            plan_json = current_plan.model_dump_json(indent=2) if current_plan else None
            prompt = f"{SYSTEM_PROMPT}\n\n{build_reasoning_prompt(arch_json, detected_pattern_id, supported_patterns, plan_json)}"
            raw = run_awaitable(llm.complete(prompt))
            result = _parse_llm_reasoning(raw, detected_pattern_id)
            if result.reasoning_status == "FAILED":
                logger.info("LLM reasoning failed to parse — falling back to deterministic rules.")
                return self._deterministic_reason(architecture, detected_pattern_id)
            return result
        except Exception as exc:
            logger.warning("LLM reasoning call failed (%s) — falling back to deterministic rules.", type(exc).__name__)
            return self._deterministic_reason(architecture, detected_pattern_id)

    def _deterministic_reason(
        self,
        architecture: NormalizedArchitecture,
        pattern_id: str | None,
    ) -> TerraformReasoningResult:
        if pattern_id == "ecs_fargate_alb_rds_dev":
            return _deterministic_ecs_reasoning(architecture)
        if pattern_id == "static_site_s3_cloudfront_route53_https":
            return _deterministic_static_site_reasoning()
        if pattern_id in {
            "serverless_http_api_lambda_dynamodb",
            "websocket_lobby_lambda_dynamodb",
            "async_processing_s3_sqs_worker",
            "secure_internal_dashboard_ecs_rds_cognito",
            "usage_analytics_ingestion_pipeline",
        }:
            return _deterministic_generic_pattern_reasoning(pattern_id)
        return TerraformReasoningResult(
            reasoning_status="UNSUPPORTED",
            pattern_id=pattern_id,
            terraform_strategy_summary="No deterministic reasoning rules exist for this pattern.",
            unsupported_reasons=[f"No deterministic reasoning rules for pattern: {pattern_id or 'unknown'}"],
        )
