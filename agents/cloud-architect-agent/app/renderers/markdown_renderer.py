import os
from enum import Enum
from jinja2 import Environment, FileSystemLoader
from ..schemas.architecture import ArchitectureSpecification, DiagramVisibility


def format_enum_label(value: object) -> str:
    raw = value.value if isinstance(value, Enum) else str(value)
    raw = raw.split(".")[-1]
    return raw.replace("_", " ").strip().title()


class MarkdownRenderer:
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir), trim_blocks=True, lstrip_blocks=True)
        self.template = self.env.get_template("architecture_report.md.j2")

    def render(self, architecture: ArchitectureSpecification, diagrams: dict[str, str]) -> str:
        context = {
            "title": architecture.title,
            "requirement_summary": architecture.requirement_summary,
            "solution": architecture.solution,
            "simple_diagram": diagrams["simple"],
            "advanced_diagram": diagrams["advanced"],
            "decisions": [
                {
                    "title": decision.title,
                    "decision": decision.decision,
                    "rationale": decision.rationale,
                    "alternatives_considered": [
                        {
                            "option": alternative.option,
                            "reason_not_selected": alternative.reason_not_selected,
                        }
                        for alternative in decision.alternatives_considered
                    ],
                }
                for decision in architecture.decisions
            ],
            "resources": [
                {
                    "name": resource.name,
                    "category": format_enum_label(resource.category),
                    "purpose": resource.purpose,
                    "diagram_visibility": format_enum_label(resource.diagram_visibility),
                }
                for resource in architecture.resources
                if resource.diagram_visibility != DiagramVisibility.HIDDEN
            ],
            "security_considerations": architecture.security_considerations,
            "cost_profile": architecture.cost_profile,
            "reliability_and_scalability": architecture.reliability_considerations + architecture.scalability_considerations,
            "assumptions": architecture.assumptions,
            "open_questions": architecture.open_questions,
            "risks": [
                {
                    "title": risk.title,
                    "severity": format_enum_label(risk.severity),
                    "mitigation": risk.mitigation,
                }
                for risk in architecture.risks
            ],
            "status": format_enum_label(architecture.status),
            "architecture_id": architecture.architecture_id,
            "architecture_version": architecture.architecture_version,
        }
        return self.template.render(**context)
