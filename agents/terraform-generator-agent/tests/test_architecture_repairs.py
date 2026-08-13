import json
from pathlib import Path

from app.core.config import Settings
from app.schemas.architecture import CanonicalArchitecture, GenerateOptions
from app.services.generator_service import TerraformGeneratorService


ROOT = Path(__file__).parent / "fixtures"


def test_unsupported_resource_returns_clean_status(tmp_path):
    payload = json.loads((ROOT / "unsupported_eks_architecture.json").read_text())
    service = TerraformGeneratorService(Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none"))
    response = service.generate(CanonicalArchitecture.model_validate(payload), GenerateOptions())
    assert response.generation_status == "UNSUPPORTED"
    assert "aws_eks_cluster" in response.unsupported_resources
    assert response.files == []


def test_none_provider_does_not_require_api_keys(tmp_path):
    fixture = json.loads((ROOT / "ecs_rds_architecture.json").read_text())
    service = TerraformGeneratorService(Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none"))
    response = service.generate(CanonicalArchitecture.model_validate(fixture))
    assert response.generation_status in {"SUCCESS", "NEEDS_REVIEW"}
    assert response.metadata.llm_provider == "none"
