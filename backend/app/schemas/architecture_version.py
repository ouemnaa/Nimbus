from datetime import datetime
from typing import Any

from app.schemas.common import APIModel, ProjectStatus
from app.utils.object_id import stringify_object_id


class ArchitectureVersionResponse(APIModel):
    id: str
    project_id: str
    version: str
    parent_version_id: str | None
    status: ProjectStatus
    architecture: dict[str, Any]
    report_markdown: str
    simple_diagram_mermaid: str | None
    advanced_diagram_mermaid: str | None
    change_summary: list[str]
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_document(
        cls, document: dict[str, Any]
    ) -> "ArchitectureVersionResponse":
        values = dict(document)
        values["id"] = stringify_object_id(values.pop("_id"))
        values["projectId"] = stringify_object_id(values.get("projectId"))
        values["parentVersionId"] = stringify_object_id(
            values.get("parentVersionId")
        )
        return cls.model_validate(values)
