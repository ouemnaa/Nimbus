from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings
from app.schemas.architecture import GenerateOptions
from app.schemas.plan import TerraformGenerationPlan
from app.utils.naming import safe_identifier, safe_name

from .architecture_normalizer import NormalizedArchitecture, NormalizedResource, resource_cfg
from .architecture_validator import validate_architecture
from .repair_service import apply_repairs


@dataclass(frozen=True)
class PatternDefinition:
    pattern_id: str
    required_provider_types: set[str]
    optional_provider_types: set[str]
    derived_implementation_resources: list[dict[str, str]]
    required_user_inputs: list[str]
    safe_default_values: dict[str, Any]
    generated_file_set: list[str]
    validation_rules: list[str]
    warnings: list[str]


class ArchitecturePattern(Protocol):
    definition: PatternDefinition

    def matches(self, architecture: NormalizedArchitecture) -> bool:
        ...

    def plan(
        self,
        architecture: NormalizedArchitecture,
        options: GenerateOptions,
        settings: Settings,
    ) -> TerraformGenerationPlan:
        ...


def _project_name(options: GenerateOptions, settings: Settings) -> str:
    return safe_name(options.project_name or settings.default_project_name)


def _environment(options: GenerateOptions, settings: Settings) -> str:
    return safe_name(options.environment or settings.default_environment)


def _supported_resources(architecture: NormalizedArchitecture) -> list[str]:
    return sorted({resource.provider_type for resource in architecture.resources})


def _base_plan(
    pattern: PatternDefinition,
    architecture: NormalizedArchitecture,
    options: GenerateOptions,
    settings: Settings,
) -> dict[str, Any]:
    return {
        "pattern_id": pattern.pattern_id,
        "project_name": _project_name(options, settings),
        "environment": _environment(options, settings),
        "aws_region": options.aws_region or architecture.region,
        "architecture_id": architecture.architecture_id,
        "architecture_version": architecture.architecture_version,
        "required_inputs": list(pattern.required_user_inputs),
        "template_set": list(pattern.generated_file_set),
        "supported_resources": _supported_resources(architecture),
        "warnings": list(pattern.warnings),
        "next_steps": [],
    }


