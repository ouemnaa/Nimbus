from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class ArchitectureStatus(str, Enum):
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    UNSUPPORTED = "UNSUPPORTED"

class ResourceCategory(str, Enum):
    NETWORK = "NETWORK"
    COMPUTE = "COMPUTE"
    CONTAINER = "CONTAINER"
    DATABASE = "DATABASE"
    STORAGE = "STORAGE"
    SECURITY = "SECURITY"
    LOAD_BALANCING = "LOAD_BALANCING"
    OBSERVABILITY = "OBSERVABILITY"
    IDENTITY = "IDENTITY"
    OTHER = "OTHER"

class ResourceScope(str, Enum):
    GLOBAL = "GLOBAL"
    REGIONAL = "REGIONAL"
    VPC = "VPC"
    PUBLIC_SUBNET = "PUBLIC_SUBNET"
    PRIVATE_SUBNET = "PRIVATE_SUBNET"
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"

class RelationshipType(str, Enum):
    ROUTES_TRAFFIC_TO = "ROUTES_TRAFFIC_TO"
    CONNECTS_TO = "CONNECTS_TO"
    READS_FROM = "READS_FROM"
    WRITES_TO = "WRITES_TO"
    AUTHENTICATES_WITH = "AUTHENTICATES_WITH"
    MONITORS = "MONITORS"
    DEPLOYS_TO = "DEPLOYS_TO"
    DEPENDS_ON = "DEPENDS_ON"

class RiskSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Alternative(BaseModel):
    option: str
    advantages: List[str]
    disadvantages: List[str]
    reason_not_selected: str

class Decision(BaseModel):
    title: str
    decision: str
    rationale: str
    alternatives_considered: List[Alternative]

class Risk(BaseModel):
    title: str
    description: str
    severity: RiskSeverity
    mitigation: str

class Resource(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9_-]+$")
    name: str
    provider_type: str
    category: ResourceCategory
    scope: ResourceScope
    purpose: str
    configuration: Dict[str, Any]
    depends_on: List[str] = []

class Relationship(BaseModel):
    source_id: str
    target_id: str
    relationship_type: RelationshipType
    label: str

class RequirementSummary(BaseModel):
    business_goal: str
    application_type: str
    environment: str
    expected_users_or_traffic: Optional[str] = None
    functional_requirements: List[str]
    non_functional_requirements: List[str]
    constraints: List[str]
    budget_preference: Optional[str] = None
    availability_requirement: Optional[str] = None

class CloudConfig(BaseModel):
    provider: str = "AWS"
    region: str
    region_rationale: str

class ArchitectureSpecification(BaseModel):
    schema_version: str = "1.0"
    architecture_id: str
    architecture_version: str = "1.0"
    status: ArchitectureStatus
    title: str
    requirement_summary: RequirementSummary
    cloud: CloudConfig
    solution: str
    resources: List[Resource] = []
    relationships: List[Relationship] = []
    decisions: List[Decision] = []
    security_considerations: List[str] = []
    reliability_considerations: List[str] = []
    scalability_considerations: List[str] = []
    cost_considerations: List[str] = []
    operational_considerations: List[str] = []
    assumptions: List[str] = []
    open_questions: List[str] = []
    risks: List[Risk] = []
    limitations: List[str] = []
    recommended_diagrams: List[str] = ["high-level"]

    @model_validator(mode="after")
    def validate_logic(self) -> "ArchitectureSpecification":
        # Check resource IDs uniqueness
        resource_ids = [r.id for r in self.resources]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("Resource IDs must be unique")
            
        # Check relationships and dependencies
        for rel in self.relationships:
            if rel.source_id not in resource_ids:
                raise ValueError(f"Relationship source '{rel.source_id}' does not exist")
            if rel.target_id not in resource_ids:
                raise ValueError(f"Relationship target '{rel.target_id}' does not exist")
                
        for res in self.resources:
            for dep in res.depends_on:
                if dep not in resource_ids:
                    raise ValueError(f"Dependency '{dep}' for resource '{res.id}' does not exist")
                    
        # Status specific checks
        if self.status == ArchitectureStatus.READY_FOR_REVIEW and not self.resources:
            raise ValueError("READY_FOR_REVIEW status must contain at least one resource")
        if self.status == ArchitectureStatus.NEEDS_CLARIFICATION and not self.open_questions:
            raise ValueError("NEEDS_CLARIFICATION status must contain at least one open question")
        if self.status == ArchitectureStatus.UNSUPPORTED and not self.limitations:
            raise ValueError("UNSUPPORTED status must contain an explanation in limitations or solution")
            
        return self
