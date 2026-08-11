from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_project_service, get_terraform_service
from app.main import create_app
from app.schemas.architecture_version import ArchitectureVersionResponse
from app.schemas.chat_message import ChatMessageResponse
from app.schemas.common import ChatIntent, ChatRole, ProjectStatus
from app.schemas.project import ProjectResponse
from app.schemas.terraform_generation import TerraformGenerationResponse
from app.schemas.workspace import ProjectWorkspaceResponse
from app.services.project_service import ProjectService
from app.services.terraform_service import TerraformService


PROJECT_ID = "64b000000000000000000001"
VERSION_ID = "64b000000000000000000002"
USER_MESSAGE_ID = "64b000000000000000000003"
ASSISTANT_MESSAGE_ID = "64b000000000000000000004"
TERRAFORM_GENERATION_ID = "64b000000000000000000005"


class FakeDatabaseManager:
    database = object()

    async def connect(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def ping(self) -> bool:
        return True


@pytest.fixture
def workspace() -> ProjectWorkspaceResponse:
    now = datetime.now(timezone.utc)
    project = ProjectResponse(
        id=PROJECT_ID,
        title="Gaming Platform Dev Architecture",
        slug="gaming-platform-dev-architecture",
        initial_requirement="Host platform and game backends on AWS.",
        context={
            "environment": "development",
            "budgetPreference": "low",
            "cloud": "AWS",
        },
        current_version_id=VERSION_ID,
        status=ProjectStatus.READY_FOR_REVIEW,
        user_id=None,
        created_at=now,
        updated_at=now,
    )
    version = ArchitectureVersionResponse(
        id=VERSION_ID,
        project_id=PROJECT_ID,
        version="1.0.0",
        parent_version_id=None,
        status=ProjectStatus.READY_FOR_REVIEW,
        architecture={"title": "Mock architecture", "resources": []},
        report_markdown="# Mock architecture",
        simple_diagram_mermaid="flowchart LR\nUser --> App",
        advanced_diagram_mermaid=None,
        change_summary=["Created the initial architecture."],
        metadata={
            "provider": "mock",
            "model": "backend-development-fixture",
            "generationDurationMs": 0,
        },
        created_at=now,
    )
    messages = [
        ChatMessageResponse(
            id=USER_MESSAGE_ID,
            project_id=PROJECT_ID,
            architecture_version_id=None,
            role=ChatRole.USER,
            content="Host platform and game backends on AWS.",
            intent=ChatIntent.INITIAL,
            architecture_changed=False,
            created_at=now,
        ),
        ChatMessageResponse(
            id=ASSISTANT_MESSAGE_ID,
            project_id=PROJECT_ID,
            architecture_version_id=VERSION_ID,
            role=ChatRole.ASSISTANT,
            content="The initial architecture has been created.",
            intent=ChatIntent.SYSTEM,
            architecture_changed=True,
            created_at=now,
        ),
    ]
    return ProjectWorkspaceResponse(
        project=project,
        current_version=version,
        versions=[version],
        messages=messages,
    )


@pytest.fixture
def service(workspace: ProjectWorkspaceResponse) -> AsyncMock:
    mock = AsyncMock(spec=ProjectService)
    mock.create_project.return_value = workspace
    mock.create_mock_project.return_value = workspace
    mock.get_workspace.return_value = workspace
    mock.list_projects.return_value = [workspace.project]
    return mock


@pytest.fixture
def terraform_generation() -> TerraformGenerationResponse:
    now = datetime.now(timezone.utc)
    return TerraformGenerationResponse(
        id=TERRAFORM_GENERATION_ID,
        project_id=PROJECT_ID,
        architecture_version_id=VERSION_ID,
        status="SUCCESS",
        files=[
            {
                "path": "versions.tf",
                "content": 'terraform { required_version = ">= 1.6.0" }\n',
            }
        ],
        warnings=[],
        next_steps=["Run terraform init."],
        metadata={"generatorVersion": "test"},
        supported_resources=["aws_vpc"],
        unsupported_resources=[],
        derived_resources=[],
        repairs=[],
        error=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def terraform_service(terraform_generation: TerraformGenerationResponse) -> AsyncMock:
    mock = AsyncMock(spec=TerraformService)
    mock.generate_for_project.return_value = terraform_generation
    mock.latest_for_project.return_value = terraform_generation
    return mock


@pytest.fixture
def client(
    service: AsyncMock, terraform_service: AsyncMock
) -> Generator[TestClient, None, None]:
    application = create_app(FakeDatabaseManager())
    application.dependency_overrides[get_project_service] = lambda: service
    application.dependency_overrides[get_terraform_service] = lambda: terraform_service
    with TestClient(application) as test_client:
        yield test_client
