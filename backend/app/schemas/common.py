from enum import Enum

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )


class ProjectStatus(str, Enum):
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    DRAFT_REVISION = "DRAFT_REVISION"
    APPROVED = "APPROVED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    UNSUPPORTED = "UNSUPPORTED"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatIntent(str, Enum):
    INITIAL = "INITIAL"
    EXPLAIN = "EXPLAIN"
    MODIFY = "MODIFY"
    CLARIFY = "CLARIFY"
    UNSUPPORTED = "UNSUPPORTED"
    SYSTEM = "SYSTEM"


class ChangeRequestStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DISCARDED = "discarded"
