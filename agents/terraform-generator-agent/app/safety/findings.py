from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


SafetySeverity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]

SafetyCode = Literal[
    "FORBIDDEN_COMMAND",
    "HARDCODED_AWS_KEY",
    "PUBLIC_RDS",
    "OPEN_DATABASE_PORT",
    "PLAINTEXT_DB_PASSWORD",
    "ADMIN_IAM",
    "WILDCARD_IAM",
    "PUBLIC_ECS_DIRECT_INGRESS",
    "S3_PUBLIC_ACCESS",
    "HTTP_ONLY_ALB",
    "SINGLE_AZ_RDS",
    "NO_ECS_LOGS",
    "UNKNOWN",
]


class SafetyFinding(BaseModel):
    severity: SafetySeverity
    code: str
    message: str
    file: str | None = None
    recommendation: str


class SafetyCheckResult(BaseModel):
    passed: bool
    has_critical: bool
    findings: list[SafetyFinding] = Field(default_factory=list)
