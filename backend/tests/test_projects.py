from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.errors import AgentResponseError, AgentUnavailableError
from tests.conftest import PROJECT_ID


MOCK_REQUEST = {
    "title": "Gaming Platform Dev Architecture",
    "requirement": "I want to host a platform backend and multiple game backends on AWS.",
    "context": {
        "environment": "development",
        "budgetPreference": "low",
        "cloud": "AWS",
    },
}


def test_invalid_project_id_returns_safe_error(client: TestClient) -> None:
    response = client.get("/api/projects/not-an-object-id")

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "invalid_object_id",
            "message": "Invalid project_id.",
        }
    }


def test_send_message_invalid_project_id_returns_safe_error(client: TestClient) -> None:
    response = client.post(
        "/api/projects/not-an-object-id/messages",
        json={"message": "Why this architecture?"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "invalid_object_id",
            "message": "Invalid project_id.",
        }
    }


def test_mock_project_creation_returns_workspace(
    client: TestClient, service: AsyncMock
) -> None:
    response = client.post("/api/projects/mock", json=MOCK_REQUEST)

    assert response.status_code == 201
    body = response.json()
    assert body["project"]["id"] == PROJECT_ID
    assert body["currentVersion"]["version"] == "1.0.0"
    assert len(body["versions"]) == 1
    assert len(body["messages"]) == 2
    service.create_mock_project.assert_awaited_once()


def test_project_creation_returns_workspace(
    client: TestClient, service: AsyncMock
) -> None:
    response = client.post(
        "/api/projects",
        json={
            "requirement": MOCK_REQUEST["requirement"],
            "context": MOCK_REQUEST["context"],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["project"]["id"] == PROJECT_ID
    assert body["currentVersion"]["version"] == "1.0.0"
    service.create_project.assert_awaited_once()


def test_project_creation_empty_requirement_returns_validation_error(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/projects",
        json={
            "requirement": "   ",
            "context": MOCK_REQUEST["context"],
        },
    )

    assert response.status_code == 422


def test_project_creation_agent_unavailable_returns_safe_error(
    client: TestClient, service: AsyncMock
) -> None:
    service.create_project.side_effect = AgentUnavailableError("http://localhost:8001")

    response = client.post(
        "/api/projects",
        json={
            "requirement": MOCK_REQUEST["requirement"],
            "context": MOCK_REQUEST["context"],
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "agent_unavailable",
            "message": (
                "Could not reach the Solution Architect Agent. "
                "Make sure it is running on http://localhost:8001."
            ),
        }
    }


def test_project_creation_invalid_agent_response_returns_safe_error(
    client: TestClient, service: AsyncMock
) -> None:
    service.create_project.side_effect = AgentResponseError()

    response = client.post(
        "/api/projects",
        json={
            "requirement": MOCK_REQUEST["requirement"],
            "context": MOCK_REQUEST["context"],
        },
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "code": "agent_invalid_response",
            "message": "Solution Architect Agent returned an invalid response.",
        }
    }


def test_project_workspace_contract(client: TestClient) -> None:
    response = client.get(f"/api/projects/{PROJECT_ID}")

    assert response.status_code == 200
    assert set(response.json()) == {
        "project",
        "currentVersion",
        "versions",
        "messages",
    }


def test_list_projects(client: TestClient) -> None:
    response = client.get("/api/projects")

    assert response.status_code == 200
    assert response.json()[0]["id"] == PROJECT_ID
