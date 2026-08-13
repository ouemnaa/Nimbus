from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from app.core.config import Settings
from app.llm.base import LLMProvider
from app.planning.terraform_resource_plan_coverage_validator import TerraformResourcePlanCoverageValidator
from app.planning.terraform_resource_plan_schema import TerraformResourcePlan
from app.rendering.generic_hcl_renderer import GenericHCLRenderer
from app.schemas.architecture import CanonicalArchitecture
from app.services.architecture_normalizer import normalize_architecture
from app.services.generator_service import TerraformGeneratorService


def _generator(settings: Settings) -> TerraformGeneratorService:
    return TerraformGeneratorService(settings)


def _unsupported_arch() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        {
            "architecture_id": "serverless-app",
            "cloud": {"provider": "aws", "region": "us-east-1"},
            "resources": [
                {"id": "api-gateway", "provider_type": "aws_apigatewayv2_api", "configuration": {}},
                {"id": "central-backend", "provider_type": "aws_lambda_function", "configuration": {}},
                {"id": "supabase", "provider_type": "external_supabase", "configuration": {}},
            ],
        }
    )


def _multi_lambda_arch() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(
        {
            "architecture_id": "flutter-multigame-backend",
            "cloud": {"provider": "aws", "region": "us-east-1"},
            "resources": [
                {
                    "id": "api-gateway",
                    "provider_type": "aws_apigatewayv2_api",
                    "configuration": {
                        "cors_configuration": {
                            "allow_origins": ["*"],
                            "allow_methods": ["GET", "POST", "OPTIONS"],
                            "allow_headers": ["Content-Type", "Authorization"],
                        }
                    },
                },
                {
                    "id": "central-backend-lambda",
                    "name": "Central Backend Lambda",
                    "provider_type": "aws_lambda_function",
                    "configuration": {"runtime": "nodejs18.x", "memory_size": 512, "timeout": 29},
                },
                {
                    "id": "game-backend-lambda",
                    "name": "Game Backend Lambda",
                    "provider_type": "aws_lambda_function",
                    "configuration": {"runtime": "nodejs18.x", "memory_size": 768, "timeout": 45},
                },
                {"id": "supabase-external", "provider_type": "external_supabase", "configuration": {}},
            ],
            "relationships": [
                {"source_id": "api-gateway", "target_id": "central-backend-lambda", "label": "Routes /api/central/*"},
                {"source_id": "api-gateway", "target_id": "game-backend-lambda", "label": "Routes /api/games/*"},
            ],
        }
    )


