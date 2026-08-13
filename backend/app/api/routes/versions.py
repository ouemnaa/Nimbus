from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_project_service, get_version_service
from app.schemas.architecture_version import ArchitectureVersionResponse
from app.schemas.workspace import ProjectWorkspaceResponse
from app.services.project_service import ProjectService
from app.services.version_service import VersionService
from app.utils.object_id import parse_object_id


router = APIRouter(prefix="/projects/{project_id}/versions", tags=["versions"])


class UpdateStatusRequest(BaseModel):
    status: str


@router.get("", response_model=list[ArchitectureVersionResponse])
async def list_project_versions(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> list[ArchitectureVersionResponse]:
    workspace = await service.get_workspace(parse_object_id(project_id, "project_id"))
    return workspace.versions


@router.get("/{version_id}", response_model=ArchitectureVersionResponse)
async def get_architecture_version(
    project_id: str,
    version_id: str,
    project_service: ProjectService = Depends(get_project_service),
    version_service: VersionService = Depends(get_version_service),
) -> ArchitectureVersionResponse:
    project_object_id = parse_object_id(project_id, "project_id")
    await project_service.get_workspace(project_object_id)
    version = await version_service.get(parse_object_id(version_id, "version_id"))
    if version.project_id != str(project_object_id):
        from app.core.errors import NotFoundError

        raise NotFoundError("Architecture version")
    return version


@router.patch("/{version_id}/status", response_model=ArchitectureVersionResponse)
async def update_version_status(
    project_id: str,
    version_id: str,
    request: UpdateStatusRequest,
    version_service: VersionService = Depends(get_version_service),
) -> ArchitectureVersionResponse:
    return await version_service.update_status(
        parse_object_id(version_id, "version_id"),
        request.status,
    )


@router.post("/{version_id}/accept", response_model=ProjectWorkspaceResponse)
async def accept_architecture_draft(
    project_id: str,
    version_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectWorkspaceResponse:
    return await service.accept_draft(
        parse_object_id(project_id, "project_id"),
        parse_object_id(version_id, "version_id"),
    )


@router.post("/{version_id}/discard", response_model=ProjectWorkspaceResponse)
async def discard_architecture_draft(
    project_id: str,
    version_id: str,
    service: ProjectService = Depends(get_project_service),
) -> ProjectWorkspaceResponse:
    return await service.discard_draft(
        parse_object_id(project_id, "project_id"),
        parse_object_id(version_id, "version_id"),
    )
