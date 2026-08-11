"""Tests for TerraformReasoningAgent — deterministic mode (LLM_PROVIDER=none)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.schemas.architecture import CanonicalArchitecture
from app.services.architecture_normalizer import normalize_architecture
from app.reasoning.terraform_reasoning_agent import TerraformReasoningAgent

FIXTURES = Path(__file__).parent / "fixtures"


def _agent() -> TerraformReasoningAgent:
    return TerraformReasoningAgent()


def _ecs_public_no_nat() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        json.loads((FIXTURES / "ecs_public_no_nat_architecture.json").read_text())
    )


def _ecs_with_nat() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        json.loads((FIXTURES / "ecs_rds_architecture.json").read_text())
    )


def _private_ecs_no_nat() -> CanonicalArchitecture:
    """Architecture with private subnets only and no NAT — dangerous configuration."""
    return CanonicalArchitecture.model_validate({
        "architecture_id": "private-ecs-no-nat",
        "architecture_version": "1.0.0",
        "cloud": {"provider": "aws", "region": "us-east-1"},
        "resources": [
            {"id": "vpc", "provider_type": "aws_vpc", "configuration": {}},
            {"id": "private-sub-1", "provider_type": "aws_subnet",
             "configuration": {"subnet_type": "private", "public": False,
                               "cidr_block": "10.0.1.0/24", "availability_zone": "us-east-1a"}},
            {"id": "alb", "provider_type": "aws_lb", "configuration": {}},
            {"id": "ecs", "provider_type": "aws_ecs_service", "configuration": {}},
            {"id": "rds", "provider_type": "aws_db_instance", "configuration": {}},
        ],
    })


def _static_site() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate({
        "architecture_id": "static-site",
        "cloud": {"provider": "aws", "region": "us-east-1"},
        "resources": [
            {"id": "bucket", "provider_type": "aws_s3_bucket", "configuration": {}},
            {"id": "cdn", "provider_type": "aws_cloudfront_distribution", "configuration": {}},
            {"id": "cert", "provider_type": "aws_acm_certificate", "configuration": {}},
            {"id": "zone", "provider_type": "aws_route53_zone", "configuration": {}},
        ],
    })


# ---------------------------------------------------------------------------
# Test 1: Public no-NAT architecture → public_ecs_no_nat_low_cost_dev
# ---------------------------------------------------------------------------

def test_ecs_public_no_nat_strategy() -> None:
    arch = _ecs_public_no_nat()
    normalized = normalize_architecture(arch, "us-east-1")
    result = _agent().reason(
        architecture=normalized,
        detected_pattern_id="ecs_fargate_alb_rds_dev",
        supported_patterns=["ecs_fargate_alb_rds_dev"],
        llm=None,
    )

    assert result.reasoning_status == "SUCCESS"
    assert result.deployment_strategy == "public_ecs_no_nat_low_cost_dev"
    assert result.networking_strategy is not None
    assert result.networking_strategy.ecs_subnets == "public"
    assert result.networking_strategy.ecs_assign_public_ip is True
    assert result.networking_strategy.nat_gateway_required is False


# ---------------------------------------------------------------------------
# Test 2: Private subnets + no NAT → NEEDS_INPUT with CRITICAL risk
# ---------------------------------------------------------------------------

def test_private_ecs_no_nat_produces_critical_warning() -> None:
    arch = _private_ecs_no_nat()
    normalized = normalize_architecture(arch, "us-east-1")
    result = _agent().reason(
        architecture=normalized,
        detected_pattern_id="ecs_fargate_alb_rds_dev",
        supported_patterns=["ecs_fargate_alb_rds_dev"],
        llm=None,
    )

    assert result.reasoning_status == "NEEDS_INPUT"
    assert result.deployment_strategy is None
    assert len(result.runtime_risks) > 0
    # Should mention inability to pull images or write logs
    combined = " ".join(result.runtime_risks + result.warnings).lower()
    assert "pull" in combined or "nat" in combined or "private" in combined


# ---------------------------------------------------------------------------
# Test 3: Static site → static_site_s3_cloudfront_route53_https strategy
# ---------------------------------------------------------------------------

def test_static_site_strategy() -> None:
    arch = _static_site()
    normalized = normalize_architecture(arch, "us-east-1")
    result = _agent().reason(
        architecture=normalized,
        detected_pattern_id="static_site_s3_cloudfront_route53_https",
        supported_patterns=["static_site_s3_cloudfront_route53_https"],
        llm=None,
    )

    assert result.reasoning_status == "SUCCESS"
    assert result.deployment_strategy == "static_site_s3_cloudfront_route53_https"
    # Should include us-east-1 ACM assertion
    assertions = " ".join(result.validation_assertions)
    assert "us_east_1" in assertions or "us-east-1" in assertions


# ---------------------------------------------------------------------------
# Test 4: LLM_PROVIDER=none → deterministic reasoning still works
# ---------------------------------------------------------------------------

def test_deterministic_reasoning_works_without_llm() -> None:
    arch = _ecs_with_nat()
    normalized = normalize_architecture(arch, "us-east-1")

    # llm=None explicitly
    result = _agent().reason(
        architecture=normalized,
        detected_pattern_id="ecs_fargate_alb_rds_dev",
        supported_patterns=["ecs_fargate_alb_rds_dev"],
        llm=None,
    )

    # Should succeed with private_ecs_with_nat (fixture has NAT)
    assert result.reasoning_status == "SUCCESS"
    assert result.deployment_strategy == "private_ecs_with_nat"
    assert result.networking_strategy is not None
    assert result.networking_strategy.ecs_assign_public_ip is False
    assert result.networking_strategy.nat_gateway_required is True


# ---------------------------------------------------------------------------
# Test 5: Unknown pattern → UNSUPPORTED reasoning
# ---------------------------------------------------------------------------

def test_unknown_pattern_returns_unsupported() -> None:
    arch = CanonicalArchitecture.model_validate({
        "architecture_id": "unknown",
        "cloud": {"provider": "aws", "region": "us-east-1"},
        "resources": [{"id": "bucket", "provider_type": "aws_s3_bucket", "configuration": {}}],
    })
    normalized = normalize_architecture(arch, "us-east-1")
    result = _agent().reason(
        architecture=normalized,
        detected_pattern_id=None,
        supported_patterns=[],
        llm=None,
    )
    assert result.reasoning_status == "UNSUPPORTED"
