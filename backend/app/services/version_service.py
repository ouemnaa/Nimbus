from bson import ObjectId

from app.core.errors import NotFoundError
from app.repositories.architecture_version_repository import (
    ArchitectureVersionRepository,
)
from app.schemas.architecture_version import ArchitectureVersionResponse


class VersionService:
    def __init__(self, repository: ArchitectureVersionRepository) -> None:
        self.repository = repository

    async def list_for_project(
        self, project_id: ObjectId
    ) -> list[ArchitectureVersionResponse]:
        documents = await self.repository.list_for_project(project_id)
        return [ArchitectureVersionResponse.from_document(item) for item in documents]

    async def get(self, version_id: ObjectId) -> ArchitectureVersionResponse:
        document = await self.repository.get_by_id(version_id)
        if document is None:
            raise NotFoundError("Architecture version")
        return ArchitectureVersionResponse.from_document(document)
