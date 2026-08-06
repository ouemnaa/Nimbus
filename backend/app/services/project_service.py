import asyncio
from typing import Any

from bson import ObjectId

from app.core.errors import NotFoundError
from app.models.architecture_version import build_architecture_version_document
from app.models.chat_message import build_chat_message_document
from app.models.project import build_project_document
from app.repositories.architecture_version_repository import (
    ArchitectureVersionRepository,
)
from app.repositories.change_request_repository import ChangeRequestRepository
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.architecture_version import ArchitectureVersionResponse
from app.schemas.chat_message import ChatMessageResponse
from app.schemas.common import ChatIntent, ChatRole, ProjectStatus
from app.schemas.project import MockProjectCreate, ProjectResponse
from app.schemas.workspace import ProjectWorkspaceResponse
from app.utils.slug import slugify


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        version_repository: ArchitectureVersionRepository,
        message_repository: ChatMessageRepository,
        change_request_repository: ChangeRequestRepository,
    ) -> None:
        self.projects = project_repository
        self.versions = version_repository
        self.messages = message_repository
        self.change_requests = change_request_repository

    async def list_projects(self) -> list[ProjectResponse]:
        documents = await self.projects.list_all()
        return [ProjectResponse.from_document(item) for item in documents]

    async def get_workspace(self, project_id: ObjectId) -> ProjectWorkspaceResponse:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project")

        versions, messages = await asyncio.gather(
            self.versions.list_for_project(project_id),
            self.messages.list_for_project(project_id),
        )
        return self._workspace_from_documents(project, versions, messages)

    async def create_mock_project(
        self, request: MockProjectCreate
    ) -> ProjectWorkspaceResponse:
        slug = await self._unique_slug(request.title)
        project_document = build_project_document(
            title=request.title,
            slug=slug,
            initial_requirement=request.requirement,
            context=request.context.model_dump(by_alias=True),
            status=ProjectStatus.READY_FOR_REVIEW.value,
        )
        project = await self.projects.create(project_document)
        project_id = project["_id"]

        try:
            architecture = self._mock_architecture(request)
            version_document = build_architecture_version_document(
                project_id=project_id,
                version="1.0.0",
                status=ProjectStatus.READY_FOR_REVIEW.value,
                architecture=architecture,
                report_markdown=self._mock_report(request),
                simple_diagram_mermaid=self._mock_simple_diagram(),
                advanced_diagram_mermaid=self._mock_advanced_diagram(),
                change_summary=["Created the initial architecture."],
                metadata={
                    "provider": "mock",
                    "model": "backend-development-fixture",
                    "generationDurationMs": 0,
                },
            )
            version = await self.versions.create(version_document)
            version_id = version["_id"]

            project = await self.projects.set_current_version(
                project_id,
                version_id,
                ProjectStatus.READY_FOR_REVIEW.value,
            )
            if project is None:
                raise NotFoundError("Project")

            user_message = await self.messages.create(
                build_chat_message_document(
                    project_id=project_id,
                    architecture_version_id=None,
                    role=ChatRole.USER.value,
                    content=request.requirement,
                    intent=ChatIntent.INITIAL.value,
                    architecture_changed=False,
                )
            )
            assistant_message = await self.messages.create(
                build_chat_message_document(
                    project_id=project_id,
                    architecture_version_id=version_id,
                    role=ChatRole.ASSISTANT.value,
                    content="The initial architecture has been created and is ready for review.",
                    intent=ChatIntent.SYSTEM.value,
                    architecture_changed=True,
                )
            )
        except Exception:
            await self._delete_related(project_id)
            await self.projects.delete(project_id)
            raise

        return self._workspace_from_documents(
            project, [version], [user_message, assistant_message]
        )

    async def delete_project(self, project_id: ObjectId) -> None:
        if await self.projects.get_by_id(project_id) is None:
            raise NotFoundError("Project")
        await self._delete_related(project_id)
        await self.projects.delete(project_id)

    async def _delete_related(self, project_id: ObjectId) -> None:
        await asyncio.gather(
            self.versions.delete_for_project(project_id),
            self.messages.delete_for_project(project_id),
            self.change_requests.delete_for_project(project_id),
        )

    async def _unique_slug(self, title: str) -> str:
        base = slugify(title)
        candidate = base
        suffix = 2
        while await self.projects.get_by_slug(candidate) is not None:
            candidate = f"{base}-{suffix}"
            suffix += 1
        return candidate

    @staticmethod
    def _workspace_from_documents(
        project: dict[str, Any],
        versions: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ) -> ProjectWorkspaceResponse:
        current_version_id = project.get("currentVersionId")
        current_document = next(
            (item for item in versions if item.get("_id") == current_version_id), None
        )
        return ProjectWorkspaceResponse(
            project=ProjectResponse.from_document(project),
            current_version=(
                ArchitectureVersionResponse.from_document(current_document)
                if current_document
                else None
            ),
            versions=[
                ArchitectureVersionResponse.from_document(item) for item in versions
            ],
            messages=[ChatMessageResponse.from_document(item) for item in messages],
        )

    @staticmethod
    def _mock_architecture(request: MockProjectCreate) -> dict[str, Any]:
        return {
            "architectureId": "mock-development-architecture",
            "status": ProjectStatus.READY_FOR_REVIEW.value,
            "title": request.title,
            "requirementSummary": {
                "businessGoal": request.requirement,
                "environment": request.context.environment,
                "constraints": [
                    f"Budget preference: {request.context.budget_preference}"
                ],
            },
            "cloud": {
                "provider": request.context.cloud,
                "region": "eu-west-1",
            },
            "solution": "A development VPC hosts an application service and a managed database.",
            "resources": [
                {
                    "id": "application-service",
                    "name": "Application Service",
                    "providerType": "AWS::ECS::Service",
                    "category": "CONTAINER",
                    "scope": "PRIVATE",
                    "purpose": "Runs the application workloads.",
                    "configuration": {"desiredCount": 1},
                },
                {
                    "id": "application-database",
                    "name": "Application Database",
                    "providerType": "AWS::RDS::DBInstance",
                    "category": "DATABASE",
                    "scope": "PRIVATE",
                    "purpose": "Stores application data.",
                    "configuration": {"engine": "postgres"},
                },
            ],
            "relationships": [
                {
                    "sourceId": "application-service",
                    "targetId": "application-database",
                    "type": "READS_AND_WRITES",
                }
            ],
        }

    @staticmethod
    def _mock_report(request: MockProjectCreate) -> str:
        return (
            f"# {request.title}\n\n"
            "## Requirement\n\n"
            f"{request.requirement}\n\n"
            "## Proposed architecture\n\n"
            "A small application service connects privately to a managed database. "
            "This mock version verifies Nimbus database persistence before agent orchestration."
        )

    @staticmethod
    def _mock_simple_diagram() -> str:
        return "flowchart LR\n    User --> App[Application Service]\n    App --> DB[(Database)]"

    @staticmethod
    def _mock_advanced_diagram() -> str:
        return (
            "flowchart TB\n"
            "    Internet --> ALB[Application Load Balancer]\n"
            "    ALB --> ECS[ECS Application Service]\n"
            "    ECS --> RDS[(RDS PostgreSQL)]"
        )
