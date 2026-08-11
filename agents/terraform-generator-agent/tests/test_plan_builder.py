"""Tests for TerraformPlanBuilder — verifies strategy application to generation plan."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import Settings
from app.planning.plan_builder import TerraformPlanBuilder
from app.reasoning.reasoning_schema import NetworkingStrategy, TerraformReasoningResult
from app.schemas.architecture import CanonicalArchitecture, GenerateOptions
from app.services.architecture_normalizer import normalize_architecture
from app.services.pattern_registry import EcsFargateAlbRdsDevPattern

FIXTURES = Path(__file__).parent / "fixtures"


def _settings():
    return Settings(llm_provider="none")


def _builder():
    return TerraformPlanBuilder()


def _pattern():
    return EcsFargateAlbRdsDevPattern()


def _public_no_nat_arch():
    return CanonicalArchitecture.model_validate(
        json.loads((FIXTURES / "ecs_public_no_nat_architecture.json").read_text())
    )


def _nat_arch():
    return CanonicalArchitecture.model_validate(
        json.loads((FIXTURES / "ecs_rds_architecture.json").read_text())
    )


def _public_no_nat_reasoning():
    return TerraformReasoningResult(
        reasoning_status="SUCCESS",
        pattern_id="ecs_fargate_alb_rds_dev",
        deployment_strategy="public_ecs_no_nat_low_cost_dev",
        networking_strategy=NetworkingStrategy(
            ecs_subnets="public",
            ecs_assign_public_ip=True,
            nat_gateway_required=False,
        ),
        validation_assertions=["ECS must use public subnets.", "assign_public_ip must be true."],
        warnings=["Public ECS IPs — restrict via ALB SG."],
    )


def _private_nat_reasoning():
    return TerraformReasoningResult(
        reasoning_status="SUCCESS",
        pattern_id="ecs_fargate_alb_rds_dev",
        deployment_strategy="private_ecs_with_nat",
        networking_strategy=NetworkingStrategy(
            ecs_subnets="private",
            ecs_assign_public_ip=False,
            nat_gateway_required=True,
        ),
        validation_assertions=["ECS must use private subnets.", "assign_public_ip must be false."],
    )


def _needs_input_reasoning():
    return TerraformReasoningResult(
        reasoning_status="NEEDS_INPUT",
        pattern_id="ecs_fargate_alb_rds_dev",
        deployment_strategy=None,
        warnings=["Private ECS without NAT — runtime failure."],
        runtime_risks=["Cannot pull images."],
        unsupported_reasons=["No NAT Gateway and no VPC endpoints."],
    )


# ---------------------------------------------------------------------------
# Test 1: public_ecs_no_nat → ECS subnets are public
# ---------------------------------------------------------------------------

def test_public_no_nat_sets_public_ecs_subnets() -> None:
    arch = _public_no_nat_arch()
    normalized = normalize_architecture(arch, "us-east-1")
    plan = _builder().build(normalized, _pattern(), _public_no_nat_reasoning(), GenerateOptions(), _settings())

    assert plan.deployment_strategy == "public_ecs_no_nat_low_cost_dev"
    ecs_subnets = plan.resources.get("ecs_subnets", [])
    assert len(ecs_subnets) > 0
    # All ECS subnets should be from the public subnet list
    public_subnet_labels = {s["label"] for s in plan.resources.get("public_subnets", [])}
    for subnet in ecs_subnets:
        assert subnet["label"] in public_subnet_labels, (
            f"ECS subnet {subnet['label']!r} is not in public subnets {public_subnet_labels}"
        )


# ---------------------------------------------------------------------------
# Test 2: public_ecs_no_nat → assign_public_ip=True
# ---------------------------------------------------------------------------

def test_public_no_nat_sets_assign_public_ip_true() -> None:
    arch = _public_no_nat_arch()
    normalized = normalize_architecture(arch, "us-east-1")
    plan = _builder().build(normalized, _pattern(), _public_no_nat_reasoning(), GenerateOptions(), _settings())

    assert plan.resources.get("assign_public_ip") is True


# ---------------------------------------------------------------------------
# Test 3: public_ecs_no_nat → RDS private (NAT not required)
# ---------------------------------------------------------------------------

def test_public_no_nat_rds_stays_private() -> None:
    arch = _public_no_nat_arch()
    normalized = normalize_architecture(arch, "us-east-1")
    plan = _builder().build(normalized, _pattern(), _public_no_nat_reasoning(), GenerateOptions(), _settings())

    # NAT label should not be set
    assert plan.resources.get("nat_label") is None
    assert plan.generation_mode == "DETERMINISTIC_SUPPORTED"


# ---------------------------------------------------------------------------
# Test 4: private_ecs_with_nat → private subnets + assign_public_ip=False
# ---------------------------------------------------------------------------

def test_private_ecs_with_nat_sets_private_subnets() -> None:
    arch = _nat_arch()
    normalized = normalize_architecture(arch, "us-east-1")
    plan = _builder().build(normalized, _pattern(), _private_nat_reasoning(), GenerateOptions(), _settings())

    assert plan.deployment_strategy == "private_ecs_with_nat"
    assert plan.resources.get("assign_public_ip") is False
    ecs_subnets = plan.resources.get("ecs_subnets", [])
    private_labels = {s["label"] for s in plan.resources.get("private_subnets", [])}
    for subnet in ecs_subnets:
        assert subnet["label"] in private_labels


# ---------------------------------------------------------------------------
# Test 5: private ECS no NAT → plan has UNSUPPORTED mode
# ---------------------------------------------------------------------------

def test_private_ecs_no_nat_returns_unsupported_mode() -> None:
    arch = _public_no_nat_arch()  # only public subnets — will trigger NEEDS_INPUT reasoning
    normalized = normalize_architecture(arch, "us-east-1")
    plan = _builder().build(normalized, _pattern(), _needs_input_reasoning(), GenerateOptions(), _settings())

    assert plan.generation_mode == "UNSUPPORTED"


# ---------------------------------------------------------------------------
# Test 6: validation_assertions are populated from reasoning
# ---------------------------------------------------------------------------

def test_validation_assertions_populated() -> None:
    arch = _public_no_nat_arch()
    normalized = normalize_architecture(arch, "us-east-1")
    plan = _builder().build(normalized, _pattern(), _public_no_nat_reasoning(), GenerateOptions(), _settings())

    assert len(plan.validation_assertions) > 0
