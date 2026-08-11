"""Tests for TerraformReviewerAgent."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import MagicMock

from app.llm.base import LLMProvider
from app.review.terraform_reviewer_agent import TerraformReviewerAgent
from app.schemas.architecture import FileArtifact
from app.schemas.plan import TerraformGenerationPlan
from app.safety.findings import SafetyCheckResult
from app.services.architecture_normalizer import normalize_architecture, CanonicalArchitecture


def _agent() -> TerraformReviewerAgent:
    return TerraformReviewerAgent()


def _dummy_plan() -> TerraformGenerationPlan:
    return TerraformGenerationPlan(
        pattern_id="ecs_fargate_alb_rds_dev",
        project_name="nimbus",
        environment="dev",
        aws_region="us-east-1",
        architecture_id="arch-123",
        architecture_version="1.0.0",
        deployment_strategy="public_ecs_no_nat_low_cost_dev",
    )


def _dummy_arch() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate({
        "architecture_id": "arch-123",
        "cloud": {"provider": "aws", "region": "us-east-1"},
        "resources": [],
    })


# ---------------------------------------------------------------------------
# Test 1: Reviewer can be skipped when LLM_PROVIDER=none
# ---------------------------------------------------------------------------

def test_reviewer_skipped_when_no_llm() -> None:
    normalized = normalize_architecture(_dummy_arch(), "us-east-1")
    result = _agent().review(
        architecture=normalized,
        plan=_dummy_plan(),
        files=[],
        validation_result=None,
        safety_findings=SafetyCheckResult(passed=True, has_critical=False),
        llm=None,  # skipped
    )

    assert result.review_status == "SKIPPED"
    assert result.trusted is True


# ---------------------------------------------------------------------------
# Test 2: Reviewer parsing LLM output (mocked using Future)
# ---------------------------------------------------------------------------

def test_reviewer_with_mocked_llm_passed() -> None:
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "mocked"
    
    # Create a resolved future to mock the async complete call
    fut = asyncio.Future()
    fut.set_result("""
    {
      "review_status": "PASSED",
      "trusted": true,
      "critical_issues": [],
      "warnings": [],
      "recommendations": ["Optimize backend tags"],
      "faithfulness_score": 1.0,
      "deployability_score": 1.0
    }
    """)
    mock_llm.complete = MagicMock(return_value=fut)

    normalized = normalize_architecture(_dummy_arch(), "us-east-1")
    result = _agent().review(
        architecture=normalized,
        plan=_dummy_plan(),
        files=[FileArtifact(path="main.tf", content="resource \"aws_vpc\" \"main\" {}")],
        validation_result=None,
        safety_findings=SafetyCheckResult(passed=True, has_critical=False),
        llm=mock_llm,
    )

    assert result.review_status == "PASSED"
    assert result.trusted is True
    assert result.faithfulness_score == 1.0
    assert result.deployability_score == 1.0


def test_reviewer_with_mocked_llm_needs_fix() -> None:
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "mocked"
    
    fut = asyncio.Future()
    fut.set_result("""
    {
      "review_status": "NEEDS_FIX",
      "trusted": false,
      "critical_issues": [
        {
          "severity": "CRITICAL",
          "file": "ecs.tf",
          "issue": "ECS tasks are placed in private subnets with assign_public_ip=false, but the architecture selected a public ECS no-NAT strategy.",
          "recommendation": "Use public subnets and assign_public_ip=true, or generate NAT/VPC endpoints."
        }
      ],
      "warnings": ["Unused acm_certificate_arn variable"],
      "recommendations": [],
      "faithfulness_score": 0.5,
      "deployability_score": 0.2
    }
    """)
    mock_llm.complete = MagicMock(return_value=fut)

    normalized = normalize_architecture(_dummy_arch(), "us-east-1")
    result = _agent().review(
        architecture=normalized,
        plan=_dummy_plan(),
        files=[FileArtifact(path="ecs.tf", content="assign_public_ip = false")],
        validation_result=None,
        safety_findings=SafetyCheckResult(passed=True, has_critical=False),
        llm=mock_llm,
    )

    assert result.review_status == "NEEDS_FIX"
    assert result.trusted is False
    assert len(result.critical_issues) == 1
    assert result.critical_issues[0].severity == "CRITICAL"
    assert "assign_public_ip=false" in result.critical_issues[0].issue
