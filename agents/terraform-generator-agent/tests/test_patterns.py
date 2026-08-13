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


def serverless_http_architecture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        {
            "architecture_id": "serverless-http-api",
            "cloud": {"provider": "AWS", "region": "us-east-1"},
            "resources": [
                {"id": "api", "provider_type": "aws_apigatewayv2_api", "configuration": {"protocol_type": "HTTP"}},
                {"id": "handler", "provider_type": "aws_lambda_function", "configuration": {"runtime": "python3.12", "handler": "handler.main"}},
                {"id": "table", "provider_type": "aws_dynamodb_table"},
            ],
            "relationships": [
                {"source": "api", "target": "handler", "label": "ANY /api/{proxy+}"},
                {"source": "handler", "target": "table", "label": "reads and writes"},
            ],
        }
    )


def websocket_lobby_architecture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        {
            "architecture_id": "websocket-lobby",
            "cloud": {"provider": "AWS", "region": "us-east-1"},
            "resources": [
                {"id": "ws-api", "provider_type": "aws_apigatewayv2_api", "configuration": {"protocol_type": "WEBSOCKET"}},
                {"id": "connect-handler", "provider_type": "aws_lambda_function"},
                {"id": "join-handler", "provider_type": "aws_lambda_function"},
                {"id": "lobby-state", "provider_type": "aws_dynamodb_table"},
            ],
            "relationships": [
                {"source": "ws-api", "target": "connect-handler", "label": "$connect"},
                {"source": "ws-api", "target": "join-handler", "label": "joinLobby"},
                {"source": "join-handler", "target": "lobby-state", "label": "updates state"},
            ],
        }
    )


def async_processing_architecture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        {
            "architecture_id": "async-worker",
            "cloud": {"provider": "AWS", "region": "us-east-1"},
            "resources": [
                {"id": "source-bucket", "provider_type": "aws_s3_bucket"},
                {"id": "jobs-queue", "provider_type": "aws_sqs_queue"},
                {"id": "worker", "provider_type": "aws_lambda_function"},
                {"id": "job-status", "provider_type": "aws_dynamodb_table"},
            ],
            "relationships": [
                {"source": "source-bucket", "target": "jobs-queue", "label": "s3:ObjectCreated:*"},
                {"source": "jobs-queue", "target": "worker", "label": "consumed by"},
                {"source": "worker", "target": "job-status", "label": "updates"},
            ],
        }
    )


def secure_dashboard_architecture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        {
            "architecture_id": "secure-dashboard",
            "cloud": {"provider": "AWS", "region": "us-east-1"},
            "resources": [
                {"id": "alb", "provider_type": "aws_lb"},
                {"id": "dashboard", "provider_type": "aws_ecs_service"},
                {"id": "postgres", "provider_type": "aws_db_instance"},
                {"id": "users", "provider_type": "aws_cognito_user_pool"},
                {"id": "users-client", "provider_type": "aws_cognito_user_pool_client"},
                {"id": "audit-logs", "provider_type": "aws_s3_bucket"},
            ],
            "relationships": [
                {"source": "alb", "target": "dashboard", "label": "forwards traffic"},
                {"source": "alb", "target": "users", "label": "authenticates users"},
                {"source": "dashboard", "target": "postgres", "label": "reads data"},
            ],
        }
    )


def analytics_pipeline_architecture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        {
            "architecture_id": "usage-analytics",
            "cloud": {"provider": "AWS", "region": "us-east-1"},
            "resources": [
                {"id": "ingest-api", "provider_type": "aws_apigatewayv2_api", "configuration": {"protocol_type": "HTTP"}},
                {"id": "ingest-queue", "provider_type": "aws_sqs_queue"},
                {"id": "processor", "provider_type": "aws_lambda_function"},
                {"id": "raw-events", "provider_type": "aws_s3_bucket"},
                {"id": "aggregates", "provider_type": "aws_dynamodb_table"},
            ],
            "relationships": [
                {"source": "ingest-api", "target": "ingest-queue", "label": "POST /events"},
                {"source": "ingest-queue", "target": "processor", "label": "consumed by"},
                {"source": "processor", "target": "raw-events", "label": "stores raw events"},
                {"source": "processor", "target": "aggregates", "label": "updates aggregates"},
            ],
        }
    )


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


def test_serverless_http_api_lambda_dynamodb_pattern_is_detected() -> None:
    normalized = normalize_architecture(serverless_http_architecture(), "us-east-1")
    plan = PatternRegistry().detect(normalized, GenerateOptions(), Settings())

    assert plan is not None
    assert plan.pattern_id == "serverless_http_api_lambda_dynamodb"


