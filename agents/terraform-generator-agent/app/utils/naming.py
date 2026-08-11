import re


def safe_identifier(value: str, fallback: str = "resource") -> str:
    text = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or ""))
    text = re.sub(r"_+", "_", text).strip("_").lower()
    if not text:
        text = fallback
    if text[0].isdigit():
        text = f"r_{text}"
    return text


def safe_name(value: str, fallback: str = "nimbus") -> str:
    text = re.sub(r"[^A-Za-z0-9-]+", "-", str(value or ""))
    text = re.sub(r"-+", "-", text).strip("-").lower()
    return text or fallback


def resource_label(resource_id: str, resource_name: str | None = None) -> str:
    return safe_identifier(resource_name or resource_id)
