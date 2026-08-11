from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    file: str | None = None
    issue: str
    recommendation: str


class TerraformReviewResult(BaseModel):
    review_status: Literal["PASSED", "NEEDS_FIX", "NEEDS_HUMAN_REVIEW", "SKIPPED", "FAILED"]
    trusted: bool = True
    critical_issues: list[ReviewIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    faithfulness_score: float = 1.0   # 0.0–1.0: does HCL match the architecture?
    deployability_score: float = 1.0  # 0.0–1.0: likelihood of successful deploy
