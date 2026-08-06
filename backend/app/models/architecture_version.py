from datetime import datetime, timezone
from typing import Any

from bson import ObjectId


COLLECTION_NAME = "architecture_versions"


def build_architecture_version_document(
    *,
    project_id: ObjectId,
    version: str,
    status: str,
    architecture: dict[str, Any],
    report_markdown: str,
    simple_diagram_mermaid: str | None,
    advanced_diagram_mermaid: str | None,
    change_summary: list[str],
    metadata: dict[str, Any],
    parent_version_id: ObjectId | None = None,
) -> dict[str, Any]:
    return {
        "projectId": project_id,
        "version": version,
        "parentVersionId": parent_version_id,
        "status": status,
        "architecture": architecture,
        "reportMarkdown": report_markdown,
        "simpleDiagramMermaid": simple_diagram_mermaid,
        "advancedDiagramMermaid": advanced_diagram_mermaid,
        "changeSummary": change_summary,
        "metadata": metadata,
        "createdAt": datetime.now(timezone.utc),
    }
