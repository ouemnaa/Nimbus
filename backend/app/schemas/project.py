from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.common import APIModel, ProjectStatus
from app.utils.object_id import stringify_object_id


class ProjectContext(APIModel):
    environment: str
    budget_preference: str
    cloud: str


class MockProjectCreate(APIModel):
    title: str = Field(min_length=1, max_length=200)
    requirement: str = Field(min_length=1, max_length=20_000)
    context: ProjectContext


class ProjectCreate(APIModel):
    requirement: str = Field(min_length=1, max_length=20_000)
    context: ProjectContext

    @field_validator("requirement")
    @classmethod
    def validate_requirement(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Requirement must not be empty.")
        return stripped


class ProjectResponse(APIModel):
    id: str
    title: str
    slug: str
    initial_requirement: str
    context: dict[str, Any]
    current_version_id: str | None
    status: ProjectStatus
    user_id: str | None
    current_version: str | None = None
    resource_count: int = 0
    has_terraform_generation: bool = False
    latest_terraform_status: str | None = None
    latest_terraform_updated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ProjectResponse":
        values = dict(document)
        values["id"] = stringify_object_id(values.pop("_id"))
        values["currentVersionId"] = stringify_object_id(
            values.get("currentVersionId")
        )
        values["userId"] = stringify_object_id(values.get("userId"))
        return cls.model_validate(values)
