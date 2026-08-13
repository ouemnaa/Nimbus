from __future__ import annotations

from pydantic import BaseModel

from app.services.architecture_normalizer import NormalizedArchitecture

from .aws_capability_catalog import AwsCapabilityCatalog
from .capability_extractor import InfrastructureCapabilityExtractor
from .infrastructure_capability_plan import InfrastructureCapabilityPlan
from .terraform_resource_plan_schema import TerraformResourcePlan


class CoverageFinding(BaseModel):
    code: str
    severity: str
    architecture_resource_id: str | None = None
    relationship_id: str | None = None
    expected: str
    actual: str
    recommendation: str


class TerraformResourcePlanCoverageValidator:
    def __init__(self) -> None:
        self.catalog = AwsCapabilityCatalog()
        self.extractor = InfrastructureCapabilityExtractor(self.catalog)

    def validate(
        self,
        architecture: NormalizedArchitecture,
        plan: TerraformResourcePlan,
    ) -> list[CoverageFinding]:
        findings: list[CoverageFinding] = []
        capability_plan = plan.infrastructure_capability_plan or self.extractor.extract(architecture)
        mappings = {item.architecture_resource_id: item for item in plan.architecture_resource_mappings}
        resources_by_address = {
            f"{resource.terraform_type}.{resource.name}": resource
            for resource in plan.resources
        }
        resources_by_type: dict[str, list[str]] = {}
        for address, resource in resources_by_address.items():
            resources_by_type.setdefault(resource.terraform_type, []).append(address)

        self._validate_global_shape(plan, findings)
        self._validate_capabilities(capability_plan, plan, resources_by_type, findings)
        self._validate_architecture_resources(architecture, mappings, resources_by_address, findings)
        self._validate_relationships(architecture, mappings, resources_by_address, findings)
        return findings

    def _validate_global_shape(
        self,
        plan: TerraformResourcePlan,
        findings: list[CoverageFinding],
    ) -> None:
        if not plan.resources:
            findings.append(
                CoverageFinding(
                    code="ZERO_RESOURCE_PLAN",
                    severity="HIGH",
                    expected="At least one concrete Terraform resource should be rendered.",
                    actual="plan.resources is empty.",
                    recommendation="Expand the capability selections into managed Terraform resources before rendering.",
                )
            )

    def _validate_capabilities(
        self,
        capability_plan: InfrastructureCapabilityPlan,
        plan: TerraformResourcePlan,
        resources_by_type: dict[str, list[str]],
        findings: list[CoverageFinding],
    ) -> None:
        available_variables = {item.name for item in plan.variables}
        available_external_ids = {item.architecture_resource_id for item in plan.external_dependencies}
        selection_by_capability = {
            item.capability_type: item
            for item in capability_plan.provider_service_selections
        }

        for capability in capability_plan.capabilities:
            selection = selection_by_capability.get(capability.capability_type)
            acceptable_types = set(self.catalog.terraform_primitives_for(capability.capability_type))
            matching_addresses = [
                address
                for tf_type, addresses in resources_by_type.items()
                if tf_type in acceptable_types
                for address in addresses
            ]
            implemented = bool(matching_addresses)
            if not implemented and capability.external:
                implemented = any(resource_id in available_external_ids for resource_id in capability.source_architecture_resource_ids)
            if not implemented and capability.capability_type == "SECRET_STORAGE":
                implemented = bool({"supabase_url", "supabase_service_role_key"} & available_variables)
            if not implemented and selection and selection.implementation_kind == "MISSING_INPUT":
                implemented = bool(plan.missing_inputs)

            if not implemented:
                findings.append(
                    CoverageFinding(
                        code="CAPABILITY_NOT_IMPLEMENTED",
                        severity="HIGH",
                        architecture_resource_id=capability.source_architecture_resource_ids[0] if capability.source_architecture_resource_ids else None,
                        expected=f"{capability.capability_type} should be implemented by Terraform resources, data sources, external mappings, or explicit missing inputs.",
                        actual="No matching implementation was found in the TerraformResourcePlan.",
                        recommendation="Select AWS services for this capability and expand them into concrete Terraform resources.",
                    )
                )

        deployable_ids = set(capability_plan.deployable_architecture_resource_ids)
        abstract_mappings = 0
        if deployable_ids:
            for resource_id in deployable_ids:
                mapping = next((item for item in plan.architecture_resource_mappings if item.architecture_resource_id == resource_id), None)
                if mapping and mapping.mapping_status in {"UNSUPPORTED", "NEEDS_INPUT"}:
                    abstract_mappings += 1
            if abstract_mappings / max(len(deployable_ids), 1) > 0.5:
                findings.append(
                    CoverageFinding(
                        code="PLAN_TOO_ABSTRACT",
                        severity="HIGH",
                        expected="At least half of deployable architecture resources should map to concrete rendered Terraform resources.",
                        actual=f"{abstract_mappings} of {len(deployable_ids)} deployable resources are still UNSUPPORTED or NEEDS_INPUT.",
                        recommendation="Produce a less abstract TerraformResourcePlan with concrete AWS resources before rendering.",
                    )
                )

    def _validate_architecture_resources(
        self,
        architecture: NormalizedArchitecture,
        mappings: dict[str, object],
        resources_by_address: dict[str, object],
        findings: list[CoverageFinding],
    ) -> None:
        for resource in architecture.resources:
            mapping = mappings.get(resource.id)
            if mapping is None:
                findings.append(
                    CoverageFinding(
                        code="MISSING_MAPPING",
                        severity="HIGH",
                        architecture_resource_id=resource.id,
                        expected="Architecture resource should have a mapping entry.",
                        actual="No mapping entry was present.",
                        recommendation="Add a mapping that marks the resource as RENDERED, EXTERNAL, UNSUPPORTED, or NEEDS_INPUT.",
                    )
                )
                continue

            if resource.provider_type.startswith("external_"):
                if mapping.mapping_status != "EXTERNAL":
                    findings.append(
                        CoverageFinding(
                            code="EXTERNAL_RESOURCE_MISCLASSIFIED",
                            severity="HIGH",
                            architecture_resource_id=resource.id,
                            expected=f"{resource.provider_type} should be marked EXTERNAL.",
                            actual=f"mapping_status={mapping.mapping_status}",
                            recommendation="Mark external services as EXTERNAL and handle them through variables, secrets, or outputs only.",
                        )
                    )
                continue

            if mapping.mapping_status != "RENDERED":
                findings.append(
                    CoverageFinding(
                        code="NON_EXTERNAL_RESOURCE_NOT_RENDERED",
                        severity="HIGH",
                        architecture_resource_id=resource.id,
                        expected="Every non-external architecture resource should map to concrete Terraform addresses.",
                        actual=f"mapping_status={mapping.mapping_status}",
                        recommendation="Render concrete Terraform resources or convert the dependency to an explicit EXTERNAL mapping.",
                    )
                )
                continue

            if not mapping.terraform_addresses:
                findings.append(
                    CoverageFinding(
                        code="RENDERED_MAPPING_ADDRESS_MISSING",
                        severity="HIGH",
                        architecture_resource_id=resource.id,
                        expected="Rendered mappings should reference at least one Terraform address.",
                        actual="terraform_addresses is empty.",
                        recommendation="Add the concrete Terraform addresses produced for this architecture resource.",
                    )
                )
            for address in mapping.terraform_addresses:
                if address not in resources_by_address:
                    findings.append(
                        CoverageFinding(
                            code="MAPPING_TARGET_MISSING",
                            severity="HIGH",
                            architecture_resource_id=resource.id,
                            expected=f"Rendered mapping target {address} should exist in plan.resources.",
                            actual="Referenced Terraform resource is missing.",
                            recommendation="Ensure terraform_addresses only reference actual rendered Terraform resources.",
                        )
                    )

            for dep in resource.depends_on:
                if architecture.resource(dep) is None:
                    findings.append(
                        CoverageFinding(
                            code="DEPENDENCY_TARGET_MISSING",
                            severity="MEDIUM",
                            architecture_resource_id=resource.id,
                            expected=f"depends_on target {dep} should exist in architecture resources.",
                            actual="Referenced dependency target does not exist.",
                            recommendation="Remove or correct the missing depends_on target.",
                        )
                    )

    def _validate_relationships(
        self,
        architecture: NormalizedArchitecture,
        mappings: dict[str, object],
        resources_by_address: dict[str, object],
        findings: list[CoverageFinding],
    ) -> None:
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
                    findings.append(
                        CoverageFinding(
                            code="API_GATEWAY_TARGET_MAPPING_MISSING",
                            severity="HIGH",
                            architecture_resource_id=target_resource.id,
                            relationship_id=relationship_id,
                            expected="API Gateway target Lambda should have a mapping.",
                            actual="No Lambda mapping was present.",
                            recommendation="Add a RENDERED mapping for the target Lambda.",
                        )
                    )
                    continue
                lambda_addresses = [addr for addr in target_mapping.terraform_addresses if addr.startswith("aws_lambda_function.")]
                if not lambda_addresses:
                    findings.append(
                        CoverageFinding(
                            code="API_GATEWAY_TARGET_LAMBDA_MISSING",
                            severity="HIGH",
                            architecture_resource_id=target_resource.id,
                            relationship_id=relationship_id,
                            expected="Relationship target should reference a rendered aws_lambda_function.",
                            actual=str(target_mapping.terraform_addresses),
                            recommendation="Ensure the target Lambda mapping points to an aws_lambda_function resource.",
                        )
                    )
                    continue
                lambda_name = lambda_addresses[0].split(".", 1)[1]
                expected_addresses = {
                    f"aws_apigatewayv2_integration.{lambda_name}_integration": "API Gateway integration resource missing.",
                    f"aws_apigatewayv2_route.{lambda_name}_route": "API Gateway route resource missing.",
                    f"aws_lambda_permission.allow_api_gateway_{lambda_name}": "Lambda permission resource missing.",
                }
                for expected_address, actual_message in expected_addresses.items():
                    if expected_address not in resources_by_address:
                        findings.append(
                            CoverageFinding(
                                code=expected_address.split(".")[0].upper() + "_MISSING",
                                severity="HIGH",
                                architecture_resource_id=target_resource.id,
                                relationship_id=relationship_id,
                                expected=expected_address,
                                actual=actual_message,
                                recommendation="Render concrete relationship wiring resources for API Gateway to Lambda connections.",
                            )
                        )
                route_resource = resources_by_address.get(f"aws_apigatewayv2_route.{lambda_name}_route")
                if route_resource and route_key:
                    configured = route_resource.body.get("route_key")
                    value = getattr(configured, "value", None)
                    if isinstance(value, str) and value != route_key:
                        findings.append(
                            CoverageFinding(
                                code="API_GATEWAY_ROUTE_KEY_MISMATCH",
                                severity="MEDIUM",
                                architecture_resource_id=target_resource.id,
                                relationship_id=relationship_id,
                                expected=route_key,
                                actual=value,
                                recommendation="Use the route derived from the relationship label.",
                            )
                        )


def _route_key_from_label(label: str) -> str | None:
    if "/api/central/*" in label:
        return "ANY /api/central/{proxy+}"
    if "/api/games/*" in label:
        return "ANY /api/games/{proxy+}"
    return None
