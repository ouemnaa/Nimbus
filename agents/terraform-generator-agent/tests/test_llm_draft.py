"""Tests for LLMDraftTerraformGenerator and draft fallback behavior."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import MagicMock

from app.core.config import Settings
from app.llm.base import LLMProvider
from app.schemas.architecture import CanonicalArchitecture, GenerateOptions
from app.services.architecture_normalizer import normalize_architecture
from app.services.generator_service import TerraformGeneratorService
from app.fallback.llm_draft_generator import LLMDraftTerraformGenerator


def _settings(draft_enabled: bool = False, provider: str = "none") -> Settings:
    return Settings(
        app_environment="production",
        llm_provider=provider,
        terraform_llm_draft_fallback_enabled=draft_enabled,
        gemini_api_key="fake-key" if provider != "none" else None,
        gemini_model="gemini-1.5-flash" if provider != "none" else None,
    )


def _generator(settings: Settings) -> TerraformGeneratorService:
    return TerraformGeneratorService(settings)


def _unsupported_arch() -> CanonicalArchitecture:
    """An EKS architecture that doesn't match any deterministic patterns."""
    return CanonicalArchitecture.model_validate({
        "architecture_id": "unsupported-eks",
        "cloud": {"provider": "aws", "region": "us-east-1"},
        "resources": [
            {"id": "cluster", "provider_type": "aws_eks_cluster", "configuration": {}}
        ]
    })


# ---------------------------------------------------------------------------
# Test 1: Draft Fallback is enabled by default in development
# ---------------------------------------------------------------------------

def test_draft_fallback_enabled_by_default_in_development(tmp_path) -> None:
    settings = Settings(generated_artifacts_dir=str(tmp_path), llm_provider="none")
    assert settings.terraform_llm_draft_fallback_enabled is True


def test_draft_fallback_disabled_by_default_in_production(tmp_path) -> None:
    settings = Settings(
        generated_artifacts_dir=str(tmp_path),
        llm_provider="none",
        app_environment="production",
    )
    assert settings.terraform_llm_draft_fallback_enabled is False


# ---------------------------------------------------------------------------
# Test 2: Unsupported pattern returns UNSUPPORTED when disabled
# ---------------------------------------------------------------------------

def test_unsupported_pattern_returns_unsupported_when_disabled(tmp_path) -> None:
    settings = Settings(
        generated_artifacts_dir=str(tmp_path),
        llm_provider="none",
        terraform_llm_draft_fallback_enabled=False,
    )
    svc = _generator(settings)
    res = svc.generate(_unsupported_arch())

    assert res.generation_status == "UNSUPPORTED"
    assert res.generation_mode == "UNSUPPORTED"
    assert res.trusted is False
    assert len(res.files) == 0


# ---------------------------------------------------------------------------
# Test 3: Unsupported pattern returns LLM_DRAFT_UNSUPPORTED when enabled and LLM available
# ---------------------------------------------------------------------------

def test_unsupported_pattern_returns_draft_when_enabled_and_llm_available(tmp_path) -> None:
    # Set settings to mock a provider but override provider creation to inject mock LLM
    settings = Settings(
        generated_artifacts_dir=str(tmp_path),
        llm_provider="gemini",
        gemini_api_key="test-key",
        gemini_model="gemini-1.5-pro",
        terraform_llm_draft_fallback_enabled=True,
    )
    svc = _generator(settings)

    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"
    
    fut = asyncio.Future()
    fut.set_result("""
    {
      "files": [
        {"path": "compute.tf", "content": "resource \\"aws_eks_cluster\\" \\"this\\" {}"}
      ],
      "assumptions": ["Assumed default VPC exists"],
      "warnings": ["Experimental draft EKS"],
      "required_inputs": [],
      "validation_assertions": [],
      "unsupported_limitations": []
    }
    """)
    mock_llm.complete = MagicMock(return_value=fut)

    # Mock generator_service's provider instantiation
    import app.services.generator_service as gs
    orig_create = gs.create_provider
    gs.create_provider = lambda s: mock_llm

    try:
        res = svc.generate(_unsupported_arch())
        assert res.generation_status == "NEEDS_REVIEW"
        assert res.generation_mode == "LLM_DRAFT_UNSUPPORTED"
        assert res.trusted is False
        assert res.requires_human_review is True
        assert len(res.files) == 1
        assert res.files[0].path == "compute.tf"
        assert "aws_eks_cluster" in res.files[0].content
        assert res.validation is not None
        assert res.review is not None
    finally:
        gs.create_provider = orig_create


