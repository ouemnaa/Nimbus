from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LLMDraftFile(BaseModel):
    path: str
    content: str


class LLMDraftResult(BaseModel):
    draft_status: Literal["SUCCESS", "FAILED"]
    files: list[LLMDraftFile] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    validation_assertions: list[str] = Field(default_factory=list)
    unsupported_limitations: list[str] = Field(default_factory=list)
    explanation: str = ""
    error: str | None = None
