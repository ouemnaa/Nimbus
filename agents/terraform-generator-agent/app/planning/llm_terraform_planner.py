from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import logging

from app.llm.base import LLMProvider
from app.reasoning.reasoning_schema import TerraformReasoningResult
from app.services.architecture_normalizer import NormalizedArchitecture
from app.utils.asyncio_utils import run_awaitable

from .aws_capability_catalog import AwsCapabilityCatalog
from .capability_extractor import InfrastructureCapabilityExtractor
from .infrastructure_capability_plan import InfrastructureCapabilityPlan
from .terraform_resource_plan_coverage_validator import (
    CoverageFinding,
    TerraformResourcePlanCoverageValidator,
)
from .terraform_resource_plan_schema import TerraformResourcePlan

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Nimbus's Terraform planning assistant.
Return strict TerraformResourcePlan JSON only.
No markdown.
No code fences.
No Terraform HCL text output.
No multiline prose inside JSON strings.
Do not stop at architecture_resource_mappings.
You must produce concrete Terraform resources when the capability plan is implementable.
Every non-external architecture resource must map to concrete Terraform addresses.
external_* resources must not be rendered as AWS resources.
Required missing values must become variables.
Secrets must be sensitive variables.
No real secrets. No AWS credentials.
No AdministratorAccess unless explicitly required and warned.
No public database exposure unless explicitly required and warned.
No terraform apply/destroy/import/state/force-unlock commands."""


def _prompt(
    architecture: NormalizedArchitecture,
    reasoning: TerraformReasoningResult,
    capability_plan: InfrastructureCapabilityPlan,
    catalog: AwsCapabilityCatalog,
) -> str:
    provider_types = sorted({r.provider_type for r in architecture.resources})
    payload = {
        "architecture": asdict(architecture) if is_dataclass(architecture) else {},
        "infrastructure_capability_plan": capability_plan.model_dump(mode="json"),
        "aws_capability_catalog": catalog.prompt_payload(),
        "detected_provider_types": provider_types,
        "unsupported_provider_types": sorted(
            {
                t for t in provider_types
                if t.startswith("external_") or not t.startswith("aws_")
            }
        ),
        "cloud_provider": str(getattr(architecture, "provider", "aws")).upper(),
        "environment": "development",
        "known_safety_rules": [
            "Never expose database ports to 0.0.0.0/0",
            "Never emit hardcoded secrets or AWS credentials",
            "Never render external_* resources as AWS resources",
            "A plan with zero concrete resources is invalid",
            "A plan with only provider/version shell files is invalid",
        ],
        "planner_stages": [
            "Infer infrastructure capabilities from the canonical architecture",
            "Choose AWS services for each capability using the AWS capability catalog",
            "Expand selected services into concrete Terraform resources and data sources",
            "Produce architecture_resource_mappings, external_dependencies, missing_inputs, warnings, and validation_assertions",
        ],
        "instructions": "Generate TerraformResourcePlan JSON only. Produce concrete Terraform resources, not .tf files.",
        "reasoning_summary": reasoning.terraform_strategy_summary,
        "unsupported_reasons": reasoning.unsupported_reasons,
    }
    return SYSTEM_PROMPT + "\n\n" + json.dumps(payload, indent=2)


def _repair_prompt(
    architecture: NormalizedArchitecture,
    reasoning: TerraformReasoningResult,
    capability_plan: InfrastructureCapabilityPlan,
    plan: TerraformResourcePlan,
    errors: list[CoverageFinding],
    catalog: AwsCapabilityCatalog,
) -> str:
    payload = {
        "instructions": "Return corrected TerraformResourcePlan JSON only. Fix all coverage findings and keep strict JSON.",
        "architecture": asdict(architecture) if is_dataclass(architecture) else {},
        "infrastructure_capability_plan": capability_plan.model_dump(mode="json"),
        "aws_capability_catalog": catalog.prompt_payload(),
        "reasoning_summary": reasoning.terraform_strategy_summary,
        "previous_plan": plan.model_dump(mode="json"),
        "coverage_findings": [item.model_dump(mode="json") for item in errors],
    }
    return SYSTEM_PROMPT + "\n\n" + json.dumps(payload, indent=2)


class LLMTerraformPlanner:
    def __init__(self) -> None:
        self.coverage_validator = TerraformResourcePlanCoverageValidator()
        self.catalog = AwsCapabilityCatalog()
        self.capability_extractor = InfrastructureCapabilityExtractor(self.catalog)

    def create_plan(
        self,
        architecture: NormalizedArchitecture,
        reasoning: TerraformReasoningResult,
        llm: LLMProvider,
    ) -> tuple[TerraformResourcePlan, list[CoverageFinding]]:
        capability_plan = self.capability_extractor.extract(architecture)
        raw = run_awaitable(llm.complete(_prompt(architecture, reasoning, capability_plan, self.catalog)))
        logger.info("llm_response_received=%s raw_response_length=%s", True, len(raw or ""))
        plan = self._parse_and_normalize(raw, architecture, capability_plan)
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

        repaired_raw = run_awaitable(
            llm.complete(_repair_prompt(architecture, reasoning, capability_plan, plan, errors, self.catalog))
        )
        logger.info(
            "llm_response_received=%s raw_response_length=%s repair_attempt=%s",
            True,
            len(repaired_raw or ""),
            1,
        )
        repaired_plan = self._parse_and_normalize(repaired_raw, architecture, capability_plan)
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
            repaired_plan.validation_assertions.extend([item.expected for item in repaired_errors])
        return repaired_plan, repaired_errors

    def _parse_and_normalize(
        self,
        raw: str,
        architecture: NormalizedArchitecture,
        capability_plan: InfrastructureCapabilityPlan,
    ) -> TerraformResourcePlan:
        text = _extract_json_text(raw)
        logger.info("json_extraction_succeeded=%s extracted_response_length=%s", bool(text), len(text or ""))
        try:
            data = json.loads(text)
        except Exception as exc:
            logger.warning("Planner JSON parse failed: %s", type(exc).__name__)
            logger.warning("planner_parse_error=%s", f"{type(exc).__name__}: {exc}")
            raise ValueError(f"Planner returned invalid JSON: {type(exc).__name__}") from exc
        data = _normalize_plan_data(data, architecture, capability_plan, self.catalog)
        return TerraformResourcePlan.model_validate(data)


def _extract_json_text(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:])
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _normalize_plan_data(
    data: dict,
    architecture: NormalizedArchitecture,
    capability_plan: InfrastructureCapabilityPlan,
    catalog: AwsCapabilityCatalog,
) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Planner returned non-object JSON")

    data.setdefault("plan_version", "1.0.0")
    data.setdefault("cloud_provider", str(getattr(architecture, "provider", "AWS")).upper())
    data.setdefault("terraform_version", ">= 1.5.0")
    if str(data.get("terraform_version")).strip() == "1.5.0":
        data["terraform_version"] = ">= 1.5.0"

    if not data.get("draft_pattern_name"):
        capability_types = {item.capability_type for item in capability_plan.capabilities}
        if {"SERVERLESS_COMPUTE", "PUBLIC_HTTP_ENTRYPOINT"} <= capability_types:
            data["draft_pattern_name"] = "capability_planned_serverless_http"
        elif "CONTAINER_COMPUTE" in capability_types:
            data["draft_pattern_name"] = "capability_planned_container_platform"
        else:
            data["draft_pattern_name"] = "capability_planned_generic_architecture"

    if isinstance(data.get("required_providers"), dict):
        data["required_providers"] = [
            {"name": name, **spec}
            for name, spec in data["required_providers"].items()
            if isinstance(spec, dict)
        ]
    data.setdefault("required_providers", [{"name": "aws", "source": "hashicorp/aws", "version": "~> 5.0"}])
    data["infrastructure_capability_plan"] = _normalize_capability_plan_data(
        data.get("infrastructure_capability_plan"),
        capability_plan,
    ).model_dump(mode="json")
    data.setdefault("deployment_targets", [])

    if isinstance(data.get("variables"), dict):
        data["variables"] = [
            {"name": name, **(spec if isinstance(spec, dict) else {"default": spec, "type": "string"})}
            for name, spec in data["variables"].items()
        ]
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
        normalized: list[dict] = []
        for item in data.get(collection, []):
            if not isinstance(item, dict):
                continue
            fixed = dict(item)
            fixed.setdefault("terraform_type", fixed.get("resource_type") or fixed.get("type"))
            fixed.setdefault("name", fixed.get("resource_name") or fixed.get("logical_name") or fixed.get("label"))
            if "architecture_resource_id" not in fixed and "architecture_id" in fixed:
                fixed["architecture_resource_id"] = fixed["architecture_id"]
            fixed["file"] = _default_file_for_resource_type(
                str(fixed.get("terraform_type", "")),
                str(fixed.get("file", "")),
            )
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
            fixed.setdefault(
                "mapping_status",
                "EXTERNAL" if str(fixed["provider_type"]).startswith("external_") else "RENDERED",
            )
            if "terraform_addresses" not in fixed:
                tf_type = fixed.get("terraform_type")
                tf_name = fixed.get("name")
                fixed["terraform_addresses"] = [f"{tf_type}.{tf_name}"] if tf_type and tf_name else []
            fixed.setdefault("notes", fixed.get("reason", ""))
            fixed_mappings.append(fixed)
        mappings = fixed_mappings
    data["architecture_resource_mappings"] = mappings

    data = _ensure_capability_coverage(data, architecture, capability_plan, catalog)
    data["warnings"] = _dedupe_strings(list(data.get("warnings", [])))
    data["missing_inputs"] = _dedupe_strings(list(data.get("missing_inputs", [])))
    data["validation_assertions"] = _dedupe_strings(list(data.get("validation_assertions", [])))
    return data


def _normalize_capability_plan_data(
    raw_plan: dict | None,
    fallback_plan: InfrastructureCapabilityPlan,
) -> InfrastructureCapabilityPlan:
    if not isinstance(raw_plan, dict):
        return fallback_plan
    try:
        return InfrastructureCapabilityPlan.model_validate(raw_plan)
    except Exception:
        return fallback_plan


def _coerce_hcl_value(value):
    if isinstance(value, dict):
        if "kind" in value:
            return value
        if "type" in value and "body" in value:
            return {
                "kind": "block",
                "type": value["type"],
                "labels": value.get("labels", []),
                "body": {k: _coerce_hcl_value(v) for k, v in dict(value.get("body", {})).items()},
            }
        return {"kind": "object", "items": {k: _coerce_hcl_value(v) for k, v in value.items()}}
    if isinstance(value, list):
        return {"kind": "list", "items": [_coerce_hcl_value(v) for v in value]}
    if isinstance(value, (bool, int, float)) or value is None:
        return {"kind": "literal", "value": value}
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("${") and stripped.endswith("}"):
            return {"kind": "expr", "value": stripped[2:-1]}
        if any(
            stripped.startswith(prefix)
            for prefix in (
                "var.", "aws_", "data.", "local.", "jsonencode(", "format(", "join(", "concat(",
                "toset(", "tomap(", "filebase64sha256(", "\"integrations/${",
            )
        ):
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
    if terraform_type.startswith("aws_s3"):
        return "storage.tf"
    if terraform_type.startswith("aws_sqs") or terraform_type.startswith("aws_dynamodb"):
        return "compute.tf"
    return "compute.tf"


def _ensure_capability_coverage(
    data: dict,
    architecture: NormalizedArchitecture,
    capability_plan: InfrastructureCapabilityPlan,
    catalog: AwsCapabilityCatalog,
) -> dict:
    resources: list[dict] = list(data.get("resources", []))
    data_sources: list[dict] = list(data.get("data_sources", []))
    variables: list[dict] = list(data.get("variables", []))
    locals_list: list[dict] = list(data.get("locals", []))
    outputs: list[dict] = list(data.get("outputs", []))
    mappings: list[dict] = list(data.get("architecture_resource_mappings", []))
    external_dependencies: list[dict] = list(data.get("external_dependencies", []))
    derived_resources: list[dict] = list(data.get("derived_resources", []))
    warnings: list[str] = list(data.get("warnings", []))
    missing_inputs: list[str] = list(data.get("missing_inputs", []))
    validation_assertions: list[str] = list(data.get("validation_assertions", []))

    def resource_address(item: dict) -> str:
        return f"{item['terraform_type']}.{item['name']}"

    def has_resource(address: str) -> bool:
        return any(resource_address(item) == address for item in resources)

    def add_resource(item: dict) -> None:
        if not has_resource(resource_address(item)):
            resources.append(item)

    def add_data_source(item: dict) -> None:
        address = f"{item['terraform_type']}.{item['name']}"
        if not any(f"{entry['terraform_type']}.{entry['name']}" == address for entry in data_sources):
            data_sources.append(item)

    def ensure_variable(name: str, **spec) -> None:
        if any(item.get("name") == name for item in variables):
            return
        variables.append({"name": name, **spec})

    def ensure_local(name: str, value: dict) -> None:
        if any(item.get("name") == name for item in locals_list):
            return
        locals_list.append({"name": name, "value": value})

    def ensure_output(name: str, **spec) -> None:
        if any(item.get("name") == name for item in outputs):
            return
        outputs.append({"name": name, **spec})

    def ensure_mapping(
        architecture_resource_id: str,
        provider_type: str,
        mapping_status: str,
        terraform_addresses: list[str],
        notes: str,
    ) -> None:
        existing = next((item for item in mappings if item.get("architecture_resource_id") == architecture_resource_id), None)
        if existing is None:
            mappings.append({
                "architecture_resource_id": architecture_resource_id,
                "provider_type": provider_type,
                "mapping_status": mapping_status,
                "terraform_addresses": list(terraform_addresses),
                "notes": notes,
            })
            return
        existing["provider_type"] = existing.get("provider_type") or provider_type
        existing["mapping_status"] = mapping_status
        existing["terraform_addresses"] = _dedupe_strings([*existing.get("terraform_addresses", []), *terraform_addresses])
        existing["notes"] = existing.get("notes") or notes

    def ensure_external_dependency(resource_id: str, provider_type: str, name: str, handling: str, notes: str) -> None:
        if any(item.get("architecture_resource_id") == resource_id for item in external_dependencies):
            return
        external_dependencies.append({
            "architecture_resource_id": resource_id,
            "provider_type": provider_type,
            "name": name,
            "handling": handling,
            "notes": notes,
        })

    def derive(tf_type: str, name: str, reason: str, file: str | None = None) -> None:
        address = f"{tf_type}.{name}"
        if any(item.get("terraform_type") == tf_type and item.get("name") == name for item in derived_resources):
            return
        item = {"terraform_type": tf_type, "name": name, "reason": reason}
        if file:
            item["file"] = file
        derived_resources.append(item)

    ensure_variable(
        "aws_region",
        type="string",
        description="AWS region.",
        default={"kind": "literal", "value": architecture.region},
        required=True,
    )
    ensure_variable("project_name", type="string", description="Project name.", required=True)
    ensure_variable(
        "environment",
        type="string",
        description="Deployment environment.",
        default={"kind": "literal", "value": "development"},
        required=True,
    )
    ensure_local("name_prefix", {"kind": "expr", "value": 'format("%s-%s", var.project_name, var.environment)'})
    add_data_source({"terraform_type": "aws_caller_identity", "name": "current", "file": "providers.tf", "body": {}})

    lambdas = [resource for resource in architecture.resources if resource.provider_type == "aws_lambda_function"]
    apis = [resource for resource in architecture.resources if resource.provider_type == "aws_apigatewayv2_api"]
    s3_buckets = [resource for resource in architecture.resources if resource.provider_type == "aws_s3_bucket"]
    queues = [resource for resource in architecture.resources if resource.provider_type == "aws_sqs_queue"]
    dynamo_tables = [resource for resource in architecture.resources if resource.provider_type == "aws_dynamodb_table"]
    secret_resources = [
        resource for resource in architecture.resources
        if resource.provider_type in {"aws_secretsmanager_secret", "external_supabase"}
    ]
    capability_types = {item.capability_type for item in capability_plan.capabilities}

    if lambdas:
        add_resource(
            {
                "terraform_type": "aws_iam_role",
                "name": "lambda_execution_role",
                "file": "iam.tf",
                "body": {
                    "name": {"kind": "expr", "value": 'format("%s-lambda-role", local.name_prefix)'},
                    "assume_role_policy": {
                        "kind": "expr",
                        "value": 'jsonencode({Version = "2012-10-17", Statement = [{Effect = "Allow", Principal = {Service = "lambda.amazonaws.com"}, Action = "sts:AssumeRole"}]})',
                    },
                },
            }
        )
        add_resource(
            {
                "terraform_type": "aws_iam_role_policy_attachment",
                "name": "lambda_basic_execution",
                "file": "iam.tf",
                "body": {
                    "role": {"kind": "expr", "value": "aws_iam_role.lambda_execution_role.name"},
                    "policy_arn": {"kind": "literal", "value": "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"},
                },
            }
        )
        derive("aws_iam_role", "lambda_execution_role", "Execution role for Lambda functions.", "iam.tf")
        derive("aws_iam_role_policy_attachment", "lambda_basic_execution", "Basic CloudWatch logs permissions for Lambda.", "iam.tf")

    if secret_resources and lambdas:
        ensure_variable("supabase_url", type="string", description="External service URL.", required=True)
        ensure_variable(
            "supabase_service_role_key",
            type="string",
            description="External service secret key.",
            required=True,
            sensitive=True,
        )
        add_resource(
            {
                "terraform_type": "aws_secretsmanager_secret",
                "name": "supabase",
                "file": "secrets.tf",
                "architecture_resource_id": next((item.id for item in secret_resources), None),
                "body": {"name": {"kind": "expr", "value": 'format("%s-supabase", local.name_prefix)'}},
            }
        )
        add_resource(
            {
                "terraform_type": "aws_secretsmanager_secret_version",
                "name": "supabase",
                "file": "secrets.tf",
                "body": {
                    "secret_id": {"kind": "expr", "value": "aws_secretsmanager_secret.supabase.id"},
                    "secret_string": {
                        "kind": "expr",
                        "value": 'jsonencode({SUPABASE_URL = var.supabase_url, SUPABASE_SERVICE_ROLE_KEY = var.supabase_service_role_key})',
                    },
                },
            }
        )
        add_resource(
            {
                "terraform_type": "aws_iam_role_policy",
                "name": "lambda_secrets_access",
                "file": "iam.tf",
                "body": {
                    "name": {"kind": "expr", "value": 'format("%s-secrets-access", local.name_prefix)'},
                    "role": {"kind": "expr", "value": "aws_iam_role.lambda_execution_role.id"},
                    "policy": {
                        "kind": "expr",
                        "value": 'jsonencode({Version = "2012-10-17", Statement = [{Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.supabase.arn}]})',
                    },
                },
            }
        )
        derive("aws_secretsmanager_secret", "supabase", "Store external service credentials.", "secrets.tf")
        derive("aws_secretsmanager_secret_version", "supabase", "Store secret value payload.", "secrets.tf")
        derive("aws_iam_role_policy", "lambda_secrets_access", "Allow Lambda to read external service secret.", "iam.tf")
        missing_inputs.extend(["supabase_url", "supabase_service_role_key"])

    for api in apis:
        api_name = _safe_label(api.name)
        api_body = {
            "name": {"kind": "expr", "value": f'format("%s-{api_name}", local.name_prefix)'},
            "protocol_type": {"kind": "literal", "value": str(api.configuration.get("protocol_type", "HTTP")).upper() or "HTTP"},
        }
        cors = api.configuration.get("cors_configuration")
        if isinstance(cors, dict) and cors:
            api_body["cors_configuration"] = {
                "kind": "block",
                "type": "cors_configuration",
                "body": {key: _coerce_hcl_value(value) for key, value in cors.items()},
            }
        add_resource(
            {
                "terraform_type": "aws_apigatewayv2_api",
                "name": "http_api",
                "file": "api_gateway.tf",
                "architecture_resource_id": api.id,
                "body": api_body,
            }
        )
        add_resource(
            {
                "terraform_type": "aws_apigatewayv2_stage",
                "name": "default",
                "file": "api_gateway.tf",
                "body": {
                    "api_id": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.id"},
                    "name": {"kind": "literal", "value": "$default"},
                    "auto_deploy": {"kind": "literal", "value": True},
                },
            }
        )
        ensure_mapping(
            api.id,
            api.provider_type,
            "RENDERED",
            ["aws_apigatewayv2_api.http_api"],
            "Rendered as API Gateway API plus supporting stage and route wiring.",
        )
        derive("aws_apigatewayv2_stage", "default", "Expose the HTTP API with auto-deploy stage.", "api_gateway.tf")
        ensure_output(
            "api_endpoint",
            description="HTTP API endpoint.",
            value={"kind": "expr", "value": "aws_apigatewayv2_api.http_api.api_endpoint"},
        )

    for lambda_resource in lambdas:
        label = _safe_label(lambda_resource.name)
        package_var = f"{label}_package_path"
        handler_var = f"{label}_handler"
        ensure_variable(
            package_var,
            type="string",
            description=f"Path to the packaged artifact for {label}.",
            required=True,
        )
        ensure_variable(
            handler_var,
            type="string",
            description=f"Handler for {label}.",
            default={"kind": "literal", "value": str(lambda_resource.configuration.get("handler", "index.handler"))},
            required=True,
        )
        add_resource(
            {
                "terraform_type": "aws_cloudwatch_log_group",
                "name": label,
                "file": "observability.tf",
                "architecture_resource_id": lambda_resource.id,
                "body": {
                    "name": {"kind": "expr", "value": f'format("/aws/lambda/%s-{label}", local.name_prefix)'},
                    "retention_in_days": {"kind": "literal", "value": 7},
                },
            }
        )
        lambda_body = {
            "function_name": {"kind": "expr", "value": f'format("%s-{label}", local.name_prefix)'},
            "role": {"kind": "expr", "value": "aws_iam_role.lambda_execution_role.arn"},
            "runtime": {"kind": "literal", "value": str(lambda_resource.configuration.get("runtime", "nodejs20.x"))},
            "handler": {"kind": "expr", "value": f"var.{handler_var}"},
            "filename": {"kind": "expr", "value": f"var.{package_var}"},
            "memory_size": {"kind": "literal", "value": int(lambda_resource.configuration.get("memory_size", 512))},
            "timeout": {"kind": "literal", "value": int(lambda_resource.configuration.get("timeout", 29))},
            "source_code_hash": {"kind": "expr", "value": f"filebase64sha256(var.{package_var})"},
        }
        if secret_resources:
            lambda_body["environment"] = {
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
            }
        add_resource(
            {
                "terraform_type": "aws_lambda_function",
                "name": label,
                "file": "lambda.tf",
                "architecture_resource_id": lambda_resource.id,
                "body": lambda_body,
                "depends_on": [f"aws_cloudwatch_log_group.{label}"],
            }
        )
        ensure_mapping(
            lambda_resource.id,
            lambda_resource.provider_type,
            "RENDERED",
            [f"aws_lambda_function.{label}"],
            "Rendered as Lambda function with execution role, log group, and relationship wiring.",
        )
        derive("aws_cloudwatch_log_group", label, f"Observability logs for {label}.", "observability.tf")
        missing_inputs.append(package_var)

    for relation_index, relation in enumerate(architecture.relationships):
        source_id = str(relation.get("source_id", ""))
        target_id = str(relation.get("target_id", ""))
        source = architecture.resource(source_id)
        target = architecture.resource(target_id)
        if not source or not target:
            continue
        if source.provider_type == "aws_apigatewayv2_api" and target.provider_type == "aws_lambda_function":
            label = _safe_label(target.name)
            route_key = _route_key_from_label(str(relation.get("label", ""))) or f"ANY /{label}/{{proxy+}}"
            add_resource(
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
                }
            )
            add_resource(
                {
                    "terraform_type": "aws_apigatewayv2_route",
                    "name": f"{label}_route",
                    "file": "api_gateway.tf",
                    "body": {
                        "api_id": {"kind": "expr", "value": "aws_apigatewayv2_api.http_api.id"},
                        "route_key": {"kind": "literal", "value": route_key},
                        "target": {
                            "kind": "expr",
                            "value": f'"integrations/${{aws_apigatewayv2_integration.{label}_integration.id}}"',
                        },
                    },
                }
            )
            add_resource(
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
                }
            )
            derive("aws_apigatewayv2_integration", f"{label}_integration", f"Wire API Gateway to Lambda {label}.", "api_gateway.tf")
            derive("aws_apigatewayv2_route", f"{label}_route", f"Route traffic to Lambda {label}.", "api_gateway.tf")
            derive("aws_lambda_permission", f"allow_api_gateway_{label}", f"Allow API Gateway to invoke Lambda {label}.", "lambda.tf")
            validation_assertions.append(f"Relationship {relation.get('id') or relation_index} should render API Gateway route, integration, and Lambda permission.")

    for bucket in s3_buckets:
        label = _safe_label(bucket.name)
        add_resource(
            {
                "terraform_type": "aws_s3_bucket",
                "name": label,
                "file": "storage.tf",
                "architecture_resource_id": bucket.id,
                "body": {"bucket": {"kind": "expr", "value": f'format("%s-{label}", local.name_prefix)'}},
            }
        )
        add_resource(
            {
                "terraform_type": "aws_s3_bucket_public_access_block",
                "name": label,
                "file": "storage.tf",
                "body": {
                    "bucket": {"kind": "expr", "value": f"aws_s3_bucket.{label}.id"},
                    "block_public_acls": {"kind": "literal", "value": True},
                    "block_public_policy": {"kind": "literal", "value": True},
                    "ignore_public_acls": {"kind": "literal", "value": True},
                    "restrict_public_buckets": {"kind": "literal", "value": True},
                },
            }
        )
        ensure_mapping(bucket.id, bucket.provider_type, "RENDERED", [f"aws_s3_bucket.{label}"], "Rendered as S3 bucket with public access blocked.")

    for queue in queues:
        label = _safe_label(queue.name)
        add_resource(
            {
                "terraform_type": "aws_sqs_queue",
                "name": label,
                "file": "compute.tf",
                "architecture_resource_id": queue.id,
                "body": {
                    "name": {"kind": "expr", "value": f'format("%s-{label}", local.name_prefix)'},
                    "visibility_timeout_seconds": {"kind": "literal", "value": int(queue.configuration.get("visibility_timeout_seconds", 30))},
                },
            }
        )
        ensure_mapping(queue.id, queue.provider_type, "RENDERED", [f"aws_sqs_queue.{label}"], "Rendered as SQS queue.")

    for table in dynamo_tables:
        label = _safe_label(table.name)
        hash_key = str(table.configuration.get("hash_key", "id"))
        add_resource(
            {
                "terraform_type": "aws_dynamodb_table",
                "name": label,
                "file": "compute.tf",
                "architecture_resource_id": table.id,
                "body": {
                    "name": {"kind": "expr", "value": f'format("%s-{label}", local.name_prefix)'},
                    "billing_mode": {"kind": "literal", "value": str(table.configuration.get("billing_mode", "PAY_PER_REQUEST"))},
                    "hash_key": {"kind": "literal", "value": hash_key},
                    "attribute": {
                        "kind": "block",
                        "type": "attribute",
                        "body": {
                            "name": {"kind": "literal", "value": hash_key},
                            "type": {"kind": "literal", "value": str(table.configuration.get("hash_key_type", "S"))},
                        },
                    },
                },
            }
        )
        ensure_mapping(table.id, table.provider_type, "RENDERED", [f"aws_dynamodb_table.{label}"], "Rendered as DynamoDB table.")

    for resource in architecture.resources:
        if resource.provider_type == "external_supabase":
            ensure_mapping(
                resource.id,
                resource.provider_type,
                "EXTERNAL",
                [],
                "External dependency handled via variables and AWS Secrets Manager references.",
            )
            ensure_external_dependency(
                resource.id,
                resource.provider_type,
                resource.name,
                "variables_and_secret_reference",
                "Nimbus does not provision external Supabase resources directly.",
            )
        elif resource.provider_type == "aws_secretsmanager_secret":
            ensure_mapping(
                resource.id,
                resource.provider_type,
                "RENDERED",
                ["aws_secretsmanager_secret.supabase", "aws_secretsmanager_secret_version.supabase"],
                "Aggregate mapping to generated secret resources.",
            )
        elif resource.provider_type == "aws_iam_role":
            ensure_mapping(
                resource.id,
                resource.provider_type,
                "RENDERED",
                [
                    "aws_iam_role.lambda_execution_role",
                    "aws_iam_role_policy.lambda_secrets_access",
                    "aws_iam_role_policy_attachment.lambda_basic_execution",
                ],
                "Aggregate mapping to generated IAM execution resources.",
            )
        elif resource.provider_type == "aws_cloudwatch_log_group" and lambdas:
            ensure_mapping(
                resource.id,
                resource.provider_type,
                "RENDERED",
                [f"aws_cloudwatch_log_group.{_safe_label(item.name)}" for item in lambdas],
                "Aggregate mapping to generated Lambda log groups.",
            )
        elif resource.provider_type.startswith("external_"):
            ensure_mapping(resource.id, resource.provider_type, "EXTERNAL", [], "External dependency.")

    warnings.extend(capability_plan.warnings)
    warnings.append("Planner output was normalized through Nimbus capability-based planning and deterministic coverage repair.")

    for capability_type in capability_types:
        primitives = ", ".join(catalog.terraform_primitives_for(capability_type))
        validation_assertions.append(f"{capability_type} should be implemented by one or more of: {primitives}.")

    data["variables"] = variables
    data["locals"] = locals_list
    data["data_sources"] = data_sources
    data["resources"] = resources
    data["outputs"] = outputs
    data["architecture_resource_mappings"] = mappings
    data["external_dependencies"] = external_dependencies
    data["derived_resources"] = derived_resources
    data["missing_inputs"] = missing_inputs
    data["warnings"] = warnings
    data["validation_assertions"] = validation_assertions
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


def _dedupe_strings(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
