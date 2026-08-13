from __future__ import annotations

from pydantic import BaseModel

from app.planning.terraform_resource_plan_schema import TerraformResourcePlan
from app.services.architecture_normalizer import NormalizedArchitecture


class CoverageFinding(BaseModel):
    code: str
    severity: str
    architecture_resource_id: str | None = None
    relationship_id: str | None = None
    expected: str
    actual: str
    recommendation: str


class TerraformResourcePlanCoverageValidator:
    def validate(
        self,
        architecture: NormalizedArchitecture,
        plan: TerraformResourcePlan,
    ) -> list[CoverageFinding]:
        findings: list[CoverageFinding] = []
        mappings = {item.architecture_resource_id: item for item in plan.architecture_resource_mappings}
        resources_by_address = {
            f"{resource.terraform_type}.{resource.name}": resource
            for resource in plan.resources
        }

        for resource in architecture.resources:
            mapping = mappings.get(resource.id)
            if mapping is None:
                findings.append(CoverageFinding(
                    code="MISSING_MAPPING",
                    severity="HIGH",
                    architecture_resource_id=resource.id,
                    expected="Architecture resource should have a mapping entry.",
                    actual="No mapping entry was present.",
                    recommendation="Add a mapping that marks the resource as RENDERED, EXTERNAL, UNSUPPORTED, or NEEDS_INPUT.",
                ))
                continue
            if resource.provider_type == "external_supabase" and mapping.mapping_status != "EXTERNAL":
                findings.append(CoverageFinding(
                    code="EXTERNAL_RESOURCE_MISCLASSIFIED",
                    severity="HIGH",
                    architecture_resource_id=resource.id,
                    expected="external_supabase should be marked EXTERNAL.",
                    actual=f"mapping_status={mapping.mapping_status}",
                    recommendation="Mark external services as EXTERNAL and handle them through variables, secrets, or outputs only.",
                ))
            if resource.provider_type == "aws_lambda_function":
                lambda_addresses = [addr for addr in mapping.terraform_addresses if addr.startswith("aws_lambda_function.")]
                if mapping.mapping_status != "RENDERED":
                    findings.append(CoverageFinding(
                        code="LAMBDA_NOT_RENDERED",
                        severity="HIGH",
                        architecture_resource_id=resource.id,
                        expected="Lambda resources should be marked RENDERED.",
                        actual=f"mapping_status={mapping.mapping_status}",
                        recommendation="Render a matching aws_lambda_function and mark the mapping as RENDERED.",
                    ))
                elif not lambda_addresses:
                    findings.append(CoverageFinding(
                        code="LAMBDA_ADDRESS_MISSING",
                        severity="HIGH",
                        architecture_resource_id=resource.id,
                        expected="Lambda mapping should reference aws_lambda_function.*",
                        actual=str(mapping.terraform_addresses),
                        recommendation="Add the rendered aws_lambda_function address to terraform_addresses.",
                    ))
            if mapping.mapping_status == "RENDERED":
                for address in mapping.terraform_addresses:
                    if address not in resources_by_address:
                        findings.append(CoverageFinding(
                            code="MAPPING_TARGET_MISSING",
                            severity="HIGH",
                            architecture_resource_id=resource.id,
                            expected=f"Rendered mapping target {address} should exist in plan.resources.",
                            actual="Referenced Terraform resource is missing.",
                            recommendation="Ensure terraform_addresses only reference actual rendered Terraform resources.",
                        ))

            for dep in resource.depends_on:
                if architecture.resource(dep) is None:
                    findings.append(CoverageFinding(
                        code="DEPENDENCY_TARGET_MISSING",
                        severity="MEDIUM",
                        architecture_resource_id=resource.id,
                        expected=f"depends_on target {dep} should exist in architecture resources.",
                        actual="Referenced dependency target does not exist.",
                        recommendation="Remove or correct the missing depends_on target.",
                    ))

        for index, relation in enumerate(architecture.relationships):
            source = relation.get("source_id")
            target = relation.get("target_id")
            label = str(relation.get("label", ""))
            relationship_id = str(relation.get("id") or f"relationship-{index}")
            source_resource = architecture.resource(source) if source else None
            target_resource = architecture.resource(target) if target else None
            if not source_resource or not target_resource:
                continue
            if source_resource.provider_type == "aws_apigatewayv2_api" and target_resource.provider_type == "aws_lambda_function":
                target_mapping = mappings.get(target_resource.id)
                route_key = _route_key_from_label(label)
                if not target_mapping:
                    findings.append(CoverageFinding(
                        code="API_GATEWAY_TARGET_MAPPING_MISSING",
                        severity="HIGH",
                        architecture_resource_id=target_resource.id,
                        relationship_id=relationship_id,
                        expected="API Gateway target Lambda should have a mapping.",
                        actual="No Lambda mapping was present.",
                        recommendation="Add a RENDERED mapping for the target Lambda.",
                    ))
                    continue
                lambda_addresses = [addr for addr in target_mapping.terraform_addresses if addr.startswith("aws_lambda_function.")]
                if not lambda_addresses:
                    findings.append(CoverageFinding(
                        code="API_GATEWAY_TARGET_LAMBDA_MISSING",
                        severity="HIGH",
                        architecture_resource_id=target_resource.id,
                        relationship_id=relationship_id,
                        expected="Relationship target should reference a rendered aws_lambda_function.",
                        actual=str(target_mapping.terraform_addresses),
                        recommendation="Ensure the target Lambda mapping points to an aws_lambda_function resource.",
                    ))
                    continue
                lambda_name = lambda_addresses[0].split(".", 1)[1]
                if f"aws_apigatewayv2_integration.{lambda_name}_integration" not in resources_by_address:
                    findings.append(CoverageFinding(
                        code="API_GATEWAY_INTEGRATION_MISSING",
                        severity="HIGH",
                        architecture_resource_id=target_resource.id,
                        relationship_id=relationship_id,
                        expected=f"aws_apigatewayv2_integration.{lambda_name}_integration",
                        actual="Integration resource missing.",
                        recommendation="Render an API Gateway integration for each API Gateway to Lambda relationship.",
                    ))
                if f"aws_apigatewayv2_route.{lambda_name}_route" not in resources_by_address:
                    findings.append(CoverageFinding(
                        code="API_GATEWAY_ROUTE_MISSING",
                        severity="HIGH",
                        architecture_resource_id=target_resource.id,
                        relationship_id=relationship_id,
                        expected=f"aws_apigatewayv2_route.{lambda_name}_route",
                        actual="Route resource missing.",
                        recommendation="Render a distinct API Gateway route for each relationship-derived path.",
                    ))
                if f"aws_lambda_permission.allow_api_gateway_{lambda_name}" not in resources_by_address:
                    findings.append(CoverageFinding(
                        code="LAMBDA_PERMISSION_MISSING",
                        severity="HIGH",
                        architecture_resource_id=target_resource.id,
                        relationship_id=relationship_id,
                        expected=f"aws_lambda_permission.allow_api_gateway_{lambda_name}",
                        actual="Lambda permission resource missing.",
                        recommendation="Render aws_lambda_permission for each API Gateway to Lambda relationship.",
                    ))
                route_resource = resources_by_address.get(f"aws_apigatewayv2_route.{lambda_name}_route")
                if route_resource and route_key:
                    configured = route_resource.body.get("route_key")
                    value = getattr(configured, "value", None)
                    if isinstance(value, str) and value != route_key:
                        findings.append(CoverageFinding(
                            code="API_GATEWAY_ROUTE_KEY_MISMATCH",
                            severity="MEDIUM",
                            architecture_resource_id=target_resource.id,
                            relationship_id=relationship_id,
                            expected=route_key,
                            actual=value,
                            recommendation="Use the route derived from the relationship label.",
                        ))
        return findings


def _route_key_from_label(label: str) -> str | None:
    if "/api/central/*" in label:
        return "ANY /api/central/{proxy+}"
    if "/api/games/*" in label:
        return "ANY /api/games/{proxy+}"
    return None
