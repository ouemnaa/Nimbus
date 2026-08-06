from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import APIModel, ChangeRequestStatus
from app.utils.object_id import stringify_object_id


class ChangeRequestResponse(APIModel):
    id: str
    project_id: str
    from_version_id: str
    to_version_id: str | None
    user_message: str
    change_summary: list[str]
    status: ChangeRequestStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ChangeRequestResponse":
        values = dict(document)
        values["id"] = stringify_object_id(values.pop("_id"))
        values["projectId"] = stringify_object_id(values.get("projectId"))
        values["fromVersionId"] = stringify_object_id(values.get("fromVersionId"))
        values["toVersionId"] = stringify_object_id(values.get("toVersionId"))
        return cls.model_validate(values)


class ChangeRequestCreate(APIModel):
    from_version_id: str
    user_message: str
    change_summary: list[str] = Field(default_factory=list)
