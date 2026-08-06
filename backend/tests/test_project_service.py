from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from datetime import datetime, timezone

from app.schemas.common import ProjectStatus
from app.schemas.project import MockProjectCreate
from app.schemas.project import ProjectCreate
from app.schemas.chat_message import ProjectMessageCreate
from app.services.agent_client import AgentAnalysisResult, AgentFollowUpResult
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


def _version_document(
    version_id: ObjectId,
    project_id: ObjectId,
    *,
    version: str = "1.0.0",
    status: str = "READY_FOR_REVIEW",
    parent_version_id: ObjectId | None = None,
) -> dict:
    return {
        "_id": version_id,
        "projectId": project_id,
        "version": version,
        "parentVersionId": parent_version_id,
        "status": status,
        "architecture": {
            "title": "Gaming Platform Dev Architecture",
            "architecture_version": version,
            "status": "READY_FOR_REVIEW",
            "resources": [],
        },
        "reportMarkdown": "# Report",
        "simpleDiagramMermaid": None,
        "advancedDiagramMermaid": None,
        "changeSummary": [],
        "metadata": {"provider": "test"},
        "createdAt": datetime.now(timezone.utc),
    }


def _message_document(
    message_id: ObjectId,
    project_id: ObjectId,
    *,
    role: str,
    content: str,
    version_id: ObjectId | None = None,
) -> dict:
    return {
        "_id": message_id,
        "projectId": project_id,
        "architectureVersionId": version_id,
        "role": role,
        "content": content,
        "intent": "EXPLAIN",
        "architectureChanged": False,
        "createdAt": datetime.now(timezone.utc),
    }


