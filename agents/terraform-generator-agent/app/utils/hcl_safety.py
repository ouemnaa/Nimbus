import re
from pathlib import PurePosixPath


UNSAFE_COMMANDS = {"apply", "destroy", "import", "state", "force-unlock"}


def validate_artifact_path(path: str) -> str:
    if not path or "\\" in path:
        raise ValueError("Artifact paths must be non-empty POSIX relative paths.")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Unsafe artifact path: {path}")
    if str(pure) != path or any(not part for part in pure.parts):
        raise ValueError(f"Unsafe artifact path: {path}")
    return path


def safe_hcl_string(value: object) -> str:
    """Return a quoted HCL string for values that must be literals."""
    text = str(value if value is not None else "")
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def contains_forbidden_terraform_command(command: list[str]) -> bool:
    return any(part.lower() in UNSAFE_COMMANDS for part in command)


def is_fake_aws_id(value: object, prefix: str) -> bool:
    return bool(re.fullmatch(rf"{re.escape(prefix)}-[A-Za-z0-9_-]+", str(value or "")))