class StaticSitePattern:
    definition = PatternDefinition(
        pattern_id="static_site_s3_cloudfront_route53_https",
        required_provider_types={
            "aws_s3_bucket",
            "aws_cloudfront_distribution",
            "aws_acm_certificate",
            "aws_route53_zone",
        },
        optional_provider_types={
            "aws_cloudfront_origin_access_control",
            "aws_s3_bucket_policy",
            "aws_route53_record",
        },
        derived_implementation_resources=[
            {
                "type": "aws_s3_bucket_public_access_block",
                "name": "site_bucket",
                "reason": "S3 buckets should be private by default.",
            },
            {
                "type": "aws_s3_bucket_server_side_encryption_configuration",
                "name": "site_bucket",
                "reason": "Static assets should be encrypted at rest.",
            },
            {
                "type": "aws_acm_certificate_validation",
                "name": "site_certificate",
                "reason": "CloudFront requires a validated ACM certificate for HTTPS aliases.",
            },
        ],
        required_user_inputs=["domain_name", "hosted_zone_name", "bucket_name"],
        safe_default_values={
            "price_class": "PriceClass_100",
            "default_root_object": "index.html",
            "viewer_protocol_policy": "redirect-to-https",
            "spa_mode": True,
        },
        generated_file_set=[
            "versions.tf",
            "providers.tf",
            "variables.tf",
            "locals.tf",
            "s3.tf",
            "acm.tf",
            "cloudfront.tf",
            "dns.tf",
            "outputs.tf",
            "terraform.tfvars.example",
            "README.generated.md",
        ],
        validation_rules=[
            "CloudFront ACM certificates must use provider alias aws.us_east_1.",
            "S3 bucket policy must allow only the CloudFront distribution ARN.",
            "Route 53 hosted zone is looked up through data.aws_route53_zone.",
        ],
        warnings=[],
    )

    def matches(self, architecture: NormalizedArchitecture) -> bool:
        types = {resource.provider_type for resource in architecture.resources}
        return self.definition.required_provider_types.issubset(types)

    def plan(
        self,
        architecture: NormalizedArchitecture,
        options: GenerateOptions,
        settings: Settings,
    ) -> TerraformGenerationPlan:
        bucket = architecture.first("aws_s3_bucket")
        distribution = architecture.first("aws_cloudfront_distribution")
        certificate = architecture.first("aws_acm_certificate")
        zone = architecture.first("aws_route53_zone")
        oac = architecture.first("aws_cloudfront_origin_access_control")
        bucket_name = str(resource_cfg(bucket, "bucket_name", "bucket", default="") if bucket else "")
        domain_name = str(resource_cfg(certificate, "domain_name", default="dev.example.com") if certificate else "dev.example.com")
        zone_name = str(resource_cfg(zone, "domain_name", "name", default="example.com") if zone else "example.com")
        plan_data = _base_plan(self.definition, architecture, options, settings)
        derived = list(self.definition.derived_implementation_resources)
        derived.append({
            "type": "aws_cloudfront_origin_access_control",
            "name": (oac.label if oac else "cloudfront_oac"),
            "derived_from": bucket.id if bucket else "architecture",
            "reason": "CloudFront accesses the private S3 bucket through Origin Access Control.",
        })
        plan_data["derived_resources"] = derived
        plan_data["resources"] = {
            "bucket_label": bucket.label if bucket else "site_bucket",
            "distribution_label": distribution.label if distribution else "cdn",
            "certificate_label": certificate.label if certificate else "site_certificate",
            "zone_label": zone.label if zone else "site_zone",
            "oac_label": oac.label if oac else "cloudfront_oac",
            "bucket_name": bucket_name or "replace-with-globally-unique-bucket-name",
            "domain_name": domain_name,
            "hosted_zone_name": zone_name,
            "price_class": str(resource_cfg(distribution, "price_class", default=self.definition.safe_default_values["price_class"]) if distribution else self.definition.safe_default_values["price_class"]),
            "root_object": str(resource_cfg(distribution, "default_root_object", default=self.definition.safe_default_values["default_root_object"]) if distribution else self.definition.safe_default_values["default_root_object"]),
            "viewer_policy": str(resource_cfg(distribution, "viewer_protocol_policy", default=self.definition.safe_default_values["viewer_protocol_policy"]) if distribution else self.definition.safe_default_values["viewer_protocol_policy"]),
            "spa_mode": bool(resource_cfg(distribution, "spa_mode", "vite_spa", default=True) if distribution else True),
        }
        plan_data["next_steps"] = [
            "Create terraform.tfvars from terraform.tfvars.example with real domain_name, hosted_zone_name, and bucket_name.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
            "Run npm run build, aws s3 sync, and create a CloudFront invalidation after infrastructure is created.",
        ]
        return TerraformGenerationPlan(**plan_data)


