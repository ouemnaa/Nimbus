from __future__ import annotations

from collections import OrderedDict

from app.services.architecture_normalizer import NormalizedArchitecture

from .aws_capability_catalog import AwsCapabilityCatalog
from .infrastructure_capability_plan import (
    CapabilityType,
    InfrastructureCapability,
    InfrastructureCapabilityPlan,
    ProviderServiceSelection,
)


class InfrastructureCapabilityExtractor:
    def __init__(self, catalog: AwsCapabilityCatalog | None = None) -> None:
        self.catalog = catalog or AwsCapabilityCatalog()

    def extract(self, architecture: NormalizedArchitecture) -> InfrastructureCapabilityPlan:
        capabilities: "OrderedDict[CapabilityType, InfrastructureCapability]" = OrderedDict()

        def add(
            capability_type: CapabilityType,
            resource_id: str | None = None,
            *,
            external: bool = False,
            details: dict | None = None,
        ) -> None:
            existing = capabilities.get(capability_type)
            if existing is None:
                existing = InfrastructureCapability(
                    capability_type=capability_type,
                    source_architecture_resource_ids=[],
                    required=True,
                    external=external,
                    details={},
                )
                capabilities[capability_type] = existing
            if resource_id and resource_id not in existing.source_architecture_resource_ids:
                existing.source_architecture_resource_ids.append(resource_id)
            existing.external = existing.external and external if existing.source_architecture_resource_ids else external
            if details:
                existing.details.update(details)

        deployable_ids: list[str] = []
        external_ids: list[str] = []
        warnings: list[str] = []

        for resource in architecture.resources:
            provider_type = resource.provider_type
            name = f"{resource.id} {resource.name} {resource.category}".lower()
            if provider_type.startswith("external_"):
                external_ids.append(resource.id)
            else:
                deployable_ids.append(resource.id)

            if provider_type in {"aws_apigatewayv2_api", "aws_lb", "aws_cloudfront_distribution"}:
                add("PUBLIC_HTTP_ENTRYPOINT", resource.id)
            if provider_type == "aws_apigatewayv2_api" and str(resource.configuration.get("protocol_type", "")).upper() == "WEBSOCKET":
                add("REALTIME_CONNECTIONS", resource.id)
            if provider_type == "aws_sqs_queue":
                add("ASYNC_QUEUE", resource.id)
            if provider_type in {"aws_lambda_function", "aws_ecs_service"} and any(token in name for token in ("worker", "job", "processor", "consumer")):
                add("BACKGROUND_WORKER", resource.id)
            if provider_type == "aws_s3_bucket":
                add("OBJECT_STORAGE", resource.id)
            if provider_type == "aws_db_instance":
                add("RELATIONAL_DATABASE", resource.id)
            if provider_type == "aws_dynamodb_table":
                add("KEY_VALUE_STORE", resource.id)
                if any(token in name for token in ("job", "status", "queue", "task")):
                    add("JOB_STATUS_STORE", resource.id)
            if provider_type in {"aws_secretsmanager_secret", "aws_secretsmanager_secret_version"}:
                add("SECRET_STORAGE", resource.id)
            if provider_type in {"aws_cognito_user_pool", "aws_cognito_user_pool_client"}:
                add("AUTHENTICATION", resource.id)
            if provider_type == "aws_lambda_function":
                add("SERVERLESS_COMPUTE", resource.id, details={"runtime": resource.configuration.get("runtime")})
            if provider_type in {"aws_ecs_cluster", "aws_ecs_service", "aws_ecs_task_definition"}:
                add("CONTAINER_COMPUTE", resource.id)
            if provider_type in {
                "aws_vpc", "aws_subnet", "aws_route_table", "aws_route", "aws_route_table_association",
                "aws_internet_gateway", "aws_nat_gateway", "aws_eip",
            }:
                add("PRIVATE_NETWORKING", resource.id)
            if provider_type == "aws_cloudwatch_log_group":
                add("OBSERVABILITY_LOGS", resource.id)
            if provider_type in {"aws_iam_role", "aws_iam_policy", "aws_iam_role_policy_attachment"}:
                add("IAM_EXECUTION_ROLE", resource.id)
            if provider_type in {"aws_apigatewayv2_route", "aws_apigatewayv2_integration", "aws_cloudwatch_event_rule", "aws_cloudwatch_event_target"}:
                add("EVENT_ROUTING", resource.id)
            if provider_type == "aws_cloudwatch_event_rule":
                add("SCHEDULED_TASKS", resource.id)
            if provider_type in {"aws_cloudfront_distribution", "aws_route53_record", "aws_route53_zone", "aws_acm_certificate"}:
                add("CDN_STATIC_HOSTING", resource.id)
            if provider_type == "external_supabase":
                add("SECRET_STORAGE", resource.id, external=True)
                add("RELATIONAL_DATABASE", resource.id, external=True)
                warnings.append("Detected external Supabase dependency; mark provider-managed data plane resources as EXTERNAL.")

        for relation in architecture.relationships:
            source = architecture.resource(str(relation.get("source_id", "")))
            target = architecture.resource(str(relation.get("target_id", "")))
            if not source or not target:
                continue
            if source.provider_type == "aws_apigatewayv2_api":
                add("EVENT_ROUTING", source.id)
                if target.provider_type == "aws_lambda_function":
                    add("PUBLIC_HTTP_ENTRYPOINT", source.id)
            if any(token in str(relation.get("label", "")).lower() for token in ("schedule", "cron", "every ")):
                add("SCHEDULED_TASKS", source.id)

        selections = self._select_services(capabilities)
        return InfrastructureCapabilityPlan(
            cloud_provider=str(getattr(architecture, "provider", "AWS")).upper(),
            capabilities=list(capabilities.values()),
            provider_service_selections=selections,
            deployable_architecture_resource_ids=deployable_ids,
            external_architecture_resource_ids=external_ids,
            warnings=_dedupe(warnings),
        )

    def _select_services(
        self,
        capabilities: "OrderedDict[CapabilityType, InfrastructureCapability]",
    ) -> list[ProviderServiceSelection]:
        selections: list[ProviderServiceSelection] = []
        has_serverless = "SERVERLESS_COMPUTE" in capabilities
        has_container = "CONTAINER_COMPUTE" in capabilities

        for capability_type, capability in capabilities.items():
            if capability.external:
                selections.append(
                    ProviderServiceSelection(
                        capability_type=capability_type,
                        selected_service="External service",
                        implementation_kind="EXTERNAL",
                        terraform_primitives=[],
                        rationale="Capability is provided by an external dependency.",
                    )
                )
                continue

            selected_service = self.catalog.definition(capability_type).service_options[0]
            if capability_type == "PUBLIC_HTTP_ENTRYPOINT":
                selected_service = "API Gateway HTTP API" if has_serverless and not has_container else "Application Load Balancer"
            elif capability_type == "BACKGROUND_WORKER":
                selected_service = "Lambda" if has_serverless else "ECS Fargate"
            elif capability_type == "AUTHENTICATION" and capability.external:
                selected_service = "External identity provider"

            definition = self.catalog.definition(capability_type)
            selections.append(
                ProviderServiceSelection(
                    capability_type=capability_type,
                    selected_service=selected_service,
                    implementation_kind="MANAGED",
                    terraform_primitives=definition.terraform_primitives,
                    rationale=definition.notes,
                )
            )
        return selections


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
