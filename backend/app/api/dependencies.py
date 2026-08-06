from typing import Any

from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.errors import DatabaseUnavailableError
from app.repositories.architecture_version_repository import (
    ArchitectureVersionRepository,
)
from app.repositories.change_request_repository import ChangeRequestRepository
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.project_repository import ProjectRepository
from app.services.project_service import ProjectService
from app.services.version_service import VersionService


def get_database(request: Request) -> AsyncIOMotorDatabase[Any]:
    try:
        return request.app.state.database_manager.database
    except RuntimeError:
        raise DatabaseUnavailableError() from None


def get_project_service(
    database: AsyncIOMotorDatabase[Any] = Depends(get_database),
) -> ProjectService:
    return ProjectService(
        ProjectRepository(database),
        ArchitectureVersionRepository(database),
        ChatMessageRepository(database),
        ChangeRequestRepository(database),
    )


def get_version_service(
    database: AsyncIOMotorDatabase[Any] = Depends(get_database),
) -> VersionService:
    return VersionService(ArchitectureVersionRepository(database))
