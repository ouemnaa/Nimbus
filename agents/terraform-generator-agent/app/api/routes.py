from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.schemas.architecture import GenerateRequest, ValidateRequest, ValidateOptions
from app.schemas.terraform import CombinedResponse
from app.services.generator_service import TerraformGeneratorService
from app.services.validator_service import TerraformValidatorService

router = APIRouter(prefix="/api/v1/terraform", tags=["terraform"])
_settings = get_settings()
_generator = TerraformGeneratorService(_settings)
_validator = TerraformValidatorService(_settings)


def _request_from_payload(payload: dict[str, Any]) -> GenerateRequest:
    if "architecture" in payload:
        return GenerateRequest.model_validate(payload)
    return GenerateRequest.model_validate({
        "architecture_id": payload.get("architecture_id"),
        "architecture_version": payload.get("architecture_version"),
        "architecture": payload,
        "options": payload.get("options", {}),
    })


@router.post("/generate")
async def generate_terraform(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        request = _request_from_payload(payload)
        architecture = request.canonical_architecture()
        response = await run_in_threadpool(_generator.generate, architecture, request.options)
        return response.model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to generate Terraform: {type(exc).__name__}: {exc}") from exc


@router.post("/validate")
async def validate_terraform(request: ValidateRequest) -> dict[str, Any]:
    response = await run_in_threadpool(_validator.validate, request.files, request.options)
    return response.model_dump(mode="json")


@router.post("/generate-and-validate", response_model=CombinedResponse)
async def generate_and_validate(payload: dict[str, Any]) -> dict[str, Any]:
    request = _request_from_payload(payload)
    architecture = request.canonical_architecture()
    generation = await run_in_threadpool(_generator.generate, architecture, request.options)
    validate_options_payload = request.options.model_extra or {}
    validation_options = ValidateOptions(
        enable_init=validate_options_payload.get("enable_init"),
        enable_plan=bool(validate_options_payload.get("enable_plan", False)),
        debug=bool(validate_options_payload.get("debug", False)),
    )
    validation = await run_in_threadpool(_validator.validate, generation.files, validation_options)
    return {"generation": generation.model_dump(mode="json"), "validation": validation.model_dump(mode="json")}
