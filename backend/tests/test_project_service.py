from unittest.mock import AsyncMock

import pytest
from bson import ObjectId

from app.schemas.project import MockProjectCreate
from app.schemas.project import ProjectCreate
from app.services.agent_client import AgentAnalysisResult
from app.services.project_service import ProjectService


@pytest.mark.asyncio
async def test_create_mock_project_persists_complete_workspace() -> None:
    project_id = ObjectId("64b000000000000000000011")
    version_id = ObjectId("64b000000000000000000012")
    message_ids = iter(
        [
            ObjectId("64b000000000000000000013"),
            ObjectId("64b000000000000000000014"),
        ]
    )

    projects = AsyncMock()
    versions = AsyncMock()
    messages = AsyncMock()
    change_requests = AsyncMock()

    projects.get_by_slug.return_value = None
    projects.create.side_effect = lambda document: {**document, "_id": project_id}
    versions.create.side_effect = lambda document: {**document, "_id": version_id}
    messages.create.side_effect = lambda document: {
        **document,
        "_id": next(message_ids),
    }

    async def set_current_version(
        _: ObjectId, current_version_id: ObjectId, status: str
    ) -> dict:
        created_project = projects.create.call_args.args[0]
        return {
            **created_project,
            "_id": project_id,
            "currentVersionId": current_version_id,
            "status": status,
        }

    projects.set_current_version.side_effect = set_current_version

    service = ProjectService(projects, versions, messages, change_requests)
    request = MockProjectCreate.model_validate(
        {
            "title": "Gaming Platform Dev Architecture",
            "requirement": "Host platform and game backends on AWS.",
            "context": {
                "environment": "development",
                "budgetPreference": "low",
                "cloud": "AWS",
            },
        }
    )

    workspace = await service.create_mock_project(request)

    assert workspace.project.id == str(project_id)
    assert workspace.project.current_version_id == str(version_id)
    assert workspace.current_version is not None
    assert workspace.current_version.version == "1.0.0"
    assert len(workspace.versions) == 1
    assert [message.role.value for message in workspace.messages] == [
        "user",
        "assistant",
    ]
    projects.create.assert_awaited_once()
    versions.create.assert_awaited_once()
    assert messages.create.await_count == 2


@pytest.mark.asyncio
async def test_create_project_persists_agent_workspace() -> None:
    project_id = ObjectId("64b000000000000000000021")
    version_id = ObjectId("64b000000000000000000022")
    message_ids = iter(
        [
            ObjectId("64b000000000000000000023"),
            ObjectId("64b000000000000000000024"),
        ]
    )

    projects = AsyncMock()
    versions = AsyncMock()
    messages = AsyncMock()
    change_requests = AsyncMock()
    agent_client = AsyncMock()

    projects.get_by_slug.return_value = None
    projects.create.side_effect = lambda document: {**document, "_id": project_id}
    versions.create.side_effect = lambda document: {**document, "_id": version_id}
    messages.create.side_effect = lambda document: {
        **document,
        "_id": next(message_ids),
    }
    agent_client.analyze_requirement.return_value = AgentAnalysisResult(
        architecture={
            "title": "Gaming Platform Dev Architecture",
            "status": "READY_FOR_REVIEW",
            "resources": [],
        },
        report_markdown="# Gaming Platform Dev Architecture",
        metadata={"provider": "agent", "model": "test-model"},
    )

    async def set_current_version(
        _: ObjectId, current_version_id: ObjectId, status: str
    ) -> dict:
        created_project = projects.create.call_args.args[0]
        return {
            **created_project,
            "_id": project_id,
            "currentVersionId": current_version_id,
            "status": status,
        }

    projects.set_current_version.side_effect = set_current_version

    service = ProjectService(
        projects,
        versions,
        messages,
        change_requests,
        agent_client,
    )
    request = ProjectCreate.model_validate(
        {
            "requirement": "Host platform and game backends on AWS.",
            "context": {
                "environment": "development",
                "budgetPreference": "low",
                "cloud": "AWS",
            },
        }
    )

    workspace = await service.create_project(request)

    version_document = versions.create.call_args.args[0]
    project_document = projects.create.call_args.args[0]

    assert workspace.project.id == str(project_id)
    assert workspace.project.title == "Gaming Platform Dev Architecture"
    assert workspace.project.current_version_id == str(version_id)
    assert workspace.current_version is not None
    assert workspace.current_version.version == "1.0.0"
    assert version_document["version"] == "1.0.0"
    assert version_document["architecture"]["resources"] == []
    assert version_document["reportMarkdown"] == "# Gaming Platform Dev Architecture"
    assert project_document["currentVersionId"] is None
    assert [message.role.value for message in workspace.messages] == [
        "user",
        "assistant",
    ]
    agent_client.analyze_requirement.assert_awaited_once_with(
        "Host platform and game backends on AWS.",
        {
            "environment": "development",
            "budget_preference": "low",
            "cloud": "AWS",
        },
    )
    projects.set_current_version.assert_awaited_once_with(
        project_id,
        version_id,
        "READY_FOR_REVIEW",
    )
    assert messages.create.await_count == 2
