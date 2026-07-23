from app.renderers.markdown_renderer import MarkdownRenderer, format_enum_label
from app.renderers.mermaid_renderer import MermaidRenderer
from app.schemas.architecture import ArchitectureSpecification, ArchitectureStatus


def build_sample_architecture() -> ArchitectureSpecification:
    return ArchitectureSpecification(
        architecture_id="dev-platform",
        status=ArchitectureStatus.READY_FOR_REVIEW,
        title="Development Platform",
        requirement_summary={
            "business_goal": "Run platform and game backends on AWS for development.",
            "application_type": "Containerized web platform",
            "environment": "development",
            "functional_requirements": ["Platform API", "Game API", "Shared PostgreSQL"],
            "non_functional_requirements": ["Low cost", "Secure database access"],
            "constraints": ["Low cost development environment"],
        },
        cloud={
            "provider": "AWS",
            "region": "us-east-1",
            "region_rationale": "Chosen for broad service availability and common usage.",
        },
        solution="A shared ALB routes traffic to platform and game ECS services backed by a shared PostgreSQL database.",
        resources=[
            {
                "id": "dev-vpc",
                "name": "Development VPC",
                "provider_type": "aws_vpc",
                "category": "NETWORK",
                "scope": "VPC",
                "purpose": "Isolated network boundary.",
                "configuration": {},
            },
            {
                "id": "public-subnet-a",
                "name": "Public Subnet A",
                "provider_type": "aws_subnet",
                "category": "NETWORK",
                "scope": "PUBLIC_SUBNET",
                "purpose": "Hosts internet-facing resources.",
                "configuration": {},
            },
            {
                "id": "private-subnet-a",
                "name": "Private App Subnet A",
                "provider_type": "aws_subnet",
                "category": "NETWORK",
                "scope": "PRIVATE_SUBNET",
                "purpose": "Hosts private application services.",
                "configuration": {},
            },
            {
                "id": "nat-gw",
                "name": "NAT Gateway",
                "provider_type": "aws_nat_gateway",
                "category": "NETWORK",
                "scope": "PUBLIC_SUBNET",
                "purpose": "Handles outbound access for private workloads.",
                "configuration": {},
            },
            {
                "id": "alb",
                "name": "Application Load Balancer",
                "provider_type": "aws_lb",
                "category": "LOAD_BALANCING",
                "scope": "PUBLIC",
                "purpose": "Accepts public traffic and routes requests.",
                "configuration": {},
            },
            {
                "id": "ecs-cluster",
                "name": "ECS Cluster",
                "provider_type": "aws_ecs_cluster",
                "category": "CONTAINER",
                "scope": "PRIVATE",
                "purpose": "Runs container services.",
                "configuration": {},
            },
            {
                "id": "platform-service",
                "name": "Platform Backend Service",
                "provider_type": "aws_ecs_service",
                "category": "CONTAINER",
                "scope": "PRIVATE",
                "purpose": "Runs the platform API.",
                "configuration": {"desired_count": 1},
            },
            {
                "id": "game-service",
                "name": "Game Backend Service",
                "provider_type": "aws_ecs_service",
                "category": "CONTAINER",
                "scope": "PRIVATE",
                "purpose": "Runs game-related APIs.",
                "configuration": {"desired_count": 1},
            },
            {
                "id": "db-secret",
                "name": "Secrets Manager",
                "provider_type": "aws_secretsmanager_secret",
                "category": "SECURITY",
                "scope": "REGIONAL",
                "purpose": "Stores shared database credentials.",
                "configuration": {},
            },
            {
                "id": "shared-db",
                "name": "Shared PostgreSQL RDS",
                "provider_type": "aws_db_instance",
                "category": "DATABASE",
                "scope": "PRIVATE",
                "purpose": "Stores application data.",
                "configuration": {"engine": "postgres"},
            },
            {
                "id": "alb-sg",
                "name": "ALB Security Group",
                "provider_type": "aws_security_group",
                "category": "SECURITY",
                "scope": "PUBLIC",
                "purpose": "Allows inbound web traffic.",
                "configuration": {},
            },
            {
                "id": "app-listener",
                "name": "ALB Listener",
                "provider_type": "aws_lb_listener",
                "category": "LOAD_BALANCING",
                "scope": "PUBLIC",
                "purpose": "Handles HTTP listener rules.",
                "configuration": {},
            },
        ],
        relationships=[
            {"source_id": "alb", "target_id": "platform-service", "relationship_type": "ROUTES_TRAFFIC_TO", "label": "api/platform/*"},
            {"source_id": "alb", "target_id": "game-service", "relationship_type": "ROUTES_TRAFFIC_TO", "label": "api/games/*"},
            {"source_id": "platform-service", "target_id": "shared-db", "relationship_type": "READS_FROM", "label": "reads and writes"},
            {"source_id": "game-service", "target_id": "shared-db", "relationship_type": "READS_FROM", "label": "reads and writes"},
            {"source_id": "platform-service", "target_id": "db-secret", "relationship_type": "AUTHENTICATES_WITH", "label": "retrieves credentials"},
            {"source_id": "game-service", "target_id": "db-secret", "relationship_type": "AUTHENTICATES_WITH", "label": "retrieves credentials"},
        ],
        decisions=[
            {
                "title": "Why ECS Fargate",
                "decision": "Use ECS Fargate for development services.",
                "rationale": "It keeps the platform production-aligned without introducing Kubernetes overhead.",
                "alternatives_considered": [
                    {
                        "option": "Single EC2 VM",
                        "reason_not_selected": "It is cheaper, but it increases manual operations and weakens service isolation.",
                    }
                ],
            }
        ],
        security_considerations=["Secrets are stored in Secrets Manager."],
        reliability_considerations=["Managed services reduce recovery toil."],
        scalability_considerations=["Both services can scale independently later."],
        assumptions=["Traffic is low during development."],
        risks=[{"title": "Single AZ", "description": "Development-only", "severity": "MEDIUM", "mitigation": "Upgrade to multi-AZ for production."}],
    )


