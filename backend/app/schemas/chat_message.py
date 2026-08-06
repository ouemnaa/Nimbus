from datetime import datetime
from typing import Any

from app.schemas.common import APIModel, ChatIntent, ChatRole
from app.utils.object_id import stringify_object_id


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
