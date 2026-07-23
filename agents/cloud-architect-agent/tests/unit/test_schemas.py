import pytest
from pydantic import ValidationError
from app.schemas.architecture import (
    ArchitectureSpecification, 
    ArchitectureStatus, 
    Resource, 
    ResourceCategory, 
    ResourceScope,
    Relationship,
    RelationshipType
)

def test_valid_architecture():
    data = {
        "architecture_id": "arch-123",
        "status": ArchitectureStatus.READY_FOR_REVIEW,
        "title": "Test Arch",
        "requirement_summary": {
            "business_goal": "Test",
            "application_type": "Test",
            "environment": "Test",
            "functional_requirements": ["Req 1"],
            "non_functional_requirements": ["Req 2"],
            "constraints": ["Const 1"]
        },
        "cloud": {
            "provider": "AWS",
            "region": "us-east-1",
            "region_rationale": "Default"
        },
        "solution": "Test solution",
        "resources": [
            {
                "id": "s3-bucket",
                "name": "My Bucket",
                "provider_type": "aws_s3_bucket",
                "category": ResourceCategory.STORAGE,
                "scope": ResourceScope.REGIONAL,
                "purpose": "Storage",
                "configuration": {},
                "depends_on": []
            }
        ]
    }
    arch = ArchitectureSpecification(**data)
    assert arch.architecture_id == "arch-123"

def test_invalid_resource_id():
    with pytest.raises(ValidationError):
        Resource(
            id="Invalid ID!",
            name="Test",
            provider_type="test",
            category=ResourceCategory.OTHER,
            scope=ResourceScope.GLOBAL,
            purpose="Test",
            configuration={}
        )

def test_missing_relationship_target():
    data = {
        "architecture_id": "arch-123",
        "status": ArchitectureStatus.READY_FOR_REVIEW,
        "title": "Test Arch",
        "requirement_summary": {
            "business_goal": "Test",
            "application_type": "Test",
            "environment": "Test",
            "functional_requirements": [],
            "non_functional_requirements": [],
            "constraints": []
        },
        "cloud": {"provider": "AWS", "region": "us-east-1", "region_rationale": "Test"},
        "solution": "Test",
        "resources": [
            {
                "id": "res-1",
                "name": "Res 1",
                "provider_type": "test",
                "category": "OTHER",
                "scope": "GLOBAL",
                "purpose": "Test",
                "configuration": {}
            }
        ],
        "relationships": [
            {
                "source_id": "res-1",
                "target_id": "non-existent",
                "relationship_type": "DEPENDS_ON",
                "label": "Test"
            }
        ]
    }
    with pytest.raises(ValidationError):
        ArchitectureSpecification(**data)
