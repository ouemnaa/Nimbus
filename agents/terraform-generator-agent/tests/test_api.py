import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


FIXTURES = Path(__file__).parent / "fixtures"
client = TestClient(app)


def architecture_payload():
    return json.loads((FIXTURES / "ecs_rds_architecture.json").read_text())


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "terraform-generator-agent"}


def test_generate_for_ecs_rds_fixture():
    response = client.post("/api/v1/terraform/generate", json={"architecture": architecture_payload(), "options": {"allow_repairs": True}})
    assert response.status_code == 200
    assert response.json()["generation_status"] == "SUCCESS"


def test_validate_endpoint():
    response = client.post("/api/v1/terraform/validate", json={"files": [{"path": "versions.tf", "content": "terraform {}\n"}], "options": {"enable_init": False}})
    assert response.status_code == 200
    assert response.json()["validation_status"] in {"PASSED", "FAILED", "SKIPPED"}


def test_generate_and_validate_returns_both_objects():
    response = client.post("/api/v1/terraform/generate-and-validate", json={"architecture": architecture_payload(), "options": {"allow_repairs": True, "enable_plan": False}})
    assert response.status_code == 200
    body = response.json()
    assert "generation" in body and "validation" in body
    assert body["generation"]["generation_status"] == "SUCCESS"


def test_unsupported_architecture_is_clean():
    payload = json.loads((FIXTURES / "unsupported_eks_architecture.json").read_text())
    response = client.post("/api/v1/terraform/generate", json={"architecture": payload})
    assert response.status_code == 200
    assert response.json()["generation_status"] == "UNSUPPORTED"
