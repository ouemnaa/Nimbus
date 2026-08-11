from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


COLLECTION_NAME = "terraform_generations"


def build_terraform_generation_document(
    *,
    project_id: ObjectId,
    architecture_version_id: ObjectId,
    status: str,
    files: list[dict[str, str]],
    warnings: list[str],
    next_steps: list[str],
    metadata: dict[str, Any],
    supported_resources: list[str],
    unsupported_resources: list[str],
    derived_resources: list[dict[str, Any]],
    repairs: list[dict[str, Any]],
    error: str | None = None,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "projectId": project_id,
        "architectureVersionId": architecture_version_id,
        "status": status,
        "files": files,
        "warnings": warnings,
        "nextSteps": next_steps,
        "metadata": metadata,
        "supportedResources": supported_resources,
        "unsupportedResources": unsupported_resources,
        "derivedResources": derived_resources,
        "repairs": repairs,
        "error": error,
        "createdAt": now,
        "updatedAt": now,
    }
