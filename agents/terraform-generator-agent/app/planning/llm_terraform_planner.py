from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import logging

from app.llm.base import LLMProvider
from app.reasoning.reasoning_schema import TerraformReasoningResult
from app.services.architecture_normalizer import NormalizedArchitecture
from app.utils.asyncio_utils import run_awaitable

from .terraform_resource_plan_coverage_validator import (
    CoverageFinding,
    TerraformResourcePlanCoverageValidator,
)
from .terraform_resource_plan_schema import TerraformResourcePlan

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Nimbus's Terraform planning assistant.
Generate TerraformResourcePlan JSON only.
Do not generate markdown.
Do not generate Terraform HCL.
Do not generate placeholder files.
Every architecture resource must appear in architecture_resource_mappings.
external_* resources must not be rendered as AWS resources.
Required missing values must become variables.
Secrets must be sensitive variables.
No real secrets. No AWS credentials.
No AdministratorAccess unless explicitly required and warned.
No public database exposure unless explicitly required and warned.
No terraform apply/destroy/import/state/force-unlock commands.
If the architecture cannot be mapped, mark resources UNSUPPORTED or NEEDS_INPUT honestly."""


def _prompt(architecture: NormalizedArchitecture, reasoning: TerraformReasoningResult) -> str:
    provider_types = sorted({r.provider_type for r in architecture.resources})
    payload = {
        "architecture": asdict(architecture) if is_dataclass(architecture) else {},
        "detected_provider_types": provider_types,
        "unsupported_provider_types": sorted({t for t in provider_types if t.startswith("external_")}),
        "cloud_provider": str(getattr(architecture, "provider", "aws")).upper(),
        "environment": "development",
        "deployment_targets": [],
        "known_safety_rules": [
            "Never expose database ports to 0.0.0.0/0",
            "Never emit hardcoded secrets or AWS credentials",
            "Never render external_* resources as AWS resources",
        ],
        "allowed_resource_types": [
            "aws_apigatewayv2_api",
            "aws_apigatewayv2_stage",
            "aws_apigatewayv2_integration",
            "aws_apigatewayv2_route",
            "aws_lambda_function",
            "aws_lambda_permission",
            "aws_iam_role",
            "aws_iam_role_policy",
            "aws_iam_role_policy_attachment",
            "aws_cloudwatch_log_group",
            "aws_secretsmanager_secret",
            "aws_secretsmanager_secret_version",
            "aws_caller_identity",
        ],
        "instructions": "Generate TerraformResourcePlan JSON only. Do not generate .tf files.",
        "reasoning_summary": reasoning.terraform_strategy_summary,
        "unsupported_reasons": reasoning.unsupported_reasons,
    }
    return SYSTEM_PROMPT + "\n\n" + json.dumps(payload, indent=2)


def _repair_prompt(
    architecture: NormalizedArchitecture,
    reasoning: TerraformReasoningResult,
    plan: TerraformResourcePlan,
    errors: list[str],
) -> str:
    payload = {
        "instructions": "Return corrected TerraformResourcePlan JSON only. Fix all coverage issues. Do not output Terraform HCL or markdown.",
        "architecture": asdict(architecture) if is_dataclass(architecture) else {},
        "reasoning_summary": reasoning.terraform_strategy_summary,
        "previous_plan": plan.model_dump(mode="json"),
        "coverage_errors": errors,
    }
    return SYSTEM_PROMPT + "\n\n" + json.dumps(payload, indent=2)


class LLMTerraformPlanner:
    def __init__(self) -> None:
        self.coverage_validator = TerraformResourcePlanCoverageValidator()

    def create_plan(
        self,
        architecture: NormalizedArchitecture,
        reasoning: TerraformReasoningResult,
        llm: LLMProvider,
    ) -> tuple[TerraformResourcePlan, list[CoverageFinding]]:
        raw = run_awaitable(llm.complete(_prompt(architecture, reasoning)))
        logger.info(
            "llm_response_received=%s raw_response_length=%s",
            True,
            len(raw or ""),
        )
        plan = self._parse_and_normalize(raw, architecture)
        logger.info(
            "planned_resource_count=%s planned_variable_count=%s architecture_resource_mapping_count=%s missing_inputs=%s warnings=%s",
            len(plan.resources),
            len(plan.variables),
            len(plan.architecture_resource_mappings),
            plan.missing_inputs,
            plan.warnings,
        )
        errors = self.coverage_validator.validate(architecture, plan)
        if not errors:
            return plan, []

        repaired_raw = run_awaitable(llm.complete(_repair_prompt(architecture, reasoning, plan, errors)))
        logger.info(
            "llm_response_received=%s raw_response_length=%s repair_attempt=%s",
            True,
            len(repaired_raw or ""),
            1,
        )
        repaired_plan = self._parse_and_normalize(repaired_raw, architecture)
        logger.info(
            "planned_resource_count=%s planned_variable_count=%s architecture_resource_mapping_count=%s missing_inputs=%s warnings=%s repair_attempt=%s",
            len(repaired_plan.resources),
            len(repaired_plan.variables),
            len(repaired_plan.architecture_resource_mappings),
            repaired_plan.missing_inputs,
            repaired_plan.warnings,
            1,
        )
        repaired_errors = self.coverage_validator.validate(architecture, repaired_plan)
        if repaired_errors:
            repaired_plan.warnings.append("Coverage validator found remaining gaps after one repair retry.")
            repaired_plan.validation_assertions.extend([f.expected for f in repaired_errors])
        return repaired_plan, repaired_errors

    def _parse_and_normalize(self, raw: str, architecture: NormalizedArchitecture) -> TerraformResourcePlan:
        text = _extract_json_text(raw)
        logger.info("json_extraction_succeeded=%s extracted_response_length=%s", bool(text), len(text or ""))
        try:
            data = json.loads(text)
        except Exception as exc:
            logger.warning("Planner JSON parse failed: %s", type(exc).__name__)
            logger.warning("planner_parse_error=%s", f"{type(exc).__name__}: {exc}")
            raise ValueError(f"Planner returned invalid JSON: {type(exc).__name__}") from exc
        data = _normalize_plan_data(data, architecture)
        return TerraformResourcePlan.model_validate(data)


def _extract_json_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _normalize_plan_data(data: dict, architecture: NormalizedArchitecture) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Planner returned non-object JSON")

    provider_types = {r.provider_type for r in architecture.resources}
    if not data.get("draft_pattern_name"):
        if {"aws_apigatewayv2_api", "aws_lambda_function"} & provider_types and "external_supabase" in provider_types:
            data["draft_pattern_name"] = "serverless_http_api_lambda_external_db"
        elif {"aws_apigatewayv2_api", "aws_lambda_function"} & provider_types:
            data["draft_pattern_name"] = "serverless_http_api_lambda"
        else:
            data["draft_pattern_name"] = "unsupported_architecture_generic"

    data.setdefault("plan_version", "1.0.0")
    data.setdefault("cloud_provider", str(getattr(architecture, "provider", "AWS")).upper())
    data.setdefault("terraform_version", ">= 1.5.0")
    if str(data.get("terraform_version")).strip() == "1.5.0":
        data["terraform_version"] = ">= 1.5.0"
    if isinstance(data.get("required_providers"), dict):
        data["required_providers"] = [{"name": name, **spec} for name, spec in data["required_providers"].items() if isinstance(spec, dict)]
    data.setdefault("required_providers", [{"name": "aws", "source": "hashicorp/aws", "version": "~> 5.0"}])
    data.setdefault("deployment_targets", [])

    if isinstance(data.get("variables"), dict):
        data["variables"] = [{"name": name, **(spec if isinstance(spec, dict) else {"default": spec, "type": "string"})} for name, spec in data["variables"].items()]
    if isinstance(data.get("locals"), dict):
        data["locals"] = [{"name": name, "value": _coerce_hcl_value(value)} for name, value in data["locals"].items()]
    if isinstance(data.get("outputs"), dict):
        data["outputs"] = [{"name": name, **(spec if isinstance(spec, dict) else {"value": spec})} for name, spec in data["outputs"].items()]

    for key in (
        "variables", "locals", "data_sources", "resources", "outputs", "external_dependencies",
        "derived_resources", "missing_inputs", "assumptions", "warnings", "runtime_risks",
        "validation_assertions",
    ):
        data.setdefault(key, [])

    for variable in data["variables"]:
        if isinstance(variable, dict):
            variable.setdefault("type", "string")
            if variable.get("default") is not None:
                variable["default"] = _coerce_hcl_value(variable["default"])

    for output in data["outputs"]:
        if isinstance(output, dict) and "value" in output:
            output["value"] = _coerce_hcl_value(output["value"])

    for collection in ("resources", "data_sources"):
        normalized = []
        for item in data.get(collection, []):
            if not isinstance(item, dict):
                continue
            fixed = dict(item)
            fixed.setdefault("terraform_type", fixed.get("resource_type") or fixed.get("type"))
            fixed.setdefault("name", fixed.get("resource_name") or fixed.get("logical_name") or fixed.get("label"))
            if "architecture_resource_id" not in fixed and "architecture_id" in fixed:
                fixed["architecture_resource_id"] = fixed["architecture_id"]
            fixed["file"] = _default_file_for_resource_type(str(fixed.get("terraform_type", "")), str(fixed.get("file", "")))
            if isinstance(fixed.get("body"), dict):
                fixed["body"] = {k: _coerce_hcl_value(v) for k, v in fixed["body"].items()}
            else:
                fixed["body"] = {}
            if (
                fixed.get("terraform_type") == "aws_apigatewayv2_integration"
                and getattr(fixed["body"].get("integration_type"), "value", None) == "AWS_PROXY"
                and "payload_format_version" not in fixed["body"]
            ):
                fixed["body"]["payload_format_version"] = {"kind": "literal", "value": "2.0"}
            normalized.append(fixed)
        data[collection] = normalized

    mappings = data.get("architecture_resource_mappings")
    if not isinstance(mappings, list) or not mappings:
        mappings = []
        for resource in architecture.resources:
            mappings.append({
                "architecture_resource_id": resource.id,
                "provider_type": resource.provider_type,
                "mapping_status": "EXTERNAL" if resource.provider_type.startswith("external_") else "UNSUPPORTED",
                "terraform_addresses": [],
                "notes": "Auto-filled because planner omitted mapping coverage.",
            })
    else:
        fixed_mappings = []
        for item in mappings:
            if not isinstance(item, dict):
                continue
            fixed = dict(item)
            if "architecture_resource_id" not in fixed and "architecture_id" in fixed:
                fixed["architecture_resource_id"] = fixed["architecture_id"]
            fixed.setdefault("provider_type", fixed.get("terraform_type") or "unknown")
            fixed.setdefault("mapping_status", "EXTERNAL" if str(fixed["provider_type"]).startswith("external_") else "RENDERED")
            if "terraform_addresses" not in fixed:
                tf_type = fixed.get("terraform_type")
                tf_name = fixed.get("name")
                fixed["terraform_addresses"] = [f"{tf_type}.{tf_name}"] if tf_type and tf_name else []
            fixed.setdefault("notes", fixed.get("reason", ""))
            fixed_mappings.append(fixed)
        mappings = fixed_mappings
    data["architecture_resource_mappings"] = mappings

    if data.get("draft_pattern_name") == "serverless_http_api_lambda_external_db":
        data = _ensure_serverless_supabase_coverage(data, architecture)

    return data


def _coerce_hcl_value(value):
    if isinstance(value, dict):
        if "kind" in value:
            return value
        if "type" in value and "body" in value:
            return {"kind": "block", "type": value["type"], "labels": value.get("labels", []), "body": {k: _coerce_hcl_value(v) for k, v in dict(value.get("body", {})).items()}}
        return {"kind": "object", "items": {k: _coerce_hcl_value(v) for k, v in value.items()}}
    if isinstance(value, list):
        return {"kind": "list", "items": [_coerce_hcl_value(v) for v in value]}
    if isinstance(value, (bool, int, float)) or value is None:
        return {"kind": "literal", "value": value}
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("${") and stripped.endswith("}"):
            return {"kind": "expr", "value": stripped[2:-1]}
        if any(stripped.startswith(prefix) for prefix in ("var.", "aws_", "data.", "local.", "jsonencode(", "format(", "join(", "concat(", "toset(", "tomap(", "\"integrations/${")):
            return {"kind": "expr", "value": stripped}
        return {"kind": "literal", "value": value}
    return {"kind": "literal", "value": str(value)}


def _default_file_for_resource_type(terraform_type: str, requested_file: str) -> str:
    if requested_file:
        return requested_file
    if terraform_type.startswith("aws_lambda") or terraform_type == "aws_lambda_permission":
        return "lambda.tf"
    if terraform_type.startswith("aws_apigatewayv2"):
        return "api_gateway.tf"
    if terraform_type.startswith("aws_secretsmanager"):
        return "secrets.tf"
    if terraform_type.startswith("aws_iam"):
        return "iam.tf"
    if terraform_type.startswith("aws_cloudwatch"):
        return "observability.tf"
    return "compute.tf"


def _ensure_serverless_supabase_coverage(data: dict, architecture: NormalizedArchitecture) -> dict:
    api = next((r for r in architecture.resources if r.provider_type == "aws_apigatewayv2_api"), None)
    lambdas = [r for r in architecture.resources if r.provider_type == "aws_lambda_function"]
    supabase = next((r for r in architecture.resources if r.provider_type == "external_supabase"), None)
    if api is None or not lambdas:
        return data

    api_id = api.id
    supabase_id = supabase.id if supabase else "external-supabase"

    resources = []
    resources.extend([
        {
            "terraform_type": "aws_iam_role",
            "name": "lambda_execution_role",
            "file": "iam.tf",
            "body": {
                "name": {"kind": "expr", "value": 'format("%s-%s-lambda-role", var.project_name, var.environment)'},
                "assume_role_policy": {"kind": "expr", "value": 'jsonencode({Version = "2012-10-17", Statement = [{Effect = "Allow", Principal = {Service = "lambda.amazonaws.com"}, Action = "sts:AssumeRole"}]})'},
            },
        },
        {
            "terraform_type": "aws_iam_role_policy_attachment",
            "name": "lambda_basic_execution",
            "file": "iam.tf",
            "body": {
                "role": {"kind": "expr", "value": "aws_iam_role.lambda_execution_role.name"},
                "policy_arn": {"kind": "literal", "value": "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"},
            },
        },
        {
            "terraform_type": "aws_iam_role_policy",
            "name": "lambda_secrets_access",
            "file": "iam.tf",
            "body": {
                "name": {"kind": "expr", "value": 'format("%s-secrets-access", local.name_prefix)'},
                "role": {"kind": "expr", "value": "aws_iam_role.lambda_execution_role.id"},
                "policy": {"kind": "expr", "value": 'jsonencode({Version = "2012-10-17", Statement = [{Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.supabase.arn}]})'},
            },
        },
        {
            "terraform_type": "aws_secretsmanager_secret",
            "name": "supabase",
            "file": "secrets.tf",
            "architecture_resource_id": supabase_id,
            "body": {"name": {"kind": "expr", "value": 'format("%s-supabase", local.name_prefix)'}},
        },
        {
            "terraform_type": "aws_secretsmanager_secret_version",
            "name": "supabase",
            "file": "secrets.tf",
            "body": {
                "secret_id": {"kind": "expr", "value": "aws_secretsmanager_secret.supabase.id"},
                "secret_string": {"kind": "expr", "value": 'jsonencode({SUPABASE_URL = var.supabase_url, SUPABASE_SERVICE_ROLE_KEY = var.supabase_service_role_key})'},
            },
        },
    ])

    api_body = {
        "name": {"kind": "expr", "value": 'format("%s-http-api", local.name_prefix)'},
        "protocol_type": {"kind": "literal", "value": "HTTP"},
    }
    cors = api.configuration.get("cors_configuration")
    if isinstance(cors, dict) and cors:
        api_body["cors_configuration"] = {
            "kind": "block",
            "type": "cors_configuration",
            "body": {k: _coerce_hcl_value(v) for k, v in cors.items()},
        }
    resources.extend([
        {
            "terraform_type": "aws_apigatewayv2_api",
            "name": "http_api",
            "file": "api_gateway.tf",
            "architecture_resource_id": api_id,
            "body": api_body,
        },
        {
            "terraform_type": "aws_apigatewayv2_stage",
            "name": "default",
            "file": "api_gateway.tf",
            "body": {
                "api_id": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.id"},
                "name": {"kind": "literal", "value": "$default"},
                "auto_deploy": {"kind": "literal", "value": True},
            },
        },
    ])

    variables = [
        {"name": "aws_region", "type": "string", "description": "AWS region.", "default": {"kind": "literal", "value": architecture.region}, "required": True},
        {"name": "project_name", "type": "string", "description": "Project name.", "required": True},
        {"name": "environment", "type": "string", "description": "Environment.", "default": {"kind": "literal", "value": "development"}, "required": True},
        {"name": "supabase_url", "type": "string", "description": "Supabase URL.", "required": True},
        {"name": "supabase_service_role_key", "type": "string", "description": "Supabase service role key.", "required": True, "sensitive": True},
    ]
    mappings = [
        {"architecture_resource_id": api_id, "provider_type": "aws_apigatewayv2_api", "mapping_status": "RENDERED", "terraform_addresses": ["aws_apigatewayv2_api.http_api"], "notes": "Rendered as HTTP API plus stage and route wiring."},
        {"architecture_resource_id": supabase_id, "provider_type": "external_supabase", "mapping_status": "EXTERNAL", "terraform_addresses": [], "notes": "Handled through variables and Secrets Manager only."},
    ]
    derived = [{"terraform_type": "aws_apigatewayv2_stage", "name": "default", "reason": "Expose the HTTP API."}]
    missing_inputs = ["supabase_url", "supabase_service_role_key"]

    for lambda_resource in lambdas:
        label = _safe_label(lambda_resource.name)
        package_var = f"{label}_package_path"
        handler_var = f"{label}_handler"
        variables.extend([
            {"name": package_var, "type": "string", "description": f"Path to packaged ZIP for {label}.", "required": True},
            {"name": handler_var, "type": "string", "description": f"Handler for {label}.", "default": {"kind": "literal", "value": str(lambda_resource.configuration.get("handler", "index.handler"))}, "required": True},
        ])
        resources.extend([
            {
                "terraform_type": "aws_cloudwatch_log_group",
                "name": label,
                "file": "observability.tf",
                "architecture_resource_id": lambda_resource.id,
                "body": {
                    "name": {"kind": "expr", "value": f'format("/aws/lambda/%s-{label}", local.name_prefix)'},
                    "retention_in_days": {"kind": "literal", "value": 7},
                },
            },
            {
                "terraform_type": "aws_lambda_function",
                "name": label,
                "file": "lambda.tf",
                "architecture_resource_id": lambda_resource.id,
                "body": {
                    "function_name": {"kind": "expr", "value": f'format("%s-{label}", local.name_prefix)'},
                    "role": {"kind": "expr", "value": "aws_iam_role.lambda_execution_role.arn"},
                    "runtime": {"kind": "literal", "value": str(lambda_resource.configuration.get("runtime", "nodejs20.x"))},
                    "handler": {"kind": "expr", "value": f"var.{handler_var}"},
                    "filename": {"kind": "expr", "value": f"var.{package_var}"},
                    "memory_size": {"kind": "literal", "value": int(lambda_resource.configuration.get("memory_size", 512))},
                    "timeout": {"kind": "literal", "value": int(lambda_resource.configuration.get("timeout", 29))},
                    "source_code_hash": {"kind": "expr", "value": f"filebase64sha256(var.{package_var})"},
                    "environment": {
                        "kind": "block",
                        "type": "environment",
                        "body": {
                            "variables": {
                                "kind": "object",
                                "items": {
                                    "ENVIRONMENT": {"kind": "expr", "value": "var.environment"},
                                    "SUPABASE_SECRET_ARN": {"kind": "expr", "value": "aws_secretsmanager_secret.supabase.arn"},
                                },
                            }
                        },
                    },
                },
                "depends_on": [f"aws_cloudwatch_log_group.{label}"],
            },
        ])
        mappings.append({"architecture_resource_id": lambda_resource.id, "provider_type": "aws_lambda_function", "mapping_status": "RENDERED", "terraform_addresses": [f"aws_lambda_function.{label}"], "notes": "Rendered as Lambda, logs, IAM, and API Gateway wiring."})
        missing_inputs.append(package_var)

    for relation in architecture.relationships:
        if relation.get("source_id") != api_id:
            continue
        target_id = relation.get("target_id")
        route_key = _route_key_from_label(str(relation.get("label", "")))
        target_resource = architecture.resource(target_id) if target_id else None
        if not target_resource or target_resource.provider_type != "aws_lambda_function" or not route_key:
            continue
        label = _safe_label(target_resource.name)
        resources.extend([
                {
                    "terraform_type": "aws_apigatewayv2_integration",
                    "name": f"{label}_integration",
                    "file": "api_gateway.tf",
                    "body": {
                        "api_id": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.id"},
                        "integration_type": {"kind": "literal", "value": "AWS_PROXY"},
                        "integration_uri": {"kind": "expr", "value": f"aws_lambda_function.{label}.invoke_arn"},
                        "integration_method": {"kind": "literal", "value": "POST"},
                        "payload_format_version": {"kind": "literal", "value": "2.0"},
                    },
                },
            {
                "terraform_type": "aws_apigatewayv2_route",
                "name": f"{label}_route",
                "file": "api_gateway.tf",
                "body": {
                    "api_id": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.id"},
                    "route_key": {"kind": "literal", "value": route_key},
                    "target": {"kind": "expr", "value": f'"integrations/${{aws_apigatewayv2_integration.{label}_integration.id}}"'},
                },
            },
            {
                "terraform_type": "aws_lambda_permission",
                "name": f"allow_api_gateway_{label}",
                "file": "lambda.tf",
                "body": {
                    "statement_id": {"kind": "literal", "value": f"AllowExecutionFromApiGateway{label.title().replace('_', '')}"},
                    "action": {"kind": "literal", "value": "lambda:InvokeFunction"},
                    "function_name": {"kind": "expr", "value": f"aws_lambda_function.{label}.function_name"},
                    "principal": {"kind": "literal", "value": "apigateway.amazonaws.com"},
                    "source_arn": {"kind": "expr", "value": 'format("%s/*/*", aws_apigatewayv2_api.http_api.execution_arn)'},
                },
            },
        ])
        derived.extend([
            {"terraform_type": "aws_apigatewayv2_integration", "name": f"{label}_integration", "reason": f"Connect API Gateway to Lambda {label}."},
            {"terraform_type": "aws_apigatewayv2_route", "name": f"{label}_route", "reason": f"Route {route_key} to Lambda {label}."},
            {"terraform_type": "aws_lambda_permission", "name": f"allow_api_gateway_{label}", "reason": f"Allow API Gateway to invoke Lambda {label}."},
        ])

    data["required_providers"] = [{"name": "aws", "source": "hashicorp/aws", "version": "~> 5.0"}]
    data["variables"] = variables
    data["locals"] = [{"name": "name_prefix", "value": {"kind": "expr", "value": 'format("%s-%s", var.project_name, var.environment)'}}]
    data["data_sources"] = [{"terraform_type": "aws_caller_identity", "name": "current", "file": "providers.tf", "body": {}}]
    data["resources"] = resources
    data["outputs"] = [
        {"name": "api_endpoint", "description": "HTTP API endpoint.", "value": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.api_endpoint"}},
        {"name": "supabase_secret_arn", "description": "Supabase secret ARN.", "value": {"kind": "expr", "value": "aws_secretsmanager_secret.supabase.arn"}},
    ]
    data["architecture_resource_mappings"] = mappings
    for resource in architecture.resources:
        if resource.provider_type == "aws_secretsmanager_secret":
            mappings.append({
                "architecture_resource_id": resource.id,
                "provider_type": resource.provider_type,
                "mapping_status": "RENDERED",
                "terraform_addresses": [
                    "aws_secretsmanager_secret.supabase",
                    "aws_secretsmanager_secret_version.supabase",
                ],
                "notes": "Aggregate mapping to generated secret resources.",
            })
        elif resource.provider_type == "aws_iam_role":
            mappings.append({
                "architecture_resource_id": resource.id,
                "provider_type": resource.provider_type,
                "mapping_status": "RENDERED",
                "terraform_addresses": [
                    "aws_iam_role.lambda_execution_role",
                    "aws_iam_role_policy.lambda_secrets_access",
                    "aws_iam_role_policy_attachment.lambda_basic_execution",
                ],
                "notes": "Aggregate mapping to generated IAM role and attached policies.",
            })
        elif resource.provider_type == "aws_cloudwatch_log_group":
            mappings.append({
                "architecture_resource_id": resource.id,
                "provider_type": resource.provider_type,
                "mapping_status": "RENDERED",
                "terraform_addresses": [
                    *(f"aws_cloudwatch_log_group.{_safe_label(item.name)}" for item in lambdas),
                ],
                "notes": "Aggregate mapping to generated Lambda log groups.",
            })
    data["external_dependencies"] = [{"architecture_resource_id": supabase_id, "provider_type": "external_supabase", "name": "Supabase", "handling": "variables_and_secret_reference", "notes": "Nimbus does not provision Supabase itself."}]
    data["derived_resources"] = derived
    data["missing_inputs"] = missing_inputs
    data["warnings"] = [*list(data.get("warnings", [])), "Planner output was enriched with Nimbus deterministic serverless defaults for API Gateway + Lambda + external Supabase."]
    data["validation_assertions"] = list({*data.get("validation_assertions", []), "Lambda package paths must point to built ZIP artifacts.", "Supabase remains external and must not be provisioned by Terraform."})
    return data


def _route_key_from_label(label: str) -> str | None:
    if "/api/central/*" in label:
        return "ANY /api/central/{proxy+}"
    if "/api/games/*" in label:
        return "ANY /api/games/{proxy+}"
    return None


def _safe_label(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return text or "app"
