import asyncio
from typing import Any

from bson import ObjectId

from app.core.errors import DatabaseUnavailableError, InvalidOperationError, NotFoundError
from app.models.architecture_version import build_architecture_version_document
from app.models.change_request import build_change_request_document
from app.models.chat_message import build_chat_message_document
from app.models.project import build_project_document
from app.repositories.architecture_version_repository import (
    ArchitectureVersionRepository,
)
from app.repositories.change_request_repository import ChangeRequestRepository
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.architecture_version import ArchitectureVersionResponse
from app.schemas.change_request import ChangeRequestResponse
from app.schemas.chat_message import (
    ChatMessageResponse,
    ProjectMessageCreate,
    ProjectMessageResponse,
)
from app.schemas.common import ChangeRequestStatus, ChatIntent, ChatRole, ProjectStatus
from app.schemas.project import MockProjectCreate, ProjectCreate, ProjectResponse
from app.schemas.workspace import ProjectWorkspaceResponse
from app.services.agent_client import SolutionArchitectAgentClient
from app.utils.slug import slugify


class ProjectService:
    def __init__(
        self,
        project_repository: ProjectRepository,
        version_repository: ArchitectureVersionRepository,
        message_repository: ChatMessageRepository,
        change_request_repository: ChangeRequestRepository,
        agent_client: SolutionArchitectAgentClient | None = None,
    ) -> None:
        self.projects = project_repository
        self.versions = version_repository
        self.messages = message_repository
        self.change_requests = change_request_repository
        self.agent_client = agent_client

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

    async def send_message(
        self, project_id: ObjectId, request: ProjectMessageCreate
    ) -> ProjectMessageResponse:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project")

        current_version_id = project.get("currentVersionId")
        if current_version_id is None:
            raise NotFoundError("Current architecture version")

        current_version = await self.versions.get_by_id(current_version_id)
        if current_version is None:
            raise NotFoundError("Current architecture version")

        recent_messages = await self.messages.list_recent_for_project(project_id, 8)
        user_message = await self.messages.create(
            build_chat_message_document(
                project_id=project_id,
                architecture_version_id=current_version_id,
                role=ChatRole.USER.value,
                content=request.message,
                intent=ChatIntent.INITIAL.value,
                architecture_changed=False,
            )
        )

        agent_client = self.agent_client or SolutionArchitectAgentClient()
        agent_result = await agent_client.follow_up(
            session_id=str(project_id),
            current_architecture=current_version["architecture"],
            current_report_markdown=current_version.get("reportMarkdown"),
            conversation_summary=None,
            messages=[
                {"role": item["role"], "content": item["content"]}
                for item in recent_messages
            ],
            user_message=request.message,
        )

        intent = ChatIntent(agent_result.intent)
        assistant_message = await self.messages.create(
            build_chat_message_document(
                project_id=project_id,
                architecture_version_id=current_version_id,
                role=ChatRole.ASSISTANT.value,
                content=agent_result.answer,
                intent=intent.value,
                architecture_changed=agent_result.architecture_changed,
            )
        )

        if not agent_result.architecture_changed:
            return ProjectMessageResponse(
                intent=intent,
                architecture_changed=False,
                answer=agent_result.answer,
                project=ProjectResponse.from_document(project),
                current_version=ArchitectureVersionResponse.from_document(
                    current_version
                ),
                messages=[
                    ChatMessageResponse.from_document(item)
                    for item in [*recent_messages, user_message, assistant_message]
                ],
            )

        new_version_string = agent_result.new_version or self._next_minor_version(
            current_version["version"]
        )
        draft_document = build_architecture_version_document(
            project_id=project_id,
            version=new_version_string,
            parent_version_id=current_version_id,
            status=ProjectStatus.DRAFT_REVISION.value,
            architecture=agent_result.architecture or {},
            report_markdown=agent_result.report_markdown or "",
            simple_diagram_mermaid=(agent_result.architecture or {}).get(
                "simpleDiagramMermaid"
            )
            or (agent_result.architecture or {}).get("simple_diagram_mermaid"),
            advanced_diagram_mermaid=(agent_result.architecture or {}).get(
                "advancedDiagramMermaid"
            )
            or (agent_result.architecture or {}).get("advanced_diagram_mermaid"),
            change_summary=agent_result.change_summary,
            metadata=agent_result.metadata,
        )
        draft_version = await self.versions.create(draft_document)
        change_request = await self.change_requests.create(
            build_change_request_document(
                project_id=project_id,
                from_version_id=current_version_id,
                to_version_id=draft_version["_id"],
                user_message=request.message,
                change_summary=agent_result.change_summary,
                status=ChangeRequestStatus.PENDING.value,
            )
        )

        return ProjectMessageResponse(
            intent=intent,
            architecture_changed=True,
            answer=agent_result.answer,
            draft_version=ArchitectureVersionResponse.from_document(draft_version),
            change_request=ChangeRequestResponse.from_document(change_request),
            change_summary=agent_result.change_summary,
            messages=[
                ChatMessageResponse.from_document(item)
                for item in [*recent_messages, user_message, assistant_message]
            ],
        )

    async def accept_draft(
        self, project_id: ObjectId, version_id: ObjectId
    ) -> ProjectWorkspaceResponse:
        version = await self._get_project_draft_version(project_id, version_id)
        updated_version = await self.versions.set_status(
            version_id, ProjectStatus.READY_FOR_REVIEW.value
        )
        if updated_version is None:
            raise NotFoundError("Architecture version")

        project = await self.projects.set_current_version(
            project_id,
            version_id,
            ProjectStatus.READY_FOR_REVIEW.value,
        )
        if project is None:
            raise NotFoundError("Project")

        change_request = await self.change_requests.get_pending_for_version(
            project_id, version_id
        )
        if change_request is not None:
            await self.change_requests.set_status(
                change_request["_id"], ChangeRequestStatus.ACCEPTED.value
            )

        await self.messages.create(
            build_chat_message_document(
                project_id=project_id,
                architecture_version_id=version_id,
                role=ChatRole.ASSISTANT.value,
                content=f"Draft architecture version {version['version']} accepted.",
                intent=ChatIntent.SYSTEM.value,
                architecture_changed=True,
            )
        )
        return await self.get_workspace(project_id)

    async def discard_draft(
        self, project_id: ObjectId, version_id: ObjectId
    ) -> ProjectWorkspaceResponse:
        version = await self._get_project_draft_version(project_id, version_id)
        change_request = await self.change_requests.get_pending_for_version(
            project_id, version_id
        )
        if change_request is not None:
            await self.change_requests.set_status(
                change_request["_id"], ChangeRequestStatus.DISCARDED.value
            )

        await self.messages.create(
            build_chat_message_document(
                project_id=project_id,
                architecture_version_id=version_id,
                role=ChatRole.ASSISTANT.value,
                content=f"Draft architecture version {version['version']} discarded.",
                intent=ChatIntent.SYSTEM.value,
                architecture_changed=False,
            )
        )
        return await self.get_workspace(project_id)

    async def create_project(self, request: ProjectCreate) -> ProjectWorkspaceResponse:
        agent_client = self.agent_client or SolutionArchitectAgentClient()
        agent_result = await agent_client.analyze_requirement(
            request.requirement,
            request.context.model_dump(),
        )

        architecture = agent_result.architecture
        status = self._status_from_architecture(architecture)
        title = self._title_from_architecture_or_requirement(
            architecture,
            request.requirement,
        )

        project_id: ObjectId | None = None
        try:
            slug = await self._unique_slug(title)
            project_document = build_project_document(
                title=title,
                slug=slug,
                initial_requirement=request.requirement,
                context=request.context.model_dump(by_alias=True),
                status=status.value,
            )
            project = await self.projects.create(project_document)
            project_id = project["_id"]

            version_document = build_architecture_version_document(
                project_id=project_id,
                version="1.0.0",
                status=status.value,
                architecture=architecture,
                report_markdown=agent_result.report_markdown,
                simple_diagram_mermaid=architecture.get("simpleDiagramMermaid")
                or architecture.get("simple_diagram_mermaid"),
                advanced_diagram_mermaid=architecture.get("advancedDiagramMermaid")
                or architecture.get("advanced_diagram_mermaid"),
                change_summary=["Generated the initial architecture."],
                metadata=agent_result.metadata,
            )
            version = await self.versions.create(version_document)
            version_id = version["_id"]

            project = await self.projects.set_current_version(
                project_id,
                version_id,
                status.value,
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
                    content=(
                        "The initial architecture has been generated and is ready "
                        "for review."
                    ),
                    intent=ChatIntent.SYSTEM.value,
                    architecture_changed=True,
                )
            )
        except Exception:
            if project_id is not None:
                await self._best_effort_delete_project(project_id)
            raise DatabaseUnavailableError() from None

        return self._workspace_from_documents(
            project, [version], [user_message, assistant_message]
        )

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

    async def _best_effort_delete_project(self, project_id: ObjectId) -> None:
        try:
            await self._delete_related(project_id)
            await self.projects.delete(project_id)
        except Exception:
            return None

    async def _get_project_draft_version(
        self, project_id: ObjectId, version_id: ObjectId
    ) -> dict[str, Any]:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project")

        version = await self.versions.get_by_id(version_id)
        if version is None or version.get("projectId") != project_id:
            raise NotFoundError("Architecture version")
        if version.get("status") != ProjectStatus.DRAFT_REVISION.value:
            raise InvalidOperationError("Architecture version is not a draft revision.")
        return version

    @staticmethod
    def _next_minor_version(version: str) -> str:
        parts = version.split(".")
        if len(parts) != 3:
            return "1.1.0"
        try:
            major = int(parts[0])
            minor = int(parts[1])
        except ValueError:
            return "1.1.0"
        return f"{major}.{minor + 1}.0"

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

    @staticmethod
    def _status_from_architecture(architecture: dict[str, Any]) -> ProjectStatus:
        status = architecture.get("status")
        if status == ProjectStatus.NEEDS_CLARIFICATION.value:
            return ProjectStatus.NEEDS_CLARIFICATION
        if status == ProjectStatus.UNSUPPORTED.value:
            return ProjectStatus.UNSUPPORTED
        return ProjectStatus.READY_FOR_REVIEW

    @staticmethod
    def _title_from_architecture_or_requirement(
        architecture: dict[str, Any], requirement: str
    ) -> str:
        title = architecture.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()[:200]

        words = [
            word.strip(".,:;!?()[]{}").lower()
            for word in requirement.split()
        ]
        ignored = {
            "a",
            "an",
            "and",
            "for",
            "i",
            "need",
            "on",
            "the",
            "to",
            "want",
            "with",
        }
        title_words = [word for word in words if word and word not in ignored][:4]
        if not title_words:
            return "Cloud Architecture"
        return f"{' '.join(title_words).title()} Architecture"[:200]
