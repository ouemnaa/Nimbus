from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


COLLECTION_NAME = "chat_messages"


def build_chat_message_document(
    *,
    project_id: ObjectId,
    architecture_version_id: ObjectId | None,
    role: str,
    content: str,
    intent: str,
    architecture_changed: bool,
) -> dict[str, Any]:
    return {
        "projectId": project_id,
        "architectureVersionId": architecture_version_id,
        "role": role,
        "content": content,
        "intent": intent,
        "architectureChanged": architecture_changed,
        "createdAt": datetime.now(timezone.utc),
    }
