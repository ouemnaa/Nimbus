from app.schemas.architecture_version import ArchitectureVersionResponse
from app.schemas.chat_message import ChatMessageResponse
from app.schemas.common import APIModel
from app.schemas.project import ProjectResponse


class ProjectWorkspaceResponse(APIModel):
    project: ProjectResponse
    current_version: ArchitectureVersionResponse | None
    versions: list[ArchitectureVersionResponse]
    messages: list[ChatMessageResponse]
