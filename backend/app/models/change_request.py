from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


COLLECTION_NAME = "change_requests"


def build_change_request_document(
    *,
    project_id: ObjectId,
    from_version_id: ObjectId,
    user_message: str,
    change_summary: list[str],
    to_version_id: ObjectId | None = None,
    status: str = "pending",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "projectId": project_id,
        "fromVersionId": from_version_id,
        "toVersionId": to_version_id,
        "userMessage": user_message,
        "changeSummary": change_summary,
        "status": status,
        "createdAt": now,
        "updatedAt": now,
    }
