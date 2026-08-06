from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_project_service
from app.schemas.project import MockProjectCreate, ProjectCreate, ProjectResponse
from app.schemas.workspace import ProjectWorkspaceResponse
from app.services.project_service import ProjectService
from app.utils.object_id import parse_object_id


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
    return await service.list_projects()


@router.post(
    "",
    response_model=ProjectWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    request: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
) -> ProjectWorkspaceResponse:
    return await service.create_project(request)


@router.get("/{project_id}", response_model=ProjectWorkspaceResponse)
async def get_project_workspace(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectWorkspaceResponse:
    return await service.get_workspace(parse_object_id(project_id, "project_id"))


@router.post(
    "/mock",
    response_model=ProjectWorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mock_project(
    request: MockProjectCreate,
    service: ProjectService = Depends(get_project_service),
) -> ProjectWorkspaceResponse:
    return await service.create_mock_project(request)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> Response:
    await service.delete_project(parse_object_id(project_id, "project_id"))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