class EcsFargateAlbRdsDevPattern:
    definition = PatternDefinition(
        pattern_id="ecs_fargate_alb_rds_dev",
        required_provider_types={"aws_vpc", "aws_lb", "aws_ecs_service", "aws_db_instance"},
        optional_provider_types={
            "aws_subnet",
            "aws_internet_gateway",
            "aws_nat_gateway",
            "aws_security_group",
            "aws_ecs_cluster",
            "aws_ecs_task_definition",
            "aws_db_subnet_group",
            "aws_secretsmanager_secret",
            "aws_secretsmanager_secret_version",
            "aws_cloudwatch_log_group",
            "aws_iam_role",
            "aws_eip",
            "random_password",
        },
        derived_implementation_resources=[
            {"type": "aws_ecs_task_definition", "name": "task_definition", "reason": "ECS service requires a task definition."},
            {"type": "aws_lb_target_group", "name": "target_group", "reason": "ALB-backed ECS service needs a target group."},
            {"type": "aws_lb_listener", "name": "http", "reason": "ALB requires a listener."},
            {"type": "aws_db_subnet_group", "name": "db_subnet_group", "reason": "RDS requires a DB subnet group."},
            {"type": "random_password", "name": "db_password", "reason": "RDS password must be generated, not hardcoded."},
            {"type": "aws_secretsmanager_secret_version", "name": "db_secret_version", "reason": "Generated DB credentials must be stored in Secrets Manager."},
        ],
        required_user_inputs=["container_image"],
        safe_default_values={"container_port": 80, "db_username": "nimbus_admin"},
        generated_file_set=[
            "versions.tf",
            "providers.tf",
            "variables.tf",
            "locals.tf",
            "networking.tf",
            "security_groups.tf",
            "load_balancing.tf",
            "iam.tf",
            "observability.tf",
            "secrets.tf",
            "database.tf",
            "ecs.tf",
            "outputs.tf",
            "terraform.tfvars.example",
            "README.generated.md",
        ],
        validation_rules=[
            "ALB needs at least two public subnets.",
            "RDS subnet group needs at least two private subnets.",
            "RDS must not be public.",
            "RDS security group only allows PostgreSQL from ECS security group.",
        ],
        warnings=[],
    )

    def matches(self, architecture: NormalizedArchitecture) -> bool:
        types = {resource.provider_type for resource in architecture.resources}
        return self.definition.required_provider_types.issubset(types)

    def plan(
        self,
        architecture: NormalizedArchitecture,
        options: GenerateOptions,
        settings: Settings,
    ) -> TerraformGenerationPlan:
        repair_state = apply_repairs(architecture) if options.allow_repairs else _empty_repair_state()
        warnings = list(repair_state.warnings)
        repairs = list(repair_state.repairs)
        derived = list(repair_state.derived_resources)
        _record_ecs_implementation_derivations(architecture, derived)
        alb = architecture.first("aws_lb")
        rds = architecture.first("aws_db_instance")
        ecs = architecture.first("aws_ecs_service")
        if alb and not resource_cfg(alb, "certificate_arn", "acm_certificate_arn", "CertificateArn"):
            warnings.append("HTTPS is not configured because no ACM certificate ARN was provided; the generated ALB listener uses HTTP port 80 only.")
        if rds and not resource_cfg(rds, "username", "master_username", "MasterUsername"):
            warnings.append("RDS username was missing; generated Terraform uses the safe variable default nimbus_admin.")
            repairs.append({
                "path": f"resources[{rds.id}].configuration.username",
                "action": "use_variable_default",
                "reason": "RDS username is required but can be safely represented as a configurable Terraform variable.",
                "result": "Created db_username with example default nimbus_admin.",
            })
        plan_data = _base_plan(self.definition, architecture, options, settings)
        plan_data["derived_resources"] = derived
        plan_data["repairs"] = repairs
        plan_data["warnings"] = warnings
        plan_data["resources"] = _ecs_context(architecture, options, settings)
        if ecs and not resource_cfg(ecs, "container_image", "image", "containerImage"):
            plan_data["required_inputs"] = ["container_image"]
        plan_data["next_steps"] = [
            "Review terraform.tfvars.example and provide a real container_image in an uncommitted terraform.tfvars file.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
            "Review the generated plan and AWS costs before any deployment.",
        ]
        return TerraformGenerationPlan(**plan_data)


def _empty_repair_state():
    class EmptyState:
        repairs: list[dict[str, str]] = []
        derived_resources: list[dict[str, str]] = []
        warnings: list[str] = []
    return EmptyState()


def _subnets(architecture: NormalizedArchitecture, public: bool) -> list[dict[str, Any]]:
    resources = architecture.by_type("aws_subnet")
    selected: list[NormalizedResource] = []
    for resource in resources:
        value = resource_cfg(resource, "public", "is_public", default=None)
        tier = str(resource_cfg(resource, "subnet_type", "network_tier", "tier", default=""))
        inferred_public = bool(value) if value is not None else ("public" in tier.lower() or "public" in resource.id.lower() or "public" in resource.name.lower())
        if inferred_public == public:
            selected.append(resource)
    result = []
    for index, resource in enumerate(selected):
        cidr = resource_cfg(resource, "cidr_block", "cidr", "CidrBlock")
        if not cidr:
            cidr = f"10.0.{index + (1 if public else 10)}.0/24"
        result.append(
            {
                "id": resource.id,
                "label": resource.label,
                "cidr": cidr,
                "az_index": index % 2,
            }
        )
    return result


