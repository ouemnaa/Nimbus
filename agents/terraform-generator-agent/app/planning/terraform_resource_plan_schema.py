from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


AllowedOutputFile = Literal[
    "versions.tf",
    "providers.tf",
    "variables.tf",
    "locals.tf",
    "networking.tf",
    "security_groups.tf",
    "iam.tf",
    "compute.tf",
    "lambda.tf",
    "api_gateway.tf",
    "database.tf",
    "storage.tf",
    "secrets.tf",
    "observability.tf",
    "outputs.tf",
    "terraform.tfvars.example",
    "README.generated.md",
]

MappingStatus = Literal["RENDERED", "DERIVED", "EXTERNAL", "UNSUPPORTED", "NEEDS_INPUT"]


class ProviderRequirement(BaseModel):
    name: str
    source: str
    version: str
    configuration_aliases: list[str] = Field(default_factory=list)


class HCLValue(BaseModel):
    kind: Literal["literal", "expr", "list", "object", "block"]
    value: Any | None = None
    items: list["HCLValue"] | dict[str, "HCLValue"] = Field(default_factory=list)
    type: str | None = None
    labels: list[str] = Field(default_factory=list)
    body: dict[str, "HCLValue"] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_shape(self) -> "HCLValue":
        if self.kind == "list" and not isinstance(self.items, list):
            raise ValueError("list HCLValue must use list items")
        if self.kind == "object" and not isinstance(self.items, dict):
            raise ValueError("object HCLValue must use dict items")
        if self.kind == "block" and not self.type:
            raise ValueError("block HCLValue requires type")
        return self


class TerraformVariable(BaseModel):
    name: str
    type: str
    description: str = ""
    default: HCLValue | None = None
    sensitive: bool = False
    required: bool = False


class TerraformLocal(BaseModel):
    name: str
    value: HCLValue


class TerraformDataSource(BaseModel):
    terraform_type: str
    name: str
    file: AllowedOutputFile
    body: dict[str, HCLValue] = Field(default_factory=dict)


class TerraformManagedResource(BaseModel):
    terraform_type: str
    name: str
    file: AllowedOutputFile
    architecture_resource_id: str | None = None
    body: dict[str, HCLValue] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)


class TerraformOutput(BaseModel):
    name: str
    description: str = ""
    value: HCLValue
    sensitive: bool = False


class ArchitectureResourceMapping(BaseModel):
    architecture_resource_id: str
    provider_type: str
    mapping_status: MappingStatus
    terraform_addresses: list[str] = Field(default_factory=list)
    notes: str = ""


class ExternalDependency(BaseModel):
    architecture_resource_id: str
    provider_type: str
    name: str
    handling: str
    notes: str = ""


class DerivedResourceSpec(BaseModel):
    terraform_type: str
    name: str
    reason: str
    file: AllowedOutputFile | None = None


class TerraformResourcePlan(BaseModel):
    plan_version: str = "1.0.0"
    draft_pattern_name: str
    cloud_provider: str
    terraform_version: str = ">= 1.5.0"
    required_providers: list[ProviderRequirement] = Field(default_factory=list)
    deployment_targets: list[str] = Field(default_factory=list)
    variables: list[TerraformVariable] = Field(default_factory=list)
    locals: list[TerraformLocal] = Field(default_factory=list)
    data_sources: list[TerraformDataSource] = Field(default_factory=list)
    resources: list[TerraformManagedResource] = Field(default_factory=list)
    outputs: list[TerraformOutput] = Field(default_factory=list)
    architecture_resource_mappings: list[ArchitectureResourceMapping] = Field(default_factory=list)
    external_dependencies: list[ExternalDependency] = Field(default_factory=list)
    derived_resources: list[DerivedResourceSpec] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    runtime_risks: list[str] = Field(default_factory=list)
    validation_assertions: list[str] = Field(default_factory=list)


HCLValue.model_rebuild()
