from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class NetworkingStrategy(BaseModel):
    ecs_subnets: Literal["public", "private"] | None = None
    ecs_assign_public_ip: bool | None = None
    rds_subnets: Literal["public", "private"] | None = None
    rds_publicly_accessible: bool = False
    nat_gateway_required: bool = False
    vpc_endpoints_required: bool = False
    vpc_endpoint_services: list[str] = Field(default_factory=list)


class TerraformReasoningResult(BaseModel):
    reasoning_status: Literal["SUCCESS", "NEEDS_INPUT", "UNSUPPORTED", "FAILED"] = "SUCCESS"
    pattern_id: str | None = None
    deployment_strategy: str | None = None
    terraform_strategy_summary: str = ""
    required_resources: list[str] = Field(default_factory=list)
    derived_resources: list[dict] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    repairs: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    runtime_risks: list[str] = Field(default_factory=list)
    validation_assertions: list[str] = Field(default_factory=list)
    unsupported_reasons: list[str] = Field(default_factory=list)
    networking_strategy: NetworkingStrategy | None = None