def _record_ecs_implementation_derivations(architecture: NormalizedArchitecture, derived: list[dict[str, str]]) -> None:
    def add(type_: str, name: str, derived_from: str, reason: str) -> None:
        if not any(item["type"] == type_ and item["name"] == name for item in derived):
            derived.append({"type": type_, "name": name, "derived_from": derived_from, "reason": reason})

    public_subnets = _subnets(architecture, True)
    private_subnets = _subnets(architecture, False)
    vpc = architecture.first("aws_vpc")
    nat = architecture.first("aws_nat_gateway")
    if nat:
        add("aws_eip", safe_identifier(f"{nat.name}_eip"), nat.id, "NAT Gateway requires an Elastic IP allocation.")
    if public_subnets and vpc:
        add("aws_route_table", "public", vpc.id, "Public subnets require a route table.")
        for subnet in public_subnets:
            add("aws_route_table_association", f"{subnet['label']}_public", subnet["id"], "Public subnets require route table associations.")
        add("aws_route", "public_internet", vpc.id, "The Internet Gateway route is required for public subnets.")
    if private_subnets and vpc:
        add("aws_route_table", "private", vpc.id, "Private subnets require a route table.")
        for subnet in private_subnets:
            add("aws_route_table_association", f"{subnet['label']}_private", subnet["id"], "Private subnets require route table associations.")
        if nat:
            add("aws_route", "private_nat", nat.id, "Private subnets require a NAT route for outbound access.")


