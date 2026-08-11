from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_terraform_service
from app.schemas.terraform_generation import TerraformGenerationResponse
from app.services.terraform_service import TerraformService
from app.utils.object_id import parse_object_id


router = APIRouter(prefix="/projects/{project_id}/terraform", tags=["terraform"])


@router.post(
    "/generate",
    response_model=TerraformGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_terraform(
    project_id: str,
    service: TerraformService = Depends(get_terraform_service),
) -> TerraformGenerationResponse:
    return await service.generate_for_project(
        parse_object_id(project_id, "project_id")
    )


@router.get("/latest", response_model=TerraformGenerationResponse | None)
async def get_latest_terraform_generation(
    project_id: str,
    service: TerraformService = Depends(get_terraform_service),
) -> TerraformGenerationResponse | Response:
    result = await service.latest_for_project(
        parse_object_id(project_id, "project_id")
    )
    if result is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return result
