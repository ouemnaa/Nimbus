from pydantic import BaseModel, Field


class ValidationCheck(BaseModel):
    name: str
    status: str
    command: str
    stdout: str = ""
    stderr: str = ""
    return_code: int | None = None


class ValidationResponse(BaseModel):
    validation_status: str
    checks: list[ValidationCheck] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
