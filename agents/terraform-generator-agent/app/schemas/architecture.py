from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CloudConfig(BaseModel):
    model_config = ConfigDict(extra="allow")
    provider: str = "aws"
    region: str | None = None


class ArchitectureResource(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str | None = None
    provider_type: str
    category: str | None = None
    scope: str | None = None
    configuration: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def accept_common_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        value = dict(value)
        value.setdefault("id", value.get("logical_id") or value.get("resource_id") or value.get("name"))
        value.setdefault("provider_type", value.get("type") or value.get("resource_type"))
        value.setdefault("configuration", value.get("config") or value.get("properties") or {})
        return value


class CanonicalArchitecture(BaseModel):
    model_config = ConfigDict(extra="allow")
    schema_version: str | None = None
    architecture_id: str = "architecture"
    architecture_version: str = "1.0.0"
    status: str | None = None
    title: str | None = None
    requirement_summary: str | dict[str, Any] | None = None
    cloud: CloudConfig = Field(default_factory=CloudConfig)
    resources: list[ArchitectureResource] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def accept_resource_map(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        value = dict(value)
        resources = value.get("resources", [])
        if isinstance(resources, dict):
            value["resources"] = [
                {"id": key, **(item if isinstance(item, dict) else {"configuration": {"value": item}})}
                for key, item in resources.items()
            ]
        return value

    def provider(self) -> str:
        return (self.cloud.provider or "aws").lower()

    def region(self, default: str) -> str:
        return self.cloud.region or default


class GenerateOptions(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)
    project_name: str | None = None
    environment: str | None = None
    aws_region: str | None = None
    allow_repairs: bool = True
    validate_output: bool = Field(default=False, alias="validate")


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    project_id: str | None = None
    architecture_version_id: str | None = None
    architecture_id: str | None = None
    architecture_version: str | None = None
    architecture: dict[str, Any] = Field(default_factory=dict)
    options: GenerateOptions = Field(default_factory=GenerateOptions)

    def canonical_architecture(self) -> CanonicalArchitecture:
        payload = self.architecture or self.model_dump(exclude={"architecture", "options"}, exclude_none=True)
        if not payload.get("architecture_id") and self.architecture_id:
            payload["architecture_id"] = self.architecture_id
        if not payload.get("architecture_version") and self.architecture_version:
            payload["architecture_version"] = self.architecture_version
        return CanonicalArchitecture.model_validate(payload)


class FileArtifact(BaseModel):
    path: str
    content: str


class ValidateOptions(BaseModel):
    model_config = ConfigDict(extra="allow")
    enable_init: bool | None = None
    enable_plan: bool = False
    debug: bool = False


class ValidateRequest(BaseModel):
    files: list[FileArtifact]
    options: ValidateOptions = Field(default_factory=ValidateOptions)


class GenerateAndValidateRequest(GenerateRequest):
    options: GenerateOptions = Field(default_factory=GenerateOptions)