def test_websocket_lobby_pattern_is_detected() -> None:
    normalized = normalize_architecture(websocket_lobby_architecture(), "us-east-1")
    plan = PatternRegistry().detect(normalized, GenerateOptions(), Settings())

    assert plan is not None
    assert plan.pattern_id == "websocket_lobby_lambda_dynamodb"


def test_async_processing_pattern_is_detected() -> None:
    normalized = normalize_architecture(async_processing_architecture(), "us-east-1")
    plan = PatternRegistry().detect(normalized, GenerateOptions(), Settings())

    assert plan is not None
    assert plan.pattern_id == "async_processing_s3_sqs_worker"


def test_secure_dashboard_pattern_is_detected() -> None:
    normalized = normalize_architecture(secure_dashboard_architecture(), "us-east-1")
    plan = PatternRegistry().detect(normalized, GenerateOptions(), Settings())

    assert plan is not None
    assert plan.pattern_id == "secure_internal_dashboard_ecs_rds_cognito"


def test_usage_analytics_pattern_is_detected() -> None:
    normalized = normalize_architecture(analytics_pipeline_architecture(), "us-east-1")
    plan = PatternRegistry().detect(normalized, GenerateOptions(), Settings())

    assert plan is not None
    assert plan.pattern_id == "usage_analytics_ingestion_pipeline"


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

    assert response.generation_status in {"SUCCESS", "NEEDS_REVIEW"}
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

    assert response.generation_status in {"SUCCESS", "NEEDS_REVIEW"}
    assert {
        "aws_ecs_task_definition",
        "aws_lb_target_group",
        "aws_lb_listener",
        "aws_db_subnet_group",
        "random_password",
        "aws_secretsmanager_secret_version",
    }.issubset(derived_types)


def test_serverless_http_generation_renders_lambda_api_and_table(tmp_path) -> None:
    response = service(tmp_path).generate(serverless_http_architecture(), GenerateOptions())
    files = file_map(response)

    assert response.pattern_id == "serverless_http_api_lambda_dynamodb"
    assert {"api_gateway.tf", "lambda.tf", "database.tf", "iam.tf", "observability.tf"}.issubset(files)
    assert 'resource "aws_apigatewayv2_route" "http_route"' in files["api_gateway.tf"]
    assert 'route_key = "ANY /api/{proxy+}"' in files["api_gateway.tf"]
    assert 'resource "aws_lambda_permission" "allow_http_api"' in files["lambda.tf"]
    assert 'resource "aws_dynamodb_table" "table"' in files["database.tf"]


def test_websocket_generation_renders_expected_lobby_routes(tmp_path) -> None:
    response = service(tmp_path).generate(websocket_lobby_architecture(), GenerateOptions())
    files = file_map(response)

    assert response.pattern_id == "websocket_lobby_lambda_dynamodb"
    assert 'protocol_type = "WEBSOCKET"' in files["api_gateway.tf"]
    assert 'route_key = "$connect"' in files["api_gateway.tf"]
    assert 'route_key = "joinLobby"' in files["api_gateway.tf"]
    assert 'resource "aws_lambda_permission"' in files["lambda.tf"]


def test_async_processing_generation_wires_s3_sqs_and_worker(tmp_path) -> None:
    response = service(tmp_path).generate(async_processing_architecture(), GenerateOptions())
    files = file_map(response)

    assert response.pattern_id == "async_processing_s3_sqs_worker"
    assert 'resource "aws_s3_bucket_notification" "source_events"' in files["storage.tf"]
    assert '"s3:ObjectCreated:*"' in files["storage.tf"]
    assert 'resource "aws_lambda_event_source_mapping" "worker_queue"' in files["lambda.tf"]
    assert 'resource "aws_sqs_queue" "jobs_queue_dlq"' in files["storage.tf"]


def test_usage_analytics_generation_wires_api_queue_lambda(tmp_path) -> None:
    response = service(tmp_path).generate(analytics_pipeline_architecture(), GenerateOptions())
    files = file_map(response)

    assert response.pattern_id == "usage_analytics_ingestion_pipeline"
    assert 'integration_subtype = "SQS-SendMessage"' in files["api_gateway.tf"]
    assert 'route_key = "POST /events"' in files["api_gateway.tf"]
    assert 'resource "aws_lambda_event_source_mapping" "analytics_processor"' in files["lambda.tf"]


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


@pytest.mark.skipif(shutil.which("terraform") is None, reason="Terraform CLI is not installed")
def test_generated_ecs_terraform_validates_when_cli_available(tmp_path) -> None:
    response = service(tmp_path).generate(ecs_architecture())
    validator = TerraformValidatorService(
        Settings(
            generated_artifacts_dir=str(tmp_path / "generated"),
            validation_enable_terraform_init=False,
        )
    )

    result = validator.validate(response.files)

    assert result.validation_status == "PASSED"
