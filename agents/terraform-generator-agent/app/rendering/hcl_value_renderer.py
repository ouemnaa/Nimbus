from __future__ import annotations

from app.planning.terraform_resource_plan_schema import HCLValue
from app.utils.hcl_safety import safe_hcl_string


def render_hcl_value(value: HCLValue, indent: int = 0) -> str:
    if value.kind == "expr":
        return str(value.value)
    if value.kind == "literal":
        if isinstance(value.value, bool):
            return "true" if value.value else "false"
        if value.value is None:
            return "null"
        if isinstance(value.value, (int, float)):
            return str(value.value)
        return safe_hcl_string(value.value)
    if value.kind == "list":
        items = value.items if isinstance(value.items, list) else []
        if not items:
            return "[]"
        pad = " " * indent
        inner = " " * (indent + 2)
        rendered = ",\n".join(f"{inner}{render_hcl_value(item, indent + 2)}" for item in items)
        return f"[\n{rendered}\n{pad}]"
    if value.kind == "object":
        items = value.items if isinstance(value.items, dict) else {}
        if not items:
            return "{}"
        pad = " " * indent
        inner = " " * (indent + 2)
        rendered = "\n".join(
            f"{inner}{key} = {render_hcl_value(items[key], indent + 2)}"
            for key in sorted(items)
        )
        return f"{{\n{rendered}\n{pad}}}"
    raise ValueError("block values must be rendered by block renderer")
