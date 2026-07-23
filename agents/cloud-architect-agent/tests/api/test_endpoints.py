import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_analyze_endpoint_fake_provider():
    # Ensure we use fake provider for tests
    settings.LLM_PROVIDER = "fake"
    
    payload = {
        "requirement": "Deploy a simple S3 bucket",
        "context": {"env": "prod"}
    }
    response = client.post("/api/v1/architectures/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "architecture" in data
    assert "report_markdown" in data
    assert data["metadata"]["provider"] == "fake"
