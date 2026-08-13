from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


CapabilityType = Literal[
    "PUBLIC_HTTP_ENTRYPOINT",
    "REALTIME_CONNECTIONS",
    "ASYNC_QUEUE",
    "BACKGROUND_WORKER",
    "OBJECT_STORAGE",
    "RELATIONAL_DATABASE",
    "KEY_VALUE_STORE",
    "JOB_STATUS_STORE",
    "SECRET_STORAGE",
    "AUTHENTICATION",
    "SERVERLESS_COMPUTE",
    "CONTAINER_COMPUTE",
    "PRIVATE_NETWORKING",
    "OBSERVABILITY_LOGS",
    "IAM_EXECUTION_ROLE",
    "EVENT_ROUTING",
    "SCHEDULED_TASKS",
    "CDN_STATIC_HOSTING",
]

ImplementationKind = Literal["MANAGED", "EXTERNAL", "MISSING_INPUT", "UNSUPPORTED"]


class InfrastructureCapability(BaseModel):
    capability_type: CapabilityType
    source_architecture_resource_ids: list[str] = Field(default_factory=list)
    required: bool = True
    external: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class ProviderServiceSelection(BaseModel):
    capability_type: CapabilityType
    selected_service: str
    implementation_kind: ImplementationKind = "MANAGED"
    terraform_primitives: list[str] = Field(default_factory=list)
    rationale: str = ""


class InfrastructureCapabilityPlan(BaseModel):
    plan_version: str = "1.0.0"
    cloud_provider: str = "AWS"
    capabilities: list[InfrastructureCapability] = Field(default_factory=list)
    provider_service_selections: list[ProviderServiceSelection] = Field(default_factory=list)
    deployable_architecture_resource_ids: list[str] = Field(default_factory=list)
    external_architecture_resource_ids: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