@pytest.mark.asyncio
async def test_explain_follow_up_does_not_create_new_version() -> None:
    project_id = ObjectId("64b000000000000000000031")
    version_id = ObjectId("64b000000000000000000032")
    user_message_id = ObjectId("64b000000000000000000033")
    assistant_message_id = ObjectId("64b000000000000000000034")

    projects = AsyncMock()
    versions = AsyncMock()
    messages = AsyncMock()
    change_requests = AsyncMock()
    agent_client = AsyncMock()

    project = {
        "_id": project_id,
        "title": "Gaming Platform Dev Architecture",
        "slug": "gaming-platform-dev-architecture",
        "initialRequirement": "Host game backends.",
        "context": {"environment": "development"},
        "currentVersionId": version_id,
        "status": "READY_FOR_REVIEW",
        "userId": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    current_version = _version_document(version_id, project_id)
    recent = [
        _message_document(
            ObjectId(f"64b00000000000000000004{i}"),
            project_id,
            role="user",
            content=f"message {i}",
            version_id=version_id,
        )
        for i in range(8)
    ]

    projects.get_by_id.return_value = project
    versions.get_by_id.return_value = current_version
    messages.list_recent_for_project.return_value = recent
    messages.create.side_effect = [
        _message_document(
            user_message_id,
            project_id,
            role="user",
            content="Why this database?",
            version_id=version_id,
        ),
        _message_document(
            assistant_message_id,
            project_id,
            role="assistant",
            content="Because managed PostgreSQL reduces operations.",
            version_id=version_id,
        ),
    ]
    agent_client.follow_up.return_value = AgentFollowUpResult(
        intent="EXPLAIN",
        architecture_changed=False,
        answer="Because managed PostgreSQL reduces operations.",
        change_summary=[],
        previous_version="1.0.0",
        new_version=None,
        architecture=None,
        report_markdown=None,
        metadata={},
    )

    service = ProjectService(projects, versions, messages, change_requests, agent_client)
    response = await service.send_message(
        project_id, ProjectMessageCreate(message="Why this database?")
    )

    assert response.intent.value == "EXPLAIN"
    assert response.architecture_changed is False
    versions.create.assert_not_awaited()
    change_requests.create.assert_not_awaited()
    assert messages.create.await_count == 2
    sent_messages = agent_client.follow_up.call_args.kwargs["messages"]
    assert len(sent_messages) == 8


@pytest.mark.asyncio
async def test_modify_follow_up_creates_draft_revision() -> None:
    project_id = ObjectId("64b000000000000000000051")
    version_id = ObjectId("64b000000000000000000052")
    draft_id = ObjectId("64b000000000000000000053")
    change_request_id = ObjectId("64b000000000000000000054")

    projects = AsyncMock()
    versions = AsyncMock()
    messages = AsyncMock()
    change_requests = AsyncMock()
    agent_client = AsyncMock()

    project = {
        "_id": project_id,
        "title": "Gaming Platform Dev Architecture",
        "slug": "gaming-platform-dev-architecture",
        "initialRequirement": "Host game backends.",
        "context": {"environment": "development"},
        "currentVersionId": version_id,
        "status": "READY_FOR_REVIEW",
        "userId": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    current_version = _version_document(version_id, project_id)
    projects.get_by_id.return_value = project
    versions.get_by_id.return_value = current_version
    messages.list_recent_for_project.return_value = []
    messages.create.side_effect = [
        _message_document(ObjectId(), project_id, role="user", content="Add Redis"),
        _message_document(
            ObjectId(),
            project_id,
            role="assistant",
            content="Created draft architecture version 1.1.0.",
        ),
    ]
    versions.create.side_effect = lambda document: {**document, "_id": draft_id}
    change_requests.create.side_effect = lambda document: {
        **document,
        "_id": change_request_id,
    }
    agent_client.follow_up.return_value = AgentFollowUpResult(
        intent="MODIFY",
        architecture_changed=True,
        answer="Created draft architecture version 1.1.0.",
        change_summary=["Added Redis cache."],
        previous_version="1.0.0",
        new_version="1.1.0",
        architecture={"title": "Gaming Platform Dev Architecture", "resources": []},
        report_markdown="# Revised report",
        metadata={"provider": "test"},
    )

    service = ProjectService(projects, versions, messages, change_requests, agent_client)
    response = await service.send_message(
        project_id, ProjectMessageCreate(message="Add Redis")
    )

    draft_document = versions.create.call_args.args[0]
    change_document = change_requests.create.call_args.args[0]
    assert response.intent.value == "MODIFY"
    assert response.architecture_changed is True
    assert response.draft_version is not None
    assert response.draft_version.status == ProjectStatus.DRAFT_REVISION
    assert draft_document["version"] == "1.1.0"
    assert draft_document["parentVersionId"] == version_id
    assert change_document["status"] == "pending"
    projects.set_current_version.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("intent", ["CLARIFY", "UNSUPPORTED"])
async def test_non_modify_follow_up_does_not_create_version(intent: str) -> None:
    project_id = ObjectId()
    version_id = ObjectId()
    projects = AsyncMock()
    versions = AsyncMock()
    messages = AsyncMock()
    change_requests = AsyncMock()
    agent_client = AsyncMock()

    projects.get_by_id.return_value = {
        "_id": project_id,
        "title": "Architecture",
        "slug": "architecture",
        "initialRequirement": "Host an app.",
        "context": {},
        "currentVersionId": version_id,
        "status": "READY_FOR_REVIEW",
        "userId": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    versions.get_by_id.return_value = _version_document(version_id, project_id)
    messages.list_recent_for_project.return_value = []
    messages.create.side_effect = [
        _message_document(ObjectId(), project_id, role="user", content="Change it"),
        _message_document(
            ObjectId(),
            project_id,
            role="assistant",
            content="Please clarify.",
        ),
    ]
    agent_client.follow_up.return_value = AgentFollowUpResult(
        intent=intent,
        architecture_changed=False,
        answer="Please clarify.",
        change_summary=[],
        previous_version="1.0.0",
        new_version=None,
        architecture=None,
        report_markdown=None,
        metadata={},
    )

    service = ProjectService(projects, versions, messages, change_requests, agent_client)
    response = await service.send_message(
        project_id, ProjectMessageCreate(message="Change it")
    )

    assert response.intent.value == intent
    assert response.architecture_changed is False
    versions.create.assert_not_awaited()
    change_requests.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_accept_draft_updates_current_version() -> None:
    project_id = ObjectId()
    current_id = ObjectId()
    draft_id = ObjectId()
    change_request_id = ObjectId()

    projects = AsyncMock()
    versions = AsyncMock()
    messages = AsyncMock()
    change_requests = AsyncMock()

    project = {
        "_id": project_id,
        "title": "Architecture",
        "slug": "architecture",
        "initialRequirement": "Host an app.",
        "context": {},
        "currentVersionId": current_id,
        "status": "READY_FOR_REVIEW",
        "userId": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    draft = _version_document(
        draft_id,
        project_id,
        version="1.1.0",
        status="DRAFT_REVISION",
        parent_version_id=current_id,
    )

    projects.get_by_id.side_effect = [
        project,
        {**project, "currentVersionId": draft_id},
    ]
    versions.get_by_id.return_value = draft
    versions.set_status.return_value = {**draft, "status": "READY_FOR_REVIEW"}
    projects.set_current_version.return_value = {**project, "currentVersionId": draft_id}
    change_requests.get_pending_for_version.return_value = {
        "_id": change_request_id,
        "projectId": project_id,
    }
    change_requests.set_status.return_value = {}
    messages.create.return_value = _message_document(
        ObjectId(),
        project_id,
        role="assistant",
        content="Draft architecture version 1.1.0 accepted.",
        version_id=draft_id,
    )
    versions.list_for_project.return_value = [
        _version_document(current_id, project_id),
        {**draft, "status": "READY_FOR_REVIEW"},
    ]
    messages.list_for_project.return_value = []

    service = ProjectService(projects, versions, messages, change_requests)
    workspace = await service.accept_draft(project_id, draft_id)

    assert workspace.project.current_version_id == str(draft_id)
    projects.set_current_version.assert_awaited_once_with(
        project_id,
        draft_id,
        "READY_FOR_REVIEW",
    )
    change_requests.set_status.assert_awaited_once_with(change_request_id, "accepted")


@pytest.mark.asyncio
async def test_discard_draft_does_not_update_current_version() -> None:
    project_id = ObjectId()
    current_id = ObjectId()
    draft_id = ObjectId()
    change_request_id = ObjectId()

    projects = AsyncMock()
    versions = AsyncMock()
    messages = AsyncMock()
    change_requests = AsyncMock()

    project = {
        "_id": project_id,
        "title": "Architecture",
        "slug": "architecture",
        "initialRequirement": "Host an app.",
        "context": {},
        "currentVersionId": current_id,
        "status": "READY_FOR_REVIEW",
        "userId": None,
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    draft = _version_document(
        draft_id,
        project_id,
        version="1.1.0",
        status="DRAFT_REVISION",
        parent_version_id=current_id,
    )

    projects.get_by_id.side_effect = [project, project]
    versions.get_by_id.return_value = draft
    change_requests.get_pending_for_version.return_value = {
        "_id": change_request_id,
        "projectId": project_id,
    }
    change_requests.set_status.return_value = {}
    messages.create.return_value = _message_document(
        ObjectId(),
        project_id,
        role="assistant",
        content="Draft architecture version 1.1.0 discarded.",
        version_id=draft_id,
    )
    versions.list_for_project.return_value = [
        _version_document(current_id, project_id),
        draft,
    ]
    messages.list_for_project.return_value = []

    service = ProjectService(projects, versions, messages, change_requests)
    workspace = await service.discard_draft(project_id, draft_id)

    assert workspace.project.current_version_id == str(current_id)
    projects.set_current_version.assert_not_awaited()
    change_requests.set_status.assert_awaited_once_with(change_request_id, "discarded")


@pytest.mark.asyncio
async def test_version_from_another_project_cannot_be_accepted() -> None:
    project_id = ObjectId()
    other_project_id = ObjectId()
    draft_id = ObjectId()

    projects = AsyncMock()
    versions = AsyncMock()
    messages = AsyncMock()
    change_requests = AsyncMock()

    projects.get_by_id.return_value = {
        "_id": project_id,
        "currentVersionId": ObjectId(),
    }
    versions.get_by_id.return_value = _version_document(
        draft_id,
        other_project_id,
        version="1.1.0",
        status="DRAFT_REVISION",
    )

    service = ProjectService(projects, versions, messages, change_requests)

    with pytest.raises(Exception) as exc_info:
        await service.accept_draft(project_id, draft_id)

    assert "Architecture version not found" in str(exc_info.value)
    projects.set_current_version.assert_not_awaited()


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
