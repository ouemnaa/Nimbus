from fastapi import APIRouter, Depends

from app.api.dependencies import get_project_service
from app.schemas.chat_message import ChatMessageResponse
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
