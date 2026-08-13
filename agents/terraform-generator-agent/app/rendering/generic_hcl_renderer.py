from __future__ import annotations

from collections import defaultdict

from app.planning.terraform_resource_plan_schema import (
    HCLValue,
    TerraformDataSource,
    TerraformManagedResource,
    TerraformOutput,
    TerraformResourcePlan,
)
from app.utils.hcl_safety import validate_artifact_path

from .file_splitter import group_blocks_by_file
from .hcl_value_renderer import render_hcl_value


class GenericHCLRenderer:
    def render(self, plan: TerraformResourcePlan) -> list[dict[str, str]]:
        plan_warnings = _dedupe(plan.warnings)
        plan = plan.model_copy(update={"warnings": plan_warnings})
        files: dict[str, str] = {}
        files["versions.tf"] = self._render_versions(plan)
        files["providers.tf"] = self._render_providers(plan)
        if plan.variables:
            files["variables.tf"] = self._render_variables(plan)
            files["terraform.tfvars.example"] = self._render_tfvars_example(plan)
        if plan.locals:
            files["locals.tf"] = self._render_locals(plan)

        blocks: list[tuple[str, str]] = []
        for ds in sorted(plan.data_sources, key=lambda i: (i.file, i.terraform_type, i.name)):
            blocks.append((ds.file, self._render_data_source(ds)))
        for resource in sorted(plan.resources, key=lambda i: (i.file, i.terraform_type, i.name)):
            blocks.append((resource.file, self._render_resource(resource)))
        if plan.outputs:
            files["outputs.tf"] = self._render_outputs(plan.outputs)
        grouped = group_blocks_by_file(blocks)
        for file, file_blocks in grouped.items():
            existing = files.get(file, "").strip()
            rendered = "\n\n".join(file_blocks).strip()
            if existing and rendered:
                files[file] = existing + "\n\n" + rendered
            elif rendered:
                files[file] = rendered

        files["README.generated.md"] = self._render_readme(plan)
        return [
            {"path": validate_artifact_path(path), "content": content.strip() + "\n"}
            for path, content in sorted(files.items())
            if content.strip()
        ]

    def _render_versions(self, plan: TerraformResourcePlan) -> str:
        providers = "\n".join(
            f'    {provider.name} = {{\n      source  = "{provider.source}"\n      version = "{provider.version}"\n    }}'
            for provider in plan.required_providers
        )
        body = f'terraform {{\n  required_version = "{plan.terraform_version}"'
        if providers:
            body += f"\n  required_providers {{\n{providers}\n  }}"
        body += "\n}"
        return body

    def _render_providers(self, plan: TerraformResourcePlan) -> str:
        chunks = []
        for provider in plan.required_providers:
            if provider.name == "aws":
                chunks.append('provider "aws" {\n  region = var.aws_region\n}')
            else:
                chunks.append(f'provider "{provider.name}" {{\n}}')
        return "\n\n".join(chunks)

    def _render_variables(self, plan: TerraformResourcePlan) -> str:
        parts = []
        for variable in sorted(plan.variables, key=lambda i: i.name):
            lines = [f'variable "{variable.name}" {{', f"  type        = {variable.type}"]
            if variable.description:
                lines.append(f'  description = "{variable.description.replace(chr(34), chr(92)+chr(34))}"')
            if variable.default is not None:
                lines.append(f"  default     = {render_hcl_value(variable.default, 2)}")
            if variable.sensitive:
                lines.append("  sensitive   = true")
            lines.append("}")
            parts.append("\n".join(lines))
        return "\n\n".join(parts)

    def _render_locals(self, plan: TerraformResourcePlan) -> str:
        body = "\n".join(
            f"  {local.name} = {render_hcl_value(local.value, 2)}"
            for local in sorted(plan.locals, key=lambda i: i.name)
        )
        return f"locals {{\n{body}\n}}"

    def _render_data_source(self, ds: TerraformDataSource) -> str:
        return self._render_block("data", ds.terraform_type, ds.name, ds.body)

    def _render_resource(self, resource: TerraformManagedResource) -> str:
        body = dict(resource.body)
        if resource.depends_on:
            body["depends_on"] = HCLValue(kind="list", items=[HCLValue(kind="expr", value=item) for item in resource.depends_on])
        return self._render_block("resource", resource.terraform_type, resource.name, body)

    def _render_outputs(self, outputs: list[TerraformOutput]) -> str:
        parts = []
        for output in sorted(outputs, key=lambda i: i.name):
            lines = [f'output "{output.name}" {{', f"  value       = {render_hcl_value(output.value, 2)}"]
            if output.description:
                lines.append(f'  description = "{output.description.replace(chr(34), chr(92)+chr(34))}"')
            if output.sensitive:
                lines.append("  sensitive   = true")
            lines.append("}")
            parts.append("\n".join(lines))
        return "\n\n".join(parts)

    def _render_tfvars_example(self, plan: TerraformResourcePlan) -> str:
        lines = []
        for variable in sorted([v for v in plan.variables if v.required], key=lambda i: i.name):
            placeholder = "<sensitive>" if variable.sensitive else "<value>"
            lines.append(f'{variable.name} = "{placeholder}"')
        return "\n".join(lines)

    def _render_readme(self, plan: TerraformResourcePlan) -> str:
        warnings = "\n".join(f"- {w}" for w in plan.warnings) or "- Review generated Terraform carefully."
        missing = "\n".join(f"- {i}" for i in plan.missing_inputs) or "- None"
        return (
            "# README.generated.md\n\n"
            "Draft Terraform generated from an LLM-planned resource plan. "
            "This architecture is not yet covered by a trusted Nimbus deterministic pattern.\n\n"
            "## Review carefully\n"
            f"{warnings}\n\n"
            "## Secret handling warning\n"
            "Terraform-managed secret values may be stored in Terraform state. Protect state carefully or inject secret values outside Terraform.\n\n"
            "## Missing inputs\n"
            f"{missing}\n"
        )

    def _render_block(
        self,
        block_kind: str,
        terraform_type: str,
        name: str,
        body: dict[str, HCLValue],
    ) -> str:
        lines = [f'{block_kind} "{terraform_type}" "{name}" {{']
        lines.extend(self._render_body(body, 2))
        lines.append("}")
        return "\n".join(lines)

    def _render_body(self, body: dict[str, HCLValue], indent: int) -> list[str]:
        lines: list[str] = []
        pad = " " * indent
        for key in sorted(body):
            value = body[key]
            if value.kind == "block":
                lines.append(f"{pad}{value.type} {{")
                lines.extend(self._render_body(value.body, indent + 2))
                lines.append(f"{pad}}}")
            elif value.kind == "list" and isinstance(value.items, list) and value.items and all(item.kind == "block" for item in value.items):
                for item in value.items:
                    lines.append(f"{pad}{item.type} {{")
                    lines.extend(self._render_body(item.body, indent + 2))
                    lines.append(f"{pad}}}")
            else:
                lines.append(f"{pad}{key} = {render_hcl_value(value, indent)}")
        return lines


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
