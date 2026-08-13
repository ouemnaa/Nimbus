from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.planning.terraform_resource_plan_schema import TerraformResourcePlan


class TerraformGenerationPlan(BaseModel):
    pattern_id: str
    generation_mode: str = "DETERMINISTIC_SUPPORTED"
    deployment_strategy: str | None = None
    project_name: str
    environment: str
    aws_region: str
    architecture_id: str
    architecture_version: str
    required_inputs: list[str] = Field(default_factory=list)
    resources: dict[str, Any] = Field(default_factory=dict)
    derived_resources: list[dict[str, Any]] = Field(default_factory=list)
    repairs: list[dict[str, str]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    runtime_risks: list[str] = Field(default_factory=list)
    validation_assertions: list[str] = Field(default_factory=list)
    safety_expectations: list[str] = Field(default_factory=list)
    template_set: list[str] = Field(default_factory=list)
    supported_resources: list[str] = Field(default_factory=list)
    unsupported_resources: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    terraform_resource_plan: TerraformResourcePlan | None = None

    def renderer_context(self) -> dict[str, Any]:
        ctx = {
            "pattern_id": self.pattern_id,
            "generation_mode": self.generation_mode,
            "deployment_strategy": self.deployment_strategy,
            "project_name": self.project_name,
            "environment": self.environment,
            "region": self.aws_region,
            "architecture_id": self.architecture_id,
            "architecture_version": self.architecture_version,
            "required_inputs": self.required_inputs,
            "resources": self.resources,
            "derived_resources": self.derived_resources,
            "repairs": self.repairs,
            "warnings": self.warnings,
            "runtime_risks": self.runtime_risks,
            "validation_assertions": self.validation_assertions,
            "terraform_resource_plan": self.terraform_resource_plan.model_dump() if self.terraform_resource_plan else None,
            **self.resources,
        }
        # Ensure assign_public_ip has a safe default if not set by plan builder
        ctx.setdefault("assign_public_ip", False)
        return ctx
