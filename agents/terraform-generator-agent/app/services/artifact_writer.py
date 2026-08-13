from pathlib import Path

from app.utils.file_utils import ensure_directory, write_artifacts
from app.utils.naming import safe_name


class ArtifactWriter:
    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir

    def write(
        self,
        files: list[dict[str, str]],
        *,
        project_id: str | None = None,
        architecture_id: str | None = None,
        architecture_version_id: str | None = None,
        architecture_version: str | None = None,
    ) -> str:
        target_dir = self._target_dir(
            project_id=project_id,
            architecture_id=architecture_id,
            architecture_version_id=architecture_version_id,
            architecture_version=architecture_version,
        )
        write_artifacts(files, target_dir)
        return ensure_directory(target_dir)

    def _target_dir(
        self,
        *,
        project_id: str | None,
        architecture_id: str | None,
        architecture_version_id: str | None,
        architecture_version: str | None,
    ) -> str:
        root = Path(self.output_dir)
        if project_id:
            project_segment = safe_name(project_id, "project")
            version_segment = safe_name(architecture_version_id or architecture_version or "latest", "latest")
            return str(root / "projects" / project_segment / "versions" / version_segment)
        architecture_segment = safe_name(architecture_id or "architecture", "architecture")
        version_segment = safe_name(architecture_version or "latest", "latest")
        return str(root / "architectures" / architecture_segment / "versions" / version_segment)
