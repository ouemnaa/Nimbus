from typing import Any

from bson import ObjectId

from app.core.errors import NotFoundError
from app.models.terraform_generation import build_terraform_generation_document
from app.repositories.architecture_version_repository import (
    ArchitectureVersionRepository,
)
from app.repositories.project_repository import ProjectRepository
from app.repositories.terraform_generation_repository import (
    TerraformGenerationRepository,
)
from app.schemas.terraform_generation import TerraformGenerationResponse
from app.services.terraform_client import TerraformGeneratorAgentClient


class TerraformService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        version_repository: ArchitectureVersionRepository,
        generation_repository: TerraformGenerationRepository,
        terraform_client: TerraformGeneratorAgentClient | None = None,
    ) -> None:
        self.projects = project_repository
        self.versions = version_repository
        self.generations = generation_repository
        self.terraform_client = terraform_client or TerraformGeneratorAgentClient()

    async def generate_for_project(
        self, project_id: ObjectId
    ) -> TerraformGenerationResponse:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project")

        current_version_id = project.get("currentVersionId")
        if current_version_id is None:
            raise NotFoundError("Current architecture version")

        version = await self.versions.get_by_id(current_version_id)
        if version is None:
            raise NotFoundError("Current architecture version")

        architecture = dict(version["architecture"])
        architecture.setdefault("architecture_version", version["version"])
        context = project.get("context", {})
        cloud = architecture.get("cloud", {})
        options: dict[str, Any] = {
            "project_name": project.get("slug") or project.get("title"),
            "environment": context.get("environment", "development"),
            "aws_region": cloud.get("region"),
            "allow_repairs": True,
            "validate": False,
        }

        result = await self.terraform_client.generate(
            project_id=str(project_id),
            architecture_version_id=str(current_version_id),
            architecture=architecture,
            options=options,
        )
        document = build_terraform_generation_document(
            project_id=project_id,
            architecture_version_id=current_version_id,
            status=result.status,
            files=result.files,
            warnings=result.warnings,
            next_steps=result.next_steps,
            metadata=result.metadata,
            supported_resources=result.supported_resources,
            unsupported_resources=result.unsupported_resources,
            derived_resources=result.derived_resources,
            repairs=result.repairs,
            error=result.error,
        )
        return TerraformGenerationResponse.from_document(
            await self.generations.create(document)
        )

    async def latest_for_project(
        self, project_id: ObjectId
    ) -> TerraformGenerationResponse | None:
        if await self.projects.get_by_id(project_id) is None:
            raise NotFoundError("Project")
        document = await self.generations.latest_for_project(project_id)
        return TerraformGenerationResponse.from_document(document) if document else None
