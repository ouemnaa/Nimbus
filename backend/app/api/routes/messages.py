from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_project_service
from app.schemas.chat_message import (
    ChatMessageResponse,
    ProjectMessageCreate,
    ProjectMessageResponse,
)
from app.services.project_service import ProjectService
from app.utils.object_id import parse_object_id


router = APIRouter(prefix="/projects/{project_id}/messages", tags=["messages"])


@router.get("", response_model=list[ChatMessageResponse])
async def list_project_messages(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
) -> list[ChatMessageResponse]:
    workspace = await service.get_workspace(parse_object_id(project_id, "project_id"))
    return workspace.messages


@router.post(
    "",
    response_model=ProjectMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_project_message(
    project_id: str,
    request: ProjectMessageCreate,
    service: ProjectService = Depends(get_project_service),
) -> ProjectMessageResponse:
    return await service.send_message(
        parse_object_id(project_id, "project_id"),
        request,
    )