def _plan_json() -> str:
    return json.dumps(
        {
            "plan_version": "1.0.0",
            "draft_pattern_name": "serverless_http_api_lambda_external_db",
            "cloud_provider": "AWS",
            "terraform_version": ">= 1.5.0",
            "required_providers": [
                {"name": "aws", "source": "hashicorp/aws", "version": "~> 5.0"}
            ],
            "variables": [
                {"name": "aws_region", "type": "string", "description": "AWS region", "default": {"kind": "literal", "value": "us-east-1"}, "required": True},
                {"name": "project_name", "type": "string", "description": "Project name", "required": True},
                {"name": "environment", "type": "string", "description": "Environment", "default": {"kind": "literal", "value": "development"}, "required": True},
                {"name": "lambda_package_path", "type": "string", "description": "Lambda zip path", "required": True},
                {"name": "lambda_runtime", "type": "string", "description": "Runtime", "default": {"kind": "literal", "value": "nodejs20.x"}, "required": True},
                {"name": "lambda_handler", "type": "string", "description": "Handler", "default": {"kind": "literal", "value": "index.handler"}, "required": True},
                {"name": "supabase_url", "type": "string", "description": "Supabase URL", "required": True},
                {"name": "supabase_service_role_key", "type": "string", "description": "Supabase key", "required": True, "sensitive": True},
            ],
            "data_sources": [
                {"terraform_type": "aws_caller_identity", "name": "current", "file": "providers.tf", "body": {}}
            ],
            "resources": [
                {"terraform_type": "aws_secretsmanager_secret", "name": "supabase", "file": "secrets.tf", "architecture_resource_id": "supabase", "body": {"name": {"kind": "expr", "value": "format(\"%s-%s-supabase\", var.project_name, var.environment)"}}}, 
                {"terraform_type": "aws_secretsmanager_secret_version", "name": "supabase", "file": "secrets.tf", "body": {"secret_id": {"kind": "expr", "value": "aws_secretsmanager_secret.supabase.id"}, "secret_string": {"kind": "expr", "value": "jsonencode({SUPABASE_URL = var.supabase_url, SUPABASE_SERVICE_ROLE_KEY = var.supabase_service_role_key})"}}},
                {"terraform_type": "aws_iam_role", "name": "lambda_execution_role", "file": "iam.tf", "body": {"name": {"kind": "expr", "value": "format(\"%s-%s-lambda-role\", var.project_name, var.environment)"}, "assume_role_policy": {"kind": "expr", "value": "jsonencode({Version = \"2012-10-17\", Statement = [{Effect = \"Allow\", Principal = {Service = \"lambda.amazonaws.com\"}, Action = \"sts:AssumeRole\"}]})"}}},
                {"terraform_type": "aws_iam_role_policy_attachment", "name": "lambda_basic", "file": "iam.tf", "body": {"role": {"kind": "expr", "value": "aws_iam_role.lambda_execution_role.name"}, "policy_arn": {"kind": "literal", "value": "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"}}},
                {"terraform_type": "aws_cloudwatch_log_group", "name": "central_backend", "file": "observability.tf", "architecture_resource_id": "central-backend", "body": {"name": {"kind": "expr", "value": "format(\"/aws/lambda/%s-%s-central\", var.project_name, var.environment)"}, "retention_in_days": {"kind": "literal", "value": 7}}},
                {"terraform_type": "aws_lambda_function", "name": "central_backend", "file": "lambda.tf", "architecture_resource_id": "central-backend", "body": {"function_name": {"kind": "expr", "value": "format(\"%s-%s-central\", var.project_name, var.environment)"}, "role": {"kind": "expr", "value": "aws_iam_role.lambda_execution_role.arn"}, "runtime": {"kind": "expr", "value": "var.lambda_runtime"}, "handler": {"kind": "expr", "value": "var.lambda_handler"}, "filename": {"kind": "expr", "value": "var.lambda_package_path"}, "environment": {"kind": "block", "type": "environment", "body": {"variables": {"kind": "object", "items": {"ENVIRONMENT": {"kind": "expr", "value": "var.environment"}, "SUPABASE_SECRET_ARN": {"kind": "expr", "value": "aws_secretsmanager_secret.supabase.arn"}}}}}}},
                {"terraform_type": "aws_apigatewayv2_api", "name": "http_api", "file": "api_gateway.tf", "architecture_resource_id": "api-gateway", "body": {"name": {"kind": "expr", "value": "format(\"%s-%s-http-api\", var.project_name, var.environment)"}, "protocol_type": {"kind": "literal", "value": "HTTP"}}},
                {"terraform_type": "aws_apigatewayv2_integration", "name": "central_backend", "file": "api_gateway.tf", "body": {"api_id": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.id"}, "integration_type": {"kind": "literal", "value": "AWS_PROXY"}, "integration_uri": {"kind": "expr", "value": "aws_lambda_function.central_backend.invoke_arn"}, "integration_method": {"kind": "literal", "value": "POST"}}},
                {"terraform_type": "aws_apigatewayv2_route", "name": "central_backend", "file": "api_gateway.tf", "body": {"api_id": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.id"}, "route_key": {"kind": "literal", "value": "ANY /api/central/{proxy+}"}, "target": {"kind": "expr", "value": "\"integrations/${aws_apigatewayv2_integration.central_backend.id}\""}}},
                {"terraform_type": "aws_apigatewayv2_stage", "name": "default", "file": "api_gateway.tf", "body": {"api_id": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.id"}, "name": {"kind": "literal", "value": "$default"}, "auto_deploy": {"kind": "literal", "value": True}}},
                {"terraform_type": "aws_lambda_permission", "name": "allow_api_gateway", "file": "lambda.tf", "body": {"statement_id": {"kind": "literal", "value": "AllowExecutionFromAPIGateway"}, "action": {"kind": "literal", "value": "lambda:InvokeFunction"}, "function_name": {"kind": "expr", "value": "aws_lambda_function.central_backend.function_name"}, "principal": {"kind": "literal", "value": "apigateway.amazonaws.com"}, "source_arn": {"kind": "expr", "value": "format(\"%s/*/*\", aws_apigatewayv2_api.http_api.execution_arn)"}}},
            ],
            "outputs": [
                {"name": "api_endpoint", "description": "HTTP API endpoint.", "value": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.api_endpoint"}, "sensitive": False}
            ],
            "architecture_resource_mappings": [
                {"architecture_resource_id": "api-gateway", "provider_type": "aws_apigatewayv2_api", "mapping_status": "RENDERED", "terraform_addresses": ["aws_apigatewayv2_api.http_api"], "notes": ""},
                {"architecture_resource_id": "central-backend", "provider_type": "aws_lambda_function", "mapping_status": "RENDERED", "terraform_addresses": ["aws_lambda_function.central_backend"], "notes": ""},
                {"architecture_resource_id": "supabase", "provider_type": "external_supabase", "mapping_status": "EXTERNAL", "terraform_addresses": [], "notes": "Represented through variables and Secrets Manager."}
            ],
            "external_dependencies": [
                {"architecture_resource_id": "supabase", "provider_type": "external_supabase", "name": "Supabase", "handling": "variables_and_secret_reference", "notes": ""}
            ],
            "derived_resources": [
                {"terraform_type": "aws_lambda_permission", "name": "allow_api_gateway", "reason": "API Gateway invoke permission", "file": "lambda.tf"}
            ],
            "missing_inputs": ["lambda_package_path", "supabase_url", "supabase_service_role_key"],
            "assumptions": ["One central backend Lambda is rendered as the main entrypoint."],
            "warnings": ["Draft plan for unsupported architecture."],
            "runtime_risks": ["Ensure Lambda package exists before apply."],
            "validation_assertions": ["API Gateway route should point to Lambda integration."]
        }
    )


def _settings(tmp_path, enabled: bool = True, provider: str = "gemini") -> Settings:
    return Settings(
        generated_artifacts_dir=str(tmp_path),
        llm_provider=provider,
        gemini_api_key="fake-key" if provider != "none" else None,
        gemini_model="gemini-3.5-flash-lite" if provider != "none" else None,
        terraform_llm_draft_fallback_enabled=enabled,
    )


def test_unknown_architecture_returns_unsupported_when_planner_disabled(tmp_path) -> None:
    res = _generator(_settings(tmp_path, enabled=False, provider="none")).generate(_unsupported_arch())
    assert res.generation_status == "UNSUPPORTED"


def test_unknown_architecture_returns_llm_planned_generic_render(tmp_path) -> None:
    settings = _settings(tmp_path, enabled=True)
    svc = _generator(settings)
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"
    mock_llm.complete = AsyncMock(return_value=_plan_json())

    import app.services.generator_service as gs
    orig_create = gs.create_provider
    gs.create_provider = lambda s: mock_llm
    try:
        res = svc.generate(_unsupported_arch())
        assert res.generation_status == "NEEDS_REVIEW"
        assert res.generation_mode == "LLM_PLANNED_GENERIC_RENDER"
        assert res.trusted is False
        assert res.requires_human_review is True
        assert len(res.files) > 0
        assert res.terraform_resource_plan is not None
        assert len(res.architecture_resource_mappings) == 3
        assert any(dep["provider_type"] == "external_supabase" for dep in res.external_dependencies)
    finally:
        gs.create_provider = orig_create


def test_generic_renderer_converts_plan_into_tf_files() -> None:
    plan = TerraformResourcePlan.model_validate(json.loads(_plan_json()))
    artifacts = GenericHCLRenderer().render(plan)
    file_map = {item["path"]: item["content"] for item in artifacts}
    assert "lambda.tf" in file_map
    assert 'resource "aws_lambda_function" "central_backend"' in file_map["lambda.tf"]
    assert "api_gateway.tf" in file_map
    assert "terraform.tfvars.example" in file_map
    assert "<sensitive>" in file_map["terraform.tfvars.example"]


def test_expression_and_literal_rendering() -> None:
    plan = TerraformResourcePlan.model_validate(json.loads(_plan_json()))
    file_map = {item["path"]: item["content"] for item in GenericHCLRenderer().render(plan)}
    assert 'runtime = var.lambda_runtime' in file_map["lambda.tf"]
    assert 'protocol_type = "HTTP"' in file_map["api_gateway.tf"]
    assert "environment {" in file_map["lambda.tf"]
    assert 'required_version = ">= 1.5.0"' in file_map["versions.tf"]


def test_every_architecture_resource_has_mapping() -> None:
    plan = TerraformResourcePlan.model_validate(json.loads(_plan_json()))
    mapped = {item.architecture_resource_id for item in plan.architecture_resource_mappings}
    assert mapped == {"api-gateway", "central-backend", "supabase"}


def test_external_supabase_marked_external_and_sensitive_inputs_present() -> None:
    plan = TerraformResourcePlan.model_validate(json.loads(_plan_json()))
    mapping = next(item for item in plan.architecture_resource_mappings if item.architecture_resource_id == "supabase")
    secret_var = next(item for item in plan.variables if item.name == "supabase_service_role_key")
    assert mapping.mapping_status == "EXTERNAL"
    assert secret_var.sensitive is True


def test_multi_lambda_serverless_synthesis_preserves_lambdas_and_routes(tmp_path) -> None:
    settings = _settings(tmp_path, enabled=True)
    svc = _generator(settings)
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"
    mock_llm.complete = AsyncMock(return_value=json.dumps({"draft_pattern_name": "serverless_http_api_lambda_external_db"}))

    import app.services.generator_service as gs
    orig_create = gs.create_provider
    gs.create_provider = lambda s: mock_llm
    try:
        res = svc.generate(_multi_lambda_arch())
        assert res.generation_status == "NEEDS_REVIEW"
        file_map = {item.path: item.content for item in res.files}
        assert 'resource "aws_lambda_function" "central_backend_lambda"' in file_map["lambda.tf"]
        assert 'resource "aws_lambda_function" "game_backend_lambda"' in file_map["lambda.tf"]
        assert 'runtime = "nodejs18.x"' in file_map["lambda.tf"]
        assert "memory_size = 768" in file_map["lambda.tf"]
        assert "timeout = 45" in file_map["lambda.tf"]
        assert 'route_key = "ANY /api/central/{proxy+}"' in file_map["api_gateway.tf"]
        assert 'route_key = "ANY /api/games/{proxy+}"' in file_map["api_gateway.tf"]
        assert "cors_configuration {" in file_map["api_gateway.tf"]
        assert 'provider "aws" {' in file_map["providers.tf"]
        assert 'payload_format_version = "2.0"' in file_map["api_gateway.tf"]
        assert "Terraform-managed secret values may be stored in Terraform state." in file_map["README.generated.md"]
        assert len(res.architecture_resource_mappings) == 4
    finally:
        gs.create_provider = orig_create


def test_coverage_validator_accepts_multi_lambda_serverless_plan(tmp_path) -> None:
    settings = _settings(tmp_path, enabled=True)
    svc = _generator(settings)
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"
    mock_llm.complete = AsyncMock(return_value=json.dumps({"draft_pattern_name": "serverless_http_api_lambda_external_db"}))

    import app.services.generator_service as gs
    orig_create = gs.create_provider
    gs.create_provider = lambda s: mock_llm
    try:
        res = svc.generate(_multi_lambda_arch())
        plan = TerraformResourcePlan.model_validate(res.terraform_resource_plan)
        errors = TerraformResourcePlanCoverageValidator().validate(
            normalize_architecture(_multi_lambda_arch(), "us-east-1"),
            plan,
        )
        assert errors == []
    finally:
        gs.create_provider = orig_create


def test_coverage_findings_are_structured_for_missing_mapping() -> None:
    plan = TerraformResourcePlan.model_validate(json.loads(_plan_json()))
    arch = normalize_architecture(_multi_lambda_arch(), "us-east-1")
    plan.architecture_resource_mappings = [item for item in plan.architecture_resource_mappings if item.architecture_resource_id != "game-backend-lambda"]
    findings = TerraformResourcePlanCoverageValidator().validate(arch, plan)
    assert any(item.code == "MISSING_MAPPING" and item.architecture_resource_id == "game-backend-lambda" for item in findings)


def test_aggregate_architecture_resources_can_map_to_multiple_addresses(tmp_path) -> None:
    settings = _settings(tmp_path, enabled=True)
    svc = _generator(settings)
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"
    mock_llm.complete = AsyncMock(return_value=json.dumps({"draft_pattern_name": "serverless_http_api_lambda_external_db"}))

    import app.services.generator_service as gs
    orig_create = gs.create_provider
    gs.create_provider = lambda s: mock_llm
    try:
        res = svc.generate(
            CanonicalArchitecture.model_validate(
                {
                    **_multi_lambda_arch().model_dump(),
                    "resources": [
                        *_multi_lambda_arch().resources,
                        {"id": "secrets-manager", "provider_type": "aws_secretsmanager_secret", "configuration": {}},
                        {"id": "lambda-execution-role", "provider_type": "aws_iam_role", "configuration": {}},
                        {"id": "cloudwatch-logs", "provider_type": "aws_cloudwatch_log_group", "configuration": {}},
                    ],
                }
            )
        )
        mapping_by_id = {item["architecture_resource_id"]: item for item in res.architecture_resource_mappings}
        assert len(mapping_by_id["secrets-manager"]["terraform_addresses"]) == 2
        assert len(mapping_by_id["lambda-execution-role"]["terraform_addresses"]) == 3
        assert len(mapping_by_id["cloudwatch-logs"]["terraform_addresses"]) == 2
    finally:
        gs.create_provider = orig_create


def test_duplicate_warnings_are_removed_from_response(tmp_path) -> None:
    settings = _settings(tmp_path, enabled=True)
    svc = _generator(settings)
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"
    mock_llm.complete = AsyncMock(return_value=json.dumps({"draft_pattern_name": "serverless_http_api_lambda_external_db"}))

    import app.services.generator_service as gs
    orig_create = gs.create_provider
    gs.create_provider = lambda s: mock_llm
    try:
        res = svc.generate(_multi_lambda_arch())
        assert len(res.warnings) == len(set(res.warnings))
    finally:
        gs.create_provider = orig_create


def test_empty_planned_resources_fail_loudly(tmp_path) -> None:
    settings = _settings(tmp_path, enabled=True)
    svc = _generator(settings)
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"

    import app.services.generator_service as gs
    orig_create = gs.create_provider
    orig_create_plan = svc.llm_planner.create_plan
    gs.create_provider = lambda s: mock_llm
    svc.llm_planner.create_plan = lambda *_args, **_kwargs: (
        TerraformResourcePlan.model_validate(
            {
                "draft_pattern_name": "unsupported_architecture_generic",
                "cloud_provider": "AWS",
                "terraform_version": ">= 1.5.0",
                "required_providers": [{"name": "aws", "source": "hashicorp/aws", "version": "~> 5.0"}],
                "variables": [{"name": "aws_region", "type": "string"}],
                "resources": [],
                "architecture_resource_mappings": [
                    {
                        "architecture_resource_id": "api-gateway",
                        "provider_type": "aws_apigatewayv2_api",
                        "mapping_status": "UNSUPPORTED",
                        "terraform_addresses": [],
                    }
                ],
            }
        ),
        [],
    )
    try:
        res = svc.generate(_unsupported_arch())
        assert res.generation_status == "FAILED"
        assert res.error == "LLM planner returned an empty TerraformResourcePlan"
    finally:
        gs.create_provider = orig_create
        svc.llm_planner.create_plan = orig_create_plan


def test_shell_only_render_fails_loudly(tmp_path) -> None:
    settings = _settings(tmp_path, enabled=True)
    svc = _generator(settings)
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.name = "gemini"
    mock_llm.complete = AsyncMock(return_value=json.dumps({
        "draft_pattern_name": "serverless_http_api_lambda_external_db",
        "required_providers": [{"name": "aws", "source": "hashicorp/aws", "version": "~> 5.0"}],
        "variables": [{"name": "aws_region", "type": "string"}],
        "resources": [],
        "architecture_resource_mappings": [
            {
                "architecture_resource_id": "api-gateway",
                "provider_type": "aws_apigatewayv2_api",
                "mapping_status": "UNSUPPORTED",
                "terraform_addresses": [],
            },
            {
                "architecture_resource_id": "central-backend",
                "provider_type": "aws_lambda_function",
                "mapping_status": "NEEDS_INPUT",
                "terraform_addresses": [],
            },
            {
                "architecture_resource_id": "supabase",
                "provider_type": "external_supabase",
                "mapping_status": "EXTERNAL",
                "terraform_addresses": [],
            },
        ],
        "warnings": [],
    }))

    import app.services.generator_service as gs
    orig_create = gs.create_provider
    orig_render = svc.generic_renderer.render
    gs.create_provider = lambda s: mock_llm
    svc.generic_renderer.render = lambda plan: [
        {"path": "versions.tf", "content": 'terraform {\n  required_version = ">= 1.5.0"\n}\n'},
        {"path": "providers.tf", "content": 'provider "aws" {\n  region = var.aws_region\n}\n'},
        {"path": "README.generated.md", "content": "# README\n"},
    ]
    try:
        res = svc.generate(_unsupported_arch())
        assert res.generation_status == "FAILED"
        assert res.error == "Generic renderer produced only shell files; no infrastructure resources were rendered."
    finally:
        gs.create_provider = orig_create
        svc.generic_renderer.render = orig_render
