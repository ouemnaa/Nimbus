from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


COLLECTION_NAME = "projects"


def build_project_document(
    *,
    title: str,
    slug: str,
    initial_requirement: str,
    context: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "title": title,
        "slug": slug,
        "initialRequirement": initial_requirement,
        "context": context,
        "currentVersionId": None,
        "status": status,
        "userId": None,
        "createdAt": now,
        "updatedAt": now,
    }


def set_current_version_update(version_id: ObjectId, status: str) -> dict[str, Any]:
    return {
        "$set": {
            "currentVersionId": version_id,
            "status": status,
            "updatedAt": datetime.now(timezone.utc),
        }
    }
