from pathlib import Path

from .hcl_safety import validate_artifact_path


def write_artifacts(files: list[dict[str, str]], output_dir: str, debug: bool = False) -> None:
    root = Path(output_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for artifact in files:
        relative = validate_artifact_path(artifact["path"])
        destination = (root / relative).resolve()
        if root not in destination.parents and destination != root:
            raise ValueError("Artifact path escapes the generated artifacts directory.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(artifact["content"], encoding="utf-8")


def ensure_directory(path: str) -> str:
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return str(root)