def test_cost_profile_is_present_for_low_cost_requests():
    architecture = build_sample_architecture()
    assert architecture.cost_profile is not None
    assert architecture.cost_profile.profile == "LOW_COST_DEVELOPMENT"


def test_nat_gateway_creates_cost_driver_warning():
    architecture = build_sample_architecture()
    reasons = [driver.reason for driver in architecture.cost_profile.main_cost_drivers]
    assert "NAT Gateway improves private networking but can become a noticeable cost driver in development." in reasons


def test_markdown_does_not_show_exact_prices():
    architecture = build_sample_architecture()
    renderer = MarkdownRenderer()
    diagrams = MermaidRenderer().render(architecture)
    report = renderer.render(architecture, diagrams)
    assert "$" not in report
    assert "/month" not in report.lower()


def test_high_level_diagram_excludes_low_level_networking_and_security():
    architecture = build_sample_architecture()
    simple_diagram = MermaidRenderer().render(architecture)["simple"]
    assert "Development VPC" not in simple_diagram
    assert "Public Subnet A" not in simple_diagram
    assert "ALB Security Group" not in simple_diagram
    assert "NAT Gateway" not in simple_diagram


def test_high_level_diagram_includes_business_facing_resources():
    architecture = build_sample_architecture()
    simple_diagram = MermaidRenderer().render(architecture)["simple"]
    assert "User / Client" in simple_diagram
    assert "Application Load Balancer" in simple_diagram
    assert "Platform Backend Service" in simple_diagram
    assert "Game Backend Service" in simple_diagram
    assert "Shared PostgreSQL RDS" in simple_diagram
    assert "Secrets Manager" in simple_diagram


def test_advanced_diagram_includes_vpc_subnets_and_nat():
    architecture = build_sample_architecture()
    advanced_diagram = MermaidRenderer().render(architecture)["advanced"]
    assert "Development VPC" in advanced_diagram
    assert "Public Subnets" in advanced_diagram
    assert "Private Data Subnets" in advanced_diagram
    assert "NAT Gateway" in advanced_diagram


def test_mermaid_labels_do_not_contain_duplicated_quotes():
    architecture = build_sample_architecture()
    diagrams = MermaidRenderer().render(architecture)
    assert '""' not in diagrams["simple"]
    assert '""' not in diagrams["advanced"]


def test_markdown_shows_simple_diagram_before_advanced_diagram():
    architecture = build_sample_architecture()
    renderer = MarkdownRenderer()
    diagrams = MermaidRenderer().render(architecture)
    report = renderer.render(architecture, diagrams)
    assert report.index("## 2. High-Level Architecture Diagram") < report.index("## 11. Advanced Technical Diagram")


def test_enum_values_display_as_clean_labels():
    assert format_enum_label(ArchitectureStatus.READY_FOR_REVIEW) == "Ready For Review"
    assert format_enum_label("MEDIUM") == "Medium"
    assert format_enum_label("NETWORK") == "Network"


def test_report_still_includes_detailed_decision_rationales():
    architecture = build_sample_architecture()
    renderer = MarkdownRenderer()
    diagrams = MermaidRenderer().render(architecture)
    report = renderer.render(architecture, diagrams)
    assert "Why ECS Fargate" in report
    assert "It keeps the platform production-aligned without introducing Kubernetes overhead." in report
    assert "Alternatives Considered" in report
