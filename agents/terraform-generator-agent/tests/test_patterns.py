import json
import shutil
from pathlib import Path

import pytest

from app.core.config import Settings
from app.schemas.architecture import CanonicalArchitecture, GenerateOptions
from app.services.architecture_normalizer import normalize_architecture
from app.services.generator_service import TerraformGeneratorService
from app.services.pattern_registry import PatternRegistry
from app.services.validator_service import TerraformValidatorService


FIXTURES = Path(__file__).parent / "fixtures"


def ecs_architecture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        json.loads((FIXTURES / "ecs_rds_architecture.json").read_text())
    )


def static_site_architecture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        {
            "architecture_id": "global-static-website",
            "architecture_version": "1.0.0",
            "cloud": {"provider": "AWS", "region": "us-east-1"},
            "resources": [
                {
                    "id": "site-bucket",
                    "name": "Site Bucket",
                    "provider_type": "aws_s3_bucket",
                    "configuration": {"bucket_name": "example-dev-site"},
                },
                {
                    "id": "cdn-oac",
                    "name": "CDN OAC",
                    "provider_type": "aws_cloudfront_origin_access_control",
                },
                {
                    "id": "cdn",
                    "name": "CDN",
                    "provider_type": "aws_cloudfront_distribution",
                    "configuration": {
                        "price_class": "PriceClass_100",
                        "default_root_object": "index.html",
                    },
                },
                {
                    "id": "cert",
                    "name": "Certificate",
                    "provider_type": "aws_acm_certificate",
                    "configuration": {"domain_name": "dev.example.com"},
                },
                {
                    "id": "zone",
                    "name": "Hosted Zone",
                    "provider_type": "aws_route53_zone",
                    "configuration": {"domain_name": "example.com"},
                },
            ],
        }
    )


def service(tmp_path) -> TerraformGeneratorService:
    return TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )


def file_map(response):
    return {artifact.path: artifact.content for artifact in response.files}


def test_static_site_pattern_is_detected() -> None:
    normalized = normalize_architecture(static_site_architecture(), "us-east-1")
    plan = PatternRegistry().detect(normalized, GenerateOptions(), Settings())

    assert plan is not None
    assert plan.pattern_id == "static_site_s3_cloudfront_route53_https"


def test_ecs_rds_pattern_is_detected() -> None:
    normalized = normalize_architecture(ecs_architecture(), "us-east-1")
    plan = PatternRegistry().detect(normalized, GenerateOptions(), Settings())

    assert plan is not None
    assert plan.pattern_id == "ecs_fargate_alb_rds_dev"


def test_unsupported_architecture_returns_missing_pattern_information(tmp_path) -> None:
    architecture = CanonicalArchitecture.model_validate(
        {
            "architecture_id": "bucket-only",
            "cloud": {"provider": "AWS", "region": "us-east-1"},
            "resources": [
                {
                    "id": "bucket",
                    "provider_type": "aws_s3_bucket",
                    "configuration": {"bucket_name": "bucket-only"},
                }
            ],
        }
    )

    response = service(tmp_path).generate(architecture)

    assert response.generation_status == "UNSUPPORTED"
    assert "No Terraform generation pattern matched" in (response.error or "")


def test_static_site_generation_uses_us_east_1_provider_alias_and_split_files(tmp_path) -> None:
    response = service(tmp_path).generate(static_site_architecture())
    files = file_map(response)

    assert response.generation_status == "SUCCESS"
    assert {"s3.tf", "acm.tf", "cloudfront.tf", "dns.tf"}.issubset(files)
    assert 'alias  = "us_east_1"' in files["providers.tf"]
    assert "provider          = aws.us_east_1" in files["acm.tf"]
    assert "custom_error_response" in files["cloudfront.tf"]
    assert "data \"aws_route53_zone\"" in files["dns.tf"]
    assert "aws s3 sync" in files["README.generated.md"]
    assert "aws cloudfront create-invalidation" in files["README.generated.md"]


def test_ecs_rds_generation_derives_required_implementation_resources(tmp_path) -> None:
    response = service(tmp_path).generate(ecs_architecture())
    derived_types = {item.type for item in response.derived_resources}

    assert response.generation_status == "SUCCESS"
    assert {
        "aws_ecs_task_definition",
        "aws_lb_target_group",
        "aws_lb_listener",
        "aws_db_subnet_group",
        "random_password",
        "aws_secretsmanager_secret_version",
    }.issubset(derived_types)


@pytest.mark.skipif(shutil.which("terraform") is None, reason="Terraform CLI is not installed")
def test_generated_terraform_validates_when_cli_available(tmp_path) -> None:
    response = service(tmp_path).generate(static_site_architecture())
    validator = TerraformValidatorService(
        Settings(
            generated_artifacts_dir=str(tmp_path / "generated"),
            validation_enable_terraform_init=False,
        )
    )

    result = validator.validate(response.files)

    assert result.validation_status == "PASSED"