# ---------------------------------------------------------------------------
# Test 4: Invalid paths from LLM are rejected
# ---------------------------------------------------------------------------

def test_draft_path_validation() -> None:
    from app.fallback.llm_draft_generator import _validate_path
    assert _validate_path("networking.tf") is True
    assert _validate_path("compute.tf") is True
    assert _validate_path("variables.tf") is True
    assert _validate_path("README.generated.md") is True

    # Bad paths
    assert _validate_path("main.sh") is False
    assert _validate_path("/etc/passwd") is False
    assert _validate_path("../secrets.tf") is False
    assert _validate_path("..\\secrets.tf") is False
    assert _validate_path("terraform.tfvars") is False  # allowed is only .tfvars.example


# ---------------------------------------------------------------------------
# Test 5: LLM output with secrets is caught by safety checker
# ---------------------------------------------------------------------------

def test_draft_with_secrets_fails_safety_check(tmp_path) -> None:
    settings = Settings(
        generated_artifacts_dir=str(tmp_path),
        llm_provider="gemini",
        gemini_api_key="test-key",
        gemini_model="gemini-1.5-pro",
        terraform_llm_draft_fallback_enabled=True,
    )
    svc = _generator(settings)

    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"
    
    fut = asyncio.Future()
    fut.set_result("""
    {
      "files": [
        {
          "path": "providers.tf",
          "content": "provider \\"aws\\" {\\n  access_key = \\"AKIA1234567890ABCDEF\\"\\n}"
        }
      ],
      "assumptions": [],
      "warnings": [],
      "required_inputs": [],
      "validation_assertions": [],
      "unsupported_limitations": []
    }
    """)
    mock_llm.complete = MagicMock(return_value=fut)

    import app.services.generator_service as gs
    orig_create = gs.create_provider
    gs.create_provider = lambda s: mock_llm

    try:
        res = svc.generate(_unsupported_arch())
        assert res.generation_status == "FAILED"
        assert res.trusted is False
        assert res.requires_human_review is True
        assert len(res.files) == 0
        # Safety findings should list HARDCODED_AWS_KEY
        findings = [f["code"] for f in res.safety_findings]
        assert "HARDCODED_AWS_KEY" in findings
    finally:
        gs.create_provider = orig_create


def test_draft_pattern_guess_for_serverless_supabase(tmp_path) -> None:
    settings = Settings(
        generated_artifacts_dir=str(tmp_path),
        llm_provider="none",
        terraform_llm_draft_fallback_enabled=False,
        app_environment="production",
    )
    svc = _generator(settings)
    arch = CanonicalArchitecture.model_validate(
        {
            "architecture_id": "serverless-app",
            "cloud": {"provider": "aws", "region": "us-east-1"},
            "resources": [
                {"id": "api", "provider_type": "aws_apigatewayv2_api", "configuration": {}},
                {"id": "fn", "provider_type": "aws_lambda_function", "configuration": {}},
                {"id": "db", "provider_type": "external_supabase", "configuration": {}},
            ],
        }
    )

    res = svc.generate(arch)

    assert res.generation_status == "UNSUPPORTED"
    assert res.draft_pattern_guess == "serverless_http_api_lambda_external_db"
