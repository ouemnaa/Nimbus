from datetime import datetime
from typing import Any

from app.schemas.common import APIModel
from app.utils.object_id import stringify_object_id


class TerraformFileResponse(APIModel):
    path: str
    content: str


class TerraformGenerationResponse(APIModel):
    id: str
    project_id: str
    architecture_version_id: str
    status: str
    files: list[TerraformFileResponse]
    warnings: list[str]
    next_steps: list[str]
    metadata: dict[str, Any]
    supported_resources: list[str]
    unsupported_resources: list[str]
    derived_resources: list[dict[str, Any]]
    repairs: list[dict[str, Any]]
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(
        cls, document: dict[str, Any]
    ) -> "TerraformGenerationResponse":
        values = dict(document)
        values["id"] = stringify_object_id(values.pop("_id"))
        values["projectId"] = stringify_object_id(values.get("projectId"))
        values["architectureVersionId"] = stringify_object_id(
            values.get("architectureVersionId")
        )
        return cls.model_validate(values)
