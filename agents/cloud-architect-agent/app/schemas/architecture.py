from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

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

class DiagramVisibility(str, Enum):
    HIGH_LEVEL = "HIGH_LEVEL"
    TECHNICAL = "TECHNICAL"
    HIDDEN = "HIDDEN"

class Alternative(BaseModel):
    option: str
    advantages: List[str] = Field(default_factory=list)
    disadvantages: List[str] = Field(default_factory=list)
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

class MainCostDriver(BaseModel):
    resource_id: str
    reason: str

class CheaperAlternative(BaseModel):
    option: str
    tradeoff: str

class CostProfile(BaseModel):
    profile: str
    estimated_level: str
    main_cost_drivers: List[MainCostDriver] = Field(default_factory=list)
    cost_saving_choices: List[str] = Field(default_factory=list)
    cheaper_alternatives: List[CheaperAlternative] = Field(default_factory=list)
    production_upgrade_notes: List[str] = Field(default_factory=list)

class Resource(BaseModel):
    id: str = Field(..., pattern=r"^[a-z0-9_-]+$")
    name: str
    provider_type: str
    category: ResourceCategory
    scope: ResourceScope
    purpose: str
    configuration: Dict[str, Any]
    depends_on: List[str] = Field(default_factory=list)
    diagram_visibility: Optional[DiagramVisibility] = None

    @model_validator(mode="after")
    def set_default_diagram_visibility(self) -> "Resource":
        if self.diagram_visibility is None:
            self.diagram_visibility = infer_diagram_visibility(self)
        return self

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
    resources: List[Resource] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    decisions: List[Decision] = Field(default_factory=list)
    security_considerations: List[str] = Field(default_factory=list)
    reliability_considerations: List[str] = Field(default_factory=list)
    scalability_considerations: List[str] = Field(default_factory=list)
    cost_considerations: List[str] = Field(default_factory=list)
    cost_profile: Optional[CostProfile] = None
    operational_considerations: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    open_questions: List[str] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    recommended_diagrams: List[str] = Field(default_factory=lambda: ["high-level"])

    @model_validator(mode="after")
    def validate_logic(self) -> "ArchitectureSpecification":
        if self.cost_profile is None:
            self.cost_profile = build_default_cost_profile(self)

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


def infer_diagram_visibility(resource: Resource) -> DiagramVisibility:
    provider_type = resource.provider_type.lower()
    name = resource.name.lower()

    hidden_keywords = ("listener", "target_group", "target-group", "route_table", "route-table", "association")
    technical_keywords = ("security_group", "security-group", "iam_role", "iam-role", "cluster", "subnet", "internet_gateway", "nat_gateway")
    high_level_keywords = ("load_balancer", "load-balancer", "service", "database", "secret", "cloudwatch", "s3", "bucket")

    if any(keyword in provider_type or keyword in name for keyword in hidden_keywords):
        return DiagramVisibility.HIDDEN
    if resource.category in {ResourceCategory.NETWORK, ResourceCategory.IDENTITY}:
        return DiagramVisibility.TECHNICAL
    if any(keyword in provider_type or keyword in name for keyword in technical_keywords):
        return DiagramVisibility.TECHNICAL
    if resource.category in {
        ResourceCategory.LOAD_BALANCING,
        ResourceCategory.DATABASE,
        ResourceCategory.OBSERVABILITY,
        ResourceCategory.STORAGE,
    }:
        return DiagramVisibility.HIGH_LEVEL
    if resource.category == ResourceCategory.SECURITY and "secret" in f"{provider_type} {name}":
        return DiagramVisibility.HIGH_LEVEL
    if resource.category in {ResourceCategory.CONTAINER, ResourceCategory.COMPUTE}:
        if "service" in f"{provider_type} {name}":
            return DiagramVisibility.HIGH_LEVEL
        if "task_definition" in provider_type or "task-definition" in name:
            return DiagramVisibility.HIDDEN
        return DiagramVisibility.TECHNICAL
    if any(keyword in provider_type or keyword in name for keyword in high_level_keywords):
        return DiagramVisibility.HIGH_LEVEL
    return DiagramVisibility.TECHNICAL


def build_default_cost_profile(architecture: ArchitectureSpecification) -> CostProfile:
    profile = "STANDARD"
    estimated_level = "MEDIUM"
    environment = architecture.requirement_summary.environment.lower()
    constraints = " ".join(architecture.requirement_summary.constraints).lower()
    cost_text = " ".join(architecture.cost_considerations).lower()
    has_low_cost_signal = "low cost" in constraints or "budget" in constraints or "low" in cost_text

    if environment == "development" and has_low_cost_signal:
        profile = "LOW_COST_DEVELOPMENT"
        estimated_level = "LOW_TO_MEDIUM"
    elif environment == "development":
        profile = "DEVELOPMENT"
        estimated_level = "LOW_TO_MEDIUM"

    drivers: List[MainCostDriver] = []
    saving_choices: List[str] = []
    cheaper_alternatives: List[CheaperAlternative] = []
    production_upgrade_notes: List[str] = []

    for resource in architecture.resources:
        resource_text = f"{resource.name} {resource.provider_type}".lower()
        if "nat" in resource_text:
            drivers.append(
                MainCostDriver(
                    resource_id=resource.id,
                    reason="NAT Gateway improves private networking but can become a noticeable cost driver in development.",
                )
            )
        elif resource.category == ResourceCategory.LOAD_BALANCING:
            drivers.append(
                MainCostDriver(
                    resource_id=resource.id,
                    reason="A shared load balancer reduces duplication, but it still adds baseline load balancing cost.",
                )
            )
        elif resource.category == ResourceCategory.DATABASE:
            drivers.append(
                MainCostDriver(
                    resource_id=resource.id,
                    reason="Managed database services add ongoing cost but reduce operational work and risk.",
                )
            )

    if any(resource.category == ResourceCategory.LOAD_BALANCING for resource in architecture.resources):
        saving_choices.append("Single Application Load Balancer shared across exposed services when routing rules allow it.")
    if any(resource.category == ResourceCategory.DATABASE for resource in architecture.resources):
        saving_choices.append("Single-AZ managed PostgreSQL for development to limit database cost.")
    if any(resource.category == ResourceCategory.CONTAINER for resource in architecture.resources):
        saving_choices.append("Minimal service count for development workloads instead of scaling out by default.")
    if not any("eks" in resource.provider_type.lower() or "kubernetes" in resource.name.lower() for resource in architecture.resources):
        saving_choices.append("No Kubernetes cluster because the workload does not justify added platform cost.")

    cheaper_alternatives.extend(
        [
            CheaperAlternative(
                option="Public application tasks without a NAT Gateway",
                tradeoff="Lower cost, but weaker isolation and less production-like networking.",
            ),
            CheaperAlternative(
                option="Single EC2 instance running the full stack",
                tradeoff="Cheaper for development, but more manual operations and less scaling flexibility.",
            ),
        ]
    )

    production_upgrade_notes.extend(
        [
            "Use Multi-AZ RDS.",
            "Use multiple NAT Gateways.",
            "Add HTTPS with ACM.",
            "Add autoscaling policies.",
            "Add stronger monitoring and alerting.",
        ]
    )

    return CostProfile(
        profile=profile,
        estimated_level=estimated_level,
        main_cost_drivers=drivers,
        cost_saving_choices=saving_choices,
        cheaper_alternatives=cheaper_alternatives,
        production_upgrade_notes=production_upgrade_notes,
    )