def _ecs_context(architecture: NormalizedArchitecture, options: GenerateOptions, settings: Settings) -> dict[str, Any]:
    vpc = architecture.first("aws_vpc")
    alb = architecture.first("aws_lb")
    ecs = architecture.first("aws_ecs_service")
    rds = architecture.first("aws_db_instance")
    nat = architecture.first("aws_nat_gateway")
    igw = architecture.first("aws_internet_gateway")
    alb_sg = architecture.first("aws_security_group")
    security_groups = architecture.by_type("aws_security_group")
    ecs_sg = next((item for item in security_groups if "ecs" in f"{item.id} {item.name}".lower()), security_groups[1] if len(security_groups) > 1 else alb_sg)
    rds_sg = next((item for item in security_groups if "rds" in f"{item.id} {item.name}".lower()), security_groups[2] if len(security_groups) > 2 else ecs_sg)
    target_group = architecture.first("aws_lb_target_group")
    execution_role = architecture.first("aws_iam_role")
    log_group = architecture.first("aws_cloudwatch_log_group")
    secret = architecture.first("aws_secretsmanager_secret")
    secret_version = architecture.first("aws_secretsmanager_secret_version")
    password = architecture.first("random_password")
    db_subnet_group = architecture.first("aws_db_subnet_group")
    public_subnets = _subnets(architecture, True)
    private_subnets = _subnets(architecture, False)
    if not public_subnets:
        public_subnets = private_subnets
    if not private_subnets:
        private_subnets = public_subnets
    return {
        "generator_version": settings.generator_version,
        "vpc_cidr": str(resource_cfg(vpc, "cidr_block", "cidr", "CidrBlock", default="10.0.0.0/16")),
        "container_port": int(resource_cfg(ecs, "container_port", "port", "containerPort", default=80) if ecs else 80),
        "container_name": str(resource_cfg(ecs, "container_name", "name", default="app") if ecs else "app"),
        "ecs_cpu": int(resource_cfg(ecs, "cpu", "task_cpu", default=256) if ecs else 256),
        "ecs_memory": int(resource_cfg(ecs, "memory", "task_memory", default=512) if ecs else 512),
        "ecs_desired_count": int(resource_cfg(ecs, "desired_count", "desiredCount", default=1) if ecs else 1),
        "db_username": str(resource_cfg(rds, "username", "master_username", "MasterUsername", default="nimbus_admin") if rds else "nimbus_admin"),
        "db_name": str(resource_cfg(rds, "db_name", "database_name", "DBName", default="nimbus") if rds else "nimbus"),
        "db_instance_class": str(resource_cfg(rds, "instance_class", "DBInstanceClass", default="db.t3.micro") if rds else "db.t3.micro"),
        "db_allocated_storage": int(resource_cfg(rds, "allocated_storage", "AllocatedStorage", default=20) if rds else 20),
        "db_multi_az": bool(resource_cfg(rds, "multi_az", "MultiAZ", default=False) if rds else False),
        "db_engine_version": str(resource_cfg(rds, "engine_version", "EngineVersion", default="15.5") if rds else "15.5"),
        "db_password_label": password.label if password else "db_password",
        "secret_label": secret.label if secret else "db_secret",
        "secret_version_label": secret_version.label if secret_version else "db_secret_version",
        "db_subnet_group_label": db_subnet_group.label if db_subnet_group else "db_subnet_group",
        "db_label": rds.label if rds else "postgres",
        "public_subnets": public_subnets,
        "private_subnets": private_subnets,
        # ecs_subnets and assign_public_ip are set by TerraformPlanBuilder
        # based on deployment_strategy from TerraformReasoningAgent.
        # Default to private subnets + no public IP (safe); plan builder overrides
        # for public_ecs_no_nat_low_cost_dev strategy.
        "ecs_subnets": private_subnets or public_subnets,
        "assign_public_ip": False,
        "vpc_label": vpc.label if vpc else "vpc",
        "igw_label": igw.label if igw else "internet_gateway",
        "nat_label": nat.label if nat else None,
        "eip_label": safe_identifier(f"{nat.name}_eip") if nat else "nat_eip",
        "alb_label": alb.label if alb else None,
        "alb_sg_label": alb_sg.label if alb_sg else "alb_sg",
        "ecs_sg_label": ecs_sg.label if ecs_sg else "ecs_sg",
        "rds_sg_label": rds_sg.label if rds_sg else "rds_sg",
        "target_group_label": target_group.label if target_group else "target_group",
        "listener_label": "application_load_balancer_listener",
        "ecs_cluster_label": (architecture.first("aws_ecs_cluster").label if architecture.first("aws_ecs_cluster") else "ecs_cluster"),
        "ecs_service_label": ecs.label if ecs else "ecs_service",
        "task_definition_label": (architecture.first("aws_ecs_task_definition").label if architecture.first("aws_ecs_task_definition") else "task_definition"),
        "ecs_execution_role_label": "ecs_task_execution_role",
        "log_group_label": log_group.label if log_group else "ecs_logs",
        "log_retention_days": int(resource_cfg(log_group, "retention_in_days", "retention", default=7) if log_group else 7),
        "health_check_path": str(resource_cfg(target_group, "health_check_path", "path", default="/") if target_group else "/"),
    }


class PatternRegistry:
    def __init__(self) -> None:
        self.patterns: list[ArchitecturePattern] = [
            StaticSitePattern(),
            EcsFargateAlbRdsDevPattern(),
        ]

    def detect(
        self,
        architecture: NormalizedArchitecture,
        options: GenerateOptions,
        settings: Settings,
    ) -> TerraformGenerationPlan | None:
        validation = validate_architecture(architecture)
        if validation.unsupported_resources:
            return None
        for pattern in self.patterns:
            if pattern.matches(architecture):
                plan = pattern.plan(architecture, options, settings)
                plan.warnings = [*validation.warnings, *plan.warnings]
                return plan
        return None

    def missing_pattern_message(self, architecture: NormalizedArchitecture) -> str:
        resource_types = sorted({resource.provider_type for resource in architecture.resources})
        return (
            "No Terraform generation pattern matched this architecture. "
            f"Observed provider types: {', '.join(resource_types) or 'none'}."
        )
