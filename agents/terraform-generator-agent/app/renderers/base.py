from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined


class BaseRenderer:
    def __init__(self, template_dir: str | None = None) -> None:
        root = Path(template_dir or Path(__file__).resolve().parents[1] / "templates")
        self.environment = Environment(
            loader=FileSystemLoader(str(root)),
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    def render(self, template: str, context: dict[str, Any]) -> str:
        return self.environment.get_template(template).render(**context).strip() + "\n"
