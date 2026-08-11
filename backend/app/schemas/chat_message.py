from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.architecture_version import ArchitectureVersionResponse
from app.schemas.change_request import ChangeRequestResponse
from app.schemas.common import APIModel, ChatIntent, ChatRole
from app.schemas.project import ProjectResponse
from app.utils.object_id import stringify_object_id


class ProjectMessageCreate(APIModel):
    message: str = Field(min_length=1, max_length=20_000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty.")
        return stripped


class ChatMessageResponse(APIModel):
    id: str
    project_id: str
    architecture_version_id: str | None
    role: ChatRole
    content: str
    intent: ChatIntent
    architecture_changed: bool
    created_at: datetime

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ChatMessageResponse":
        values = dict(document)
        values["id"] = stringify_object_id(values.pop("_id"))
        values["projectId"] = stringify_object_id(values.get("projectId"))
        values["architectureVersionId"] = stringify_object_id(
            values.get("architectureVersionId")
        )
        return cls.model_validate(values)


class ProjectMessageResponse(APIModel):
    intent: ChatIntent
    architecture_changed: bool
    answer: str
    messages: list[ChatMessageResponse]
    project: ProjectResponse | None = None
    current_version: ArchitectureVersionResponse | None = None
    draft_version: ArchitectureVersionResponse | None = None
    change_request: ChangeRequestResponse | None = None
    change_summary: list[str] = Field(default_factory=list)
