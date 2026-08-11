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


class GenerationResponse(BaseModel):
    generation_status: str
    target: str = "terraform"
    supported_resources: list[str] = Field(default_factory=list)
    unsupported_resources: list[str] = Field(default_factory=list)
    files: list[FileArtifact] = Field(default_factory=list)
    derived_resources: list[DerivedResource] = Field(default_factory=list)
    repairs: list[RepairRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    metadata: GenerationMetadata
    error: str | None = None


class CombinedResponse(BaseModel):
    generation: GenerationResponse
    validation: Any
