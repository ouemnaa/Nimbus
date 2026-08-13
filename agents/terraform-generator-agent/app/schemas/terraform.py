from typing import Any

from pydantic import BaseModel, Field

from .architecture import FileArtifact


class DerivedResource(BaseModel):
    type: str
    name: str
    derived_from: str | None = None
    reason: str


class RepairRecord(BaseModel):
    path: str
    action: str
    reason: str
    result: str


class GenerationMetadata(BaseModel):
    generator_version: str
    generated_file_count: int
    llm_provider: str
    architecture_id: str
    architecture_version: str
    reasoning_enabled: bool = False
    reviewer_enabled: bool = False
    draft_fallback_enabled: bool = False


class CoverageFinding(BaseModel):
    code: str
    severity: str
    architecture_resource_id: str | None = None
    relationship_id: str | None = None
    expected: str
    actual: str
    recommendation: str


class GenerationResponse(BaseModel):
    generation_status: str
    generation_mode: str = "DETERMINISTIC_SUPPORTED"
    trusted: bool = True
    requires_human_review: bool = False
    target: str = "terraform"
    pattern_id: str | None = None
    draft_pattern_name: str | None = None
    draft_pattern_guess: str | None = None
    deployment_strategy: str | None = None
    supported_resources: list[str] = Field(default_factory=list)
    unsupported_resources: list[str] = Field(default_factory=list)
    files: list[FileArtifact] = Field(default_factory=list)
    derived_resources: list[DerivedResource] = Field(default_factory=list)
    repairs: list[RepairRecord] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    runtime_risks: list[str] = Field(default_factory=list)
    validation_assertions: list[str] = Field(default_factory=list)
    terraform_resource_plan: dict[str, Any] | None = None
    architecture_resource_mappings: list[dict[str, Any]] = Field(default_factory=list)
    external_dependencies: list[dict[str, Any]] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    validation: dict[str, Any] | None = None
    coverage_findings: list[CoverageFinding] = Field(default_factory=list)
    safety_findings: list[dict[str, Any]] = Field(default_factory=list)
    reasoning: dict[str, Any] | None = None
    review: dict[str, Any] | None = None
    next_steps: list[str] = Field(default_factory=list)
    metadata: GenerationMetadata
    error: str | None = None


class CombinedResponse(BaseModel):
    generation: GenerationResponse
    validation: Any
