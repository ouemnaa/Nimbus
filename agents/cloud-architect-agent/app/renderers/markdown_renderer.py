from jinja2 import Environment, FileSystemLoader
from ..schemas.architecture import ArchitectureSpecification
import os

class MarkdownRenderer:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template = self.env.get_template("architecture_report.md.j2")

    def render(self, architecture: ArchitectureSpecification, mermaid_diagram: str) -> str:
        data = architecture.model_dump()
        data["mermaid_diagram"] = mermaid_diagram
        return self.template.render(**data)
