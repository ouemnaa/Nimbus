from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings
from app.planning.terraform_resource_plan_schema import (
    ArchitectureResourceMapping,
    DerivedResourceSpec,
    HCLValue,
    ProviderRequirement,
    TerraformDataSource,
    TerraformLocal,
    TerraformManagedResource,
    TerraformOutput,
    TerraformResourcePlan,
    TerraformVariable,
)
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
    required_relationships: list[str] | None = None
    iam_synthesis: str | None = None
    networking_synthesis: str | None = None
    file_renderer: str | None = None


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


def _lit(value: Any) -> HCLValue:
    return HCLValue(kind="literal", value=value)


def _expr(value: str) -> HCLValue:
    return HCLValue(kind="expr", value=value)


def _list(*items: HCLValue) -> HCLValue:
    return HCLValue(kind="list", items=list(items))


def _obj(**items: HCLValue) -> HCLValue:
    return HCLValue(kind="object", items=items)


def _block(type_: str, **body: HCLValue) -> HCLValue:
    return HCLValue(kind="block", type=type_, body=body)


def _relationship_values(architecture: NormalizedArchitecture) -> list[dict[str, Any]]:
    return [item for item in architecture.relationships if isinstance(item, dict)]


def _relationship_label(relationship: dict[str, Any]) -> str:
    return str(
        relationship.get("label")
        or relationship.get("name")
        or relationship.get("description")
        or relationship.get("type")
        or ""
    )


def _relationship_source(relationship: dict[str, Any]) -> str:
    return str(
        relationship.get("source")
        or relationship.get("source_id")
        or relationship.get("from")
        or relationship.get("source_resource_id")
        or ""
    )


def _relationship_target(relationship: dict[str, Any]) -> str:
    return str(
        relationship.get("target")
        or relationship.get("target_id")
        or relationship.get("to")
        or relationship.get("target_resource_id")
        or ""
    )


def _has_relationship(architecture: NormalizedArchitecture, source_type: str, target_type: str) -> bool:
    for relationship in _relationship_values(architecture):
        source = architecture.resource(_relationship_source(relationship))
        target = architecture.resource(_relationship_target(relationship))
        if source and target and source.provider_type == source_type and target.provider_type == target_type:
            return True
    return False


def _generic_template_set(*files: str) -> list[str]:
    return [
        "versions.tf",
        "providers.tf",
        "variables.tf",
        "locals.tf",
        *files,
        "outputs.tf",
        "terraform.tfvars.example",
        "README.generated.md",
    ]


def _common_variables(architecture: NormalizedArchitecture) -> list[TerraformVariable]:
    return [
        TerraformVariable(
            name="aws_region",
            type="string",
            description="AWS region.",
            default=_lit(architecture.region),
            required=True,
        ),
        TerraformVariable(name="project_name", type="string", description="Project name.", required=True),
        TerraformVariable(name="environment", type="string", description="Deployment environment.", default=_lit("development"), required=True),
    ]


def _common_locals() -> list[TerraformLocal]:
    return [
        TerraformLocal(name="environment_slug_raw", value=_expr('replace(lower(var.environment), "/[^a-z0-9-]/", "-")')),
        TerraformLocal(name="environment_slug", value=_expr('trim(replace(local.environment_slug_raw, "/-+/", "-"), "-")')),
        TerraformLocal(name="project_slug_raw", value=_expr('replace(lower(var.project_name), "/[^a-z0-9-]/", "-")')),
        TerraformLocal(name="project_slug", value=_expr('trim(replace(local.project_slug_raw, "/-+/", "-"), "-")')),
        TerraformLocal(name="short_environment_slug", value=_expr('substr(local.environment_slug != "" ? local.environment_slug : "dev", 0, 7)')),
        TerraformLocal(name="short_project_slug", value=_expr('substr(local.project_slug != "" ? local.project_slug : "nimbus", 0, 16)')),
        TerraformLocal(name="name_prefix", value=_expr('substr("${local.short_project_slug}-${local.short_environment_slug}", 0, 24)')),
        TerraformLocal(
            name="common_tags",
            value=_obj(
                Project=_expr("var.project_name"),
                Environment=_expr("var.environment"),
                ManagedBy=_lit("nimbus-terraform-generator"),
            ),
        ),
    ]


def _base_resource_plan(
    architecture: NormalizedArchitecture,
    pattern_name: str,
    *,
    include_random: bool = False,
) -> TerraformResourcePlan:
    providers = [ProviderRequirement(name="aws", source="hashicorp/aws", version="~> 5.0")]
    if include_random:
        providers.append(ProviderRequirement(name="random", source="hashicorp/random", version="~> 3.6"))
    return TerraformResourcePlan(
        draft_pattern_name=pattern_name,
        trusted_pattern=True,
        cloud_provider="aws",
        required_providers=providers,
        deployment_targets=["aws"],
        variables=_common_variables(architecture),
        locals=_common_locals(),
    )


def _mapping(resource: NormalizedResource, *addresses: str, status: str = "RENDERED", notes: str = "") -> ArchitectureResourceMapping:
    return ArchitectureResourceMapping(
        architecture_resource_id=resource.id,
        provider_type=resource.provider_type,
        mapping_status=status,
        terraform_addresses=list(addresses),
        notes=notes,
    )


def _derived(terraform_type: str, name: str, reason: str, file: str | None = None) -> DerivedResourceSpec:
    return DerivedResourceSpec(terraform_type=terraform_type, name=name, reason=reason, file=file)


def _derived_response_items(items: list[DerivedResourceSpec]) -> list[dict[str, Any]]:
    return [
        {"type": item.terraform_type, "name": item.name, "reason": item.reason}
        for item in items
    ]


def _default_http_route_key(architecture: NormalizedArchitecture) -> str:
    for relationship in _relationship_values(architecture):
        label = _relationship_label(relationship)
        if "/" in label:
            path = label[label.find("/"):]
            return f"ANY {path}"
    return "ANY /{proxy+}"


def _websocket_route_keys(architecture: NormalizedArchitecture) -> list[str]:
    keys: list[str] = []
    for relationship in _relationship_values(architecture):
        label = _relationship_label(relationship).strip()
        if label.startswith("$") or label in {"createLobby", "joinLobby", "leaveLobby", "startGame"}:
            keys.append(label)
    if not keys:
        keys = ["$connect", "$disconnect", "createLobby", "joinLobby", "leaveLobby", "startGame"]
    seen: set[str] = set()
    return [key for key in keys if not (key in seen or seen.add(key))]


def _lambda_runtime(resource: NormalizedResource | None, default: str = "python3.12") -> str:
    return str(resource_cfg(resource, "runtime", default=default) if resource else default)


def _lambda_handler(resource: NormalizedResource | None, default: str = "handler.main") -> str:
    return str(resource_cfg(resource, "handler", default=default) if resource else default)


def _name_from_resource(resource: NormalizedResource | None, fallback: str) -> str:
    return resource.label if resource else fallback


class ServerlessHttpApiLambdaDynamodbPattern:
    definition = PatternDefinition(
        pattern_id="serverless_http_api_lambda_dynamodb",
        required_provider_types={"aws_apigatewayv2_api", "aws_lambda_function", "aws_dynamodb_table"},
        optional_provider_types={"aws_iam_role", "aws_cloudwatch_log_group"},
        derived_implementation_resources=[
            {"type": "aws_apigatewayv2_integration", "name": "http_integration", "reason": "HTTP API requires Lambda integration."},
            {"type": "aws_apigatewayv2_route", "name": "http_route", "reason": "HTTP API requires at least one route."},
            {"type": "aws_lambda_permission", "name": "allow_http_api", "reason": "API Gateway must be allowed to invoke Lambda."},
            {"type": "aws_iam_role_policy", "name": "lambda_dynamodb_access", "reason": "Lambda needs scoped DynamoDB access."},
        ],
        required_user_inputs=["lambda_package_path"],
        safe_default_values={"route_key": "ANY /{proxy+}"},
        generated_file_set=_generic_template_set("api_gateway.tf", "lambda.tf", "database.tf", "iam.tf", "observability.tf"),
        validation_rules=["HTTP API must integrate with Lambda and permit invocation.", "Lambda IAM must be scoped to the DynamoDB table."],
        warnings=[],
        required_relationships=["aws_apigatewayv2_api -> aws_lambda_function", "aws_lambda_function -> aws_dynamodb_table"],
        iam_synthesis="Scoped Lambda execution role with DynamoDB and CloudWatch access.",
        networking_synthesis="Public HTTP API; no VPC networking required unless explicitly modeled.",
        file_renderer="generic_hcl_renderer",
    )

    def matches(self, architecture: NormalizedArchitecture) -> bool:
        types = {resource.provider_type for resource in architecture.resources}
        api = architecture.first("aws_apigatewayv2_api")
        protocol = str(resource_cfg(api, "protocol_type", default="HTTP")).upper() if api else "HTTP"
        return self.definition.required_provider_types.issubset(types) and protocol != "WEBSOCKET"

    def plan(self, architecture: NormalizedArchitecture, options: GenerateOptions, settings: Settings) -> TerraformGenerationPlan:
        api = architecture.first("aws_apigatewayv2_api")
        lambda_resource = architecture.first("aws_lambda_function")
        table = architecture.first("aws_dynamodb_table")
        route_key = _default_http_route_key(architecture)
        lambda_label = _name_from_resource(lambda_resource, "application_lambda")
        table_label = _name_from_resource(table, "application_table")
        api_label = _name_from_resource(api, "http_api")
        tf_plan = _base_resource_plan(architecture, self.definition.pattern_id)
        tf_plan.variables.append(
            TerraformVariable(name="lambda_package_path", type="string", description="Lambda deployment package path.", required=True)
        )
        tf_plan.resources.extend(
            [
                TerraformManagedResource(
                    terraform_type="aws_dynamodb_table",
                    name=table_label,
                    file="database.tf",
                    architecture_resource_id=table.id if table else None,
                    body={
                        "name": _expr('format("%s-table", local.name_prefix)'),
                        "billing_mode": _lit("PAY_PER_REQUEST"),
                        "hash_key": _lit("pk"),
                        "attribute": _list(_block("attribute", name=_lit("pk"), type=_lit("S"))),
                        "tags": _expr("local.common_tags"),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_iam_role",
                    name="lambda_execution_role",
                    file="iam.tf",
                    body={
                        "name": _expr('format("%s-lambda-role", local.name_prefix)'),
                        "assume_role_policy": _expr('jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="lambda.amazonaws.com"},Action="sts:AssumeRole"}]})'),
                        "tags": _expr("local.common_tags"),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_iam_role_policy_attachment",
                    name="lambda_basic_execution",
                    file="iam.tf",
                    body={
                        "role": _expr("aws_iam_role.lambda_execution_role.name"),
                        "policy_arn": _lit("arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_iam_role_policy",
                    name="lambda_dynamodb_access",
                    file="iam.tf",
                    body={
                        "name": _expr('format("%s-dynamodb-access", local.name_prefix)'),
                        "role": _expr("aws_iam_role.lambda_execution_role.id"),
                        "policy": _expr(f'jsonencode({{Version="2012-10-17",Statement=[{{Effect="Allow",Action=["dynamodb:GetItem","dynamodb:PutItem","dynamodb:UpdateItem","dynamodb:Query","dynamodb:Scan"],Resource=[aws_dynamodb_table.{table_label}.arn,format("%s/index/*", aws_dynamodb_table.{table_label}.arn)]}}]}})'),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_cloudwatch_log_group",
                    name=lambda_label,
                    file="observability.tf",
                    body={
                        "name": _expr(f'format("/aws/lambda/%s-{lambda_label}", local.name_prefix)'),
                        "retention_in_days": _lit(7),
                        "tags": _expr("local.common_tags"),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_lambda_function",
                    name=lambda_label,
                    file="lambda.tf",
                    architecture_resource_id=lambda_resource.id if lambda_resource else None,
                    depends_on=["aws_iam_role_policy_attachment.lambda_basic_execution"],
                    body={
                        "function_name": _expr(f'format("%s-{lambda_label}", local.name_prefix)'),
                        "role": _expr("aws_iam_role.lambda_execution_role.arn"),
                        "handler": _lit(_lambda_handler(lambda_resource)),
                        "runtime": _lit(_lambda_runtime(lambda_resource)),
                        "filename": _expr("var.lambda_package_path"),
                        "source_code_hash": _expr("filebase64sha256(var.lambda_package_path)"),
                        "memory_size": _lit(int(resource_cfg(lambda_resource, "memory_size", default=256) if lambda_resource else 256)),
                        "timeout": _lit(int(resource_cfg(lambda_resource, "timeout", default=30) if lambda_resource else 30)),
                        "environment": _block("environment", variables=_obj(TABLE_NAME=_expr(f"aws_dynamodb_table.{table_label}.name"))),
                        "tags": _expr("local.common_tags"),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_apigatewayv2_api",
                    name=api_label,
                    file="api_gateway.tf",
                    architecture_resource_id=api.id if api else None,
                    body={"name": _expr(f'format("%s-{api_label}", local.name_prefix)'), "protocol_type": _lit("HTTP"), "tags": _expr("local.common_tags")},
                ),
                TerraformManagedResource(
                    terraform_type="aws_apigatewayv2_integration",
                    name="http_integration",
                    file="api_gateway.tf",
                    body={
                        "api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"),
                        "integration_type": _lit("AWS_PROXY"),
                        "integration_uri": _expr(f"aws_lambda_function.{lambda_label}.invoke_arn"),
                        "payload_format_version": _lit("2.0"),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_apigatewayv2_route",
                    name="http_route",
                    file="api_gateway.tf",
                    body={"api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"), "route_key": _lit(route_key), "target": _expr('format("integrations/%s", aws_apigatewayv2_integration.http_integration.id)')},
                ),
                TerraformManagedResource(
                    terraform_type="aws_apigatewayv2_stage",
                    name="default",
                    file="api_gateway.tf",
                    body={"api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"), "name": _lit("$default"), "auto_deploy": _lit(True), "tags": _expr("local.common_tags")},
                ),
                TerraformManagedResource(
                    terraform_type="aws_lambda_permission",
                    name="allow_http_api",
                    file="lambda.tf",
                    body={
                        "statement_id": _lit("AllowExecutionFromAPIGateway"),
                        "action": _lit("lambda:InvokeFunction"),
                        "function_name": _expr(f"aws_lambda_function.{lambda_label}.function_name"),
                        "principal": _lit("apigateway.amazonaws.com"),
                        "source_arn": _expr(f'format("%s/*/*", aws_apigatewayv2_api.{api_label}.execution_arn)'),
                    },
                ),
            ]
        )
        tf_plan.outputs.extend(
            [
                TerraformOutput(name="http_api_endpoint", value=_expr(f"aws_apigatewayv2_stage.default.invoke_url")),
                TerraformOutput(name="dynamodb_table_name", value=_expr(f"aws_dynamodb_table.{table_label}.name")),
            ]
        )
        if lambda_resource:
            tf_plan.architecture_resource_mappings.append(_mapping(lambda_resource, f"aws_lambda_function.{lambda_label}", f"aws_cloudwatch_log_group.{lambda_label}"))
        if api:
            tf_plan.architecture_resource_mappings.append(_mapping(api, f"aws_apigatewayv2_api.{api_label}", "aws_apigatewayv2_integration.http_integration", "aws_apigatewayv2_route.http_route", "aws_apigatewayv2_stage.default"))
        if table:
            tf_plan.architecture_resource_mappings.append(_mapping(table, f"aws_dynamodb_table.{table_label}"))
        tf_plan.derived_resources.extend(
            [
                _derived("aws_apigatewayv2_integration", "http_integration", "HTTP API Lambda integration.", "api_gateway.tf"),
                _derived("aws_apigatewayv2_route", "http_route", "HTTP API route.", "api_gateway.tf"),
                _derived("aws_lambda_permission", "allow_http_api", "Allow API Gateway to invoke Lambda.", "lambda.tf"),
            ]
        )
        plan_data = _base_plan(self.definition, architecture, options, settings)
        plan_data["terraform_resource_plan"] = tf_plan
        plan_data["derived_resources"] = _derived_response_items(tf_plan.derived_resources)
        plan_data["required_inputs"] = ["lambda_package_path"]
        plan_data["next_steps"] = [
            "Provide lambda_package_path in terraform.tfvars or through your CI pipeline.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
        ]
        return TerraformGenerationPlan(**plan_data)


class WebsocketLobbyLambdaDynamodbPattern:
    definition = PatternDefinition(
        pattern_id="websocket_lobby_lambda_dynamodb",
        required_provider_types={"aws_apigatewayv2_api", "aws_lambda_function", "aws_dynamodb_table"},
        optional_provider_types={"aws_iam_role", "aws_cloudwatch_log_group"},
        derived_implementation_resources=[
            {"type": "aws_apigatewayv2_integration", "name": "websocket_integrations", "reason": "WebSocket API requires Lambda integrations."},
            {"type": "aws_apigatewayv2_route", "name": "websocket_routes", "reason": "WebSocket API requires routes for connect/disconnect and lobby actions."},
            {"type": "aws_lambda_permission", "name": "allow_websocket_api", "reason": "API Gateway must be allowed to invoke Lambda."},
        ],
        required_user_inputs=["lambda_package_path"],
        safe_default_values={},
        generated_file_set=_generic_template_set("api_gateway.tf", "lambda.tf", "database.tf", "iam.tf", "observability.tf"),
        validation_rules=["WebSocket routes must map to Lambda integrations.", "IAM policy must allow manage connections only for the generated API."],
        warnings=[],
        required_relationships=["aws_apigatewayv2_api -> aws_lambda_function", "aws_lambda_function -> aws_dynamodb_table"],
        iam_synthesis="Scoped Lambda execution role with DynamoDB and execute-api:ManageConnections access.",
        networking_synthesis="Managed WebSocket API; no VPC networking unless explicitly modeled.",
        file_renderer="generic_hcl_renderer",
    )

    def matches(self, architecture: NormalizedArchitecture) -> bool:
        types = {resource.provider_type for resource in architecture.resources}
        api = architecture.first("aws_apigatewayv2_api")
        protocol = str(resource_cfg(api, "protocol_type", default="")).upper() if api else ""
        labels = " ".join(_relationship_label(item) for item in _relationship_values(architecture)).lower()
        return self.definition.required_provider_types.issubset(types) and (protocol == "WEBSOCKET" or "lobby" in labels or "$connect" in labels)

    def plan(self, architecture: NormalizedArchitecture, options: GenerateOptions, settings: Settings) -> TerraformGenerationPlan:
        api = architecture.first("aws_apigatewayv2_api")
        table = architecture.first("aws_dynamodb_table")
        lambdas = architecture.by_type("aws_lambda_function") or [architecture.first("aws_lambda_function")]
        route_keys = _websocket_route_keys(architecture)
        table_label = _name_from_resource(table, "lobby_state")
        api_label = _name_from_resource(api, "lobby_websocket_api")
        tf_plan = _base_resource_plan(architecture, self.definition.pattern_id)
        tf_plan.variables.append(TerraformVariable(name="lambda_package_path", type="string", description="Lambda deployment package path.", required=True))
        tf_plan.resources.append(
            TerraformManagedResource(
                terraform_type="aws_dynamodb_table",
                name=table_label,
                file="database.tf",
                architecture_resource_id=table.id if table else None,
                body={
                    "name": _expr('format("%s-lobby-state", local.name_prefix)'),
                    "billing_mode": _lit("PAY_PER_REQUEST"),
                    "hash_key": _lit("pk"),
                    "attribute": _list(_block("attribute", name=_lit("pk"), type=_lit("S"))),
                    "tags": _expr("local.common_tags"),
                },
            )
        )
        tf_plan.resources.extend(
            [
                TerraformManagedResource(
                    terraform_type="aws_iam_role",
                    name="lambda_execution_role",
                    file="iam.tf",
                    body={
                        "name": _expr('format("%s-lambda-role", local.name_prefix)'),
                        "assume_role_policy": _expr('jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="lambda.amazonaws.com"},Action="sts:AssumeRole"}]})'),
                        "tags": _expr("local.common_tags"),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_iam_role_policy_attachment",
                    name="lambda_basic_execution",
                    file="iam.tf",
                    body={"role": _expr("aws_iam_role.lambda_execution_role.name"), "policy_arn": _lit("arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")},
                ),
                TerraformManagedResource(
                    terraform_type="aws_iam_role_policy",
                    name="websocket_access",
                    file="iam.tf",
                    body={
                        "name": _expr('format("%s-websocket-access", local.name_prefix)'),
                        "role": _expr("aws_iam_role.lambda_execution_role.id"),
                        "policy": _expr(f'jsonencode({{Version="2012-10-17",Statement=[{{Effect="Allow",Action=["dynamodb:GetItem","dynamodb:PutItem","dynamodb:UpdateItem","dynamodb:Query"],Resource=[aws_dynamodb_table.{table_label}.arn,format("%s/index/*", aws_dynamodb_table.{table_label}.arn)]}},{{Effect="Allow",Action=["execute-api:ManageConnections"],Resource=[format("%s/*", aws_apigatewayv2_api.{api_label}.execution_arn)]}}]}})'),
                    },
                ),
                TerraformManagedResource(
                    terraform_type="aws_apigatewayv2_api",
                    name=api_label,
                    file="api_gateway.tf",
                    architecture_resource_id=api.id if api else None,
                    body={"name": _expr(f'format("%s-{api_label}", local.name_prefix)'), "protocol_type": _lit("WEBSOCKET"), "route_selection_expression": _lit("$request.body.action"), "tags": _expr("local.common_tags")},
                ),
                TerraformManagedResource(
                    terraform_type="aws_apigatewayv2_stage",
                    name="default",
                    file="api_gateway.tf",
                    body={"api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"), "name": _lit("$default"), "auto_deploy": _lit(True), "tags": _expr("local.common_tags")},
                ),
            ]
        )
        for index, lambda_resource in enumerate([item for item in lambdas if item]):
            lambda_label = lambda_resource.label
            integration_name = f"{lambda_label}_integration"
            permission_name = f"{lambda_label}_permission"
            route_key = route_keys[index] if index < len(route_keys) else route_keys[-1]
            route_name = safe_identifier(route_key.replace("$", "system_").replace("/", "_").replace("+", "plus"))
            tf_plan.resources.extend(
                [
                    TerraformManagedResource(
                        terraform_type="aws_cloudwatch_log_group",
                        name=lambda_label,
                        file="observability.tf",
                        body={"name": _expr(f'format("/aws/lambda/%s-{lambda_label}", local.name_prefix)'), "retention_in_days": _lit(7), "tags": _expr("local.common_tags")},
                    ),
                    TerraformManagedResource(
                        terraform_type="aws_lambda_function",
                        name=lambda_label,
                        file="lambda.tf",
                        architecture_resource_id=lambda_resource.id,
                        depends_on=["aws_iam_role_policy_attachment.lambda_basic_execution"],
                        body={
                            "function_name": _expr(f'format("%s-{lambda_label}", local.name_prefix)'),
                            "role": _expr("aws_iam_role.lambda_execution_role.arn"),
                            "handler": _lit(_lambda_handler(lambda_resource)),
                            "runtime": _lit(_lambda_runtime(lambda_resource)),
                            "filename": _expr("var.lambda_package_path"),
                            "source_code_hash": _expr("filebase64sha256(var.lambda_package_path)"),
                            "memory_size": _lit(int(resource_cfg(lambda_resource, "memory_size", default=256))),
                            "timeout": _lit(int(resource_cfg(lambda_resource, "timeout", default=30))),
                            "environment": _block("environment", variables=_obj(TABLE_NAME=_expr(f"aws_dynamodb_table.{table_label}.name"))),
                            "tags": _expr("local.common_tags"),
                        },
                    ),
                    TerraformManagedResource(
                        terraform_type="aws_apigatewayv2_integration",
                        name=integration_name,
                        file="api_gateway.tf",
                        body={"api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"), "integration_type": _lit("AWS_PROXY"), "integration_uri": _expr(f"aws_lambda_function.{lambda_label}.invoke_arn")},
                    ),
                    TerraformManagedResource(
                        terraform_type="aws_apigatewayv2_route",
                        name=route_name,
                        file="api_gateway.tf",
                        body={"api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"), "route_key": _lit(route_key), "target": _expr(f'format("integrations/%s", aws_apigatewayv2_integration.{integration_name}.id)')},
                    ),
                    TerraformManagedResource(
                        terraform_type="aws_lambda_permission",
                        name=permission_name,
                        file="lambda.tf",
                        body={
                            "statement_id": _lit(f"AllowWebsocketInvoke{index}"),
                            "action": _lit("lambda:InvokeFunction"),
                            "function_name": _expr(f"aws_lambda_function.{lambda_label}.function_name"),
                            "principal": _lit("apigateway.amazonaws.com"),
                            "source_arn": _expr(f'format("%s/*", aws_apigatewayv2_api.{api_label}.execution_arn)'),
                        },
                    ),
                ]
            )
            tf_plan.architecture_resource_mappings.append(_mapping(lambda_resource, f"aws_lambda_function.{lambda_label}", f"aws_cloudwatch_log_group.{lambda_label}", f"aws_apigatewayv2_integration.{integration_name}", f"aws_apigatewayv2_route.{route_name}"))
        if api:
            tf_plan.architecture_resource_mappings.append(_mapping(api, f"aws_apigatewayv2_api.{api_label}", "aws_apigatewayv2_stage.default"))
        if table:
            tf_plan.architecture_resource_mappings.append(_mapping(table, f"aws_dynamodb_table.{table_label}"))
        tf_plan.outputs.append(TerraformOutput(name="websocket_api_endpoint", value=_expr(f"aws_apigatewayv2_stage.default.invoke_url")))
        plan_data = _base_plan(self.definition, architecture, options, settings)
        plan_data["terraform_resource_plan"] = tf_plan
        plan_data["derived_resources"] = _derived_response_items(tf_plan.derived_resources)
        plan_data["required_inputs"] = ["lambda_package_path"]
        plan_data["next_steps"] = [
            "Package the Lambda handlers and provide lambda_package_path.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
        ]
        return TerraformGenerationPlan(**plan_data)


class AsyncProcessingS3SqsWorkerPattern:
    definition = PatternDefinition(
        pattern_id="async_processing_s3_sqs_worker",
        required_provider_types={"aws_s3_bucket", "aws_sqs_queue", "aws_dynamodb_table"},
        optional_provider_types={"aws_lambda_function", "aws_ecs_service", "aws_cloudwatch_log_group"},
        derived_implementation_resources=[
            {"type": "aws_s3_bucket_notification", "name": "source_events", "reason": "S3 uploads must enqueue work items."},
            {"type": "aws_lambda_event_source_mapping", "name": "worker_queue", "reason": "Worker Lambda must consume the queue."},
            {"type": "aws_iam_role_policy", "name": "worker_queue_access", "reason": "Worker needs scoped S3/SQS/DynamoDB access."},
        ],
        required_user_inputs=["lambda_package_path"],
        safe_default_values={},
        generated_file_set=_generic_template_set("storage.tf", "lambda.tf", "database.tf", "iam.tf", "observability.tf"),
        validation_rules=["S3 must notify SQS or the worker path is incomplete.", "Worker must consume SQS and update the job status store."],
        warnings=[],
        required_relationships=["aws_s3_bucket -> aws_sqs_queue", "aws_sqs_queue -> worker", "worker -> aws_dynamodb_table"],
        iam_synthesis="Scoped worker execution role with S3, SQS, DynamoDB, and logging access.",
        networking_synthesis="Event-driven managed services; no VPC networking required unless explicitly modeled.",
        file_renderer="generic_hcl_renderer",
    )

    def matches(self, architecture: NormalizedArchitecture) -> bool:
        types = {resource.provider_type for resource in architecture.resources}
        return {"aws_s3_bucket", "aws_sqs_queue", "aws_dynamodb_table"}.issubset(types) and "aws_lambda_function" in types and _has_relationship(architecture, "aws_s3_bucket", "aws_sqs_queue")

    def plan(self, architecture: NormalizedArchitecture, options: GenerateOptions, settings: Settings) -> TerraformGenerationPlan:
        buckets = architecture.by_type("aws_s3_bucket")
        source_bucket = buckets[0] if buckets else None
        queue = architecture.first("aws_sqs_queue")
        table = architecture.first("aws_dynamodb_table")
        worker = architecture.first("aws_lambda_function")
        bucket_label = _name_from_resource(source_bucket, "source_bucket")
        queue_label = _name_from_resource(queue, "work_queue")
        dlq_label = f"{queue_label}_dlq"
        table_label = _name_from_resource(table, "job_status")
        worker_label = _name_from_resource(worker, "worker")
        tf_plan = _base_resource_plan(architecture, self.definition.pattern_id)
        tf_plan.variables.append(TerraformVariable(name="lambda_package_path", type="string", description="Worker Lambda deployment package path.", required=True))
        tf_plan.resources.extend(
            [
                TerraformManagedResource(terraform_type="aws_s3_bucket", name=bucket_label, file="storage.tf", architecture_resource_id=source_bucket.id if source_bucket else None, body={"bucket": _expr(f'format("%s-{bucket_label.replace("_", "-")}", local.name_prefix)'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_s3_bucket_public_access_block", name=bucket_label, file="storage.tf", body={"bucket": _expr(f"aws_s3_bucket.{bucket_label}.id"), "block_public_acls": _lit(True), "block_public_policy": _lit(True), "ignore_public_acls": _lit(True), "restrict_public_buckets": _lit(True)}),
                TerraformManagedResource(terraform_type="aws_s3_bucket_server_side_encryption_configuration", name=bucket_label, file="storage.tf", body={"bucket": _expr(f"aws_s3_bucket.{bucket_label}.id"), "rule": _block("rule", apply_server_side_encryption_by_default=_block("apply_server_side_encryption_by_default", sse_algorithm=_lit("AES256")))}),
                TerraformManagedResource(terraform_type="aws_sqs_queue", name=dlq_label, file="storage.tf", body={"name": _expr(f'format("%s-{dlq_label.replace("_", "-")}", local.name_prefix)'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_sqs_queue", name=queue_label, file="storage.tf", architecture_resource_id=queue.id if queue else None, body={"name": _expr(f'format("%s-{queue_label.replace("_", "-")}", local.name_prefix)'), "redrive_policy": _expr(f'jsonencode({{deadLetterTargetArn=aws_sqs_queue.{dlq_label}.arn,maxReceiveCount=5}})'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_s3_bucket_notification", name="source_events", file="storage.tf", body={"bucket": _expr(f"aws_s3_bucket.{bucket_label}.id"), "queue": _list(_block("queue", queue_arn=_expr(f"aws_sqs_queue.{queue_label}.arn"), events=_list(_lit("s3:ObjectCreated:*"))))}),
                TerraformManagedResource(terraform_type="aws_dynamodb_table", name=table_label, file="database.tf", architecture_resource_id=table.id if table else None, body={"name": _expr('format("%s-job-status", local.name_prefix)'), "billing_mode": _lit("PAY_PER_REQUEST"), "hash_key": _lit("job_id"), "attribute": _list(_block("attribute", name=_lit("job_id"), type=_lit("S"))), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_iam_role", name="worker_role", file="iam.tf", body={"name": _expr('format("%s-worker-role", local.name_prefix)'), "assume_role_policy": _expr('jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="lambda.amazonaws.com"},Action="sts:AssumeRole"}]})'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_iam_role_policy_attachment", name="worker_basic_execution", file="iam.tf", body={"role": _expr("aws_iam_role.worker_role.name"), "policy_arn": _lit("arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")}),
                TerraformManagedResource(terraform_type="aws_iam_role_policy", name="worker_queue_access", file="iam.tf", body={"name": _expr('format("%s-worker-access", local.name_prefix)'), "role": _expr("aws_iam_role.worker_role.id"), "policy": _expr(f'jsonencode({{Version="2012-10-17",Statement=[{{Effect="Allow",Action=["s3:GetObject","s3:ListBucket"],Resource=[aws_s3_bucket.{bucket_label}.arn,format("%s/*", aws_s3_bucket.{bucket_label}.arn)]}},{{Effect="Allow",Action=["sqs:ReceiveMessage","sqs:DeleteMessage","sqs:GetQueueAttributes"],Resource=[aws_sqs_queue.{queue_label}.arn]}},{{Effect="Allow",Action=["dynamodb:GetItem","dynamodb:PutItem","dynamodb:UpdateItem"],Resource=[aws_dynamodb_table.{table_label}.arn]}}]}})')}),
                TerraformManagedResource(terraform_type="aws_cloudwatch_log_group", name=worker_label, file="observability.tf", body={"name": _expr(f'format("/aws/lambda/%s-{worker_label}", local.name_prefix)'), "retention_in_days": _lit(7), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_lambda_function", name=worker_label, file="lambda.tf", architecture_resource_id=worker.id if worker else None, depends_on=["aws_iam_role_policy_attachment.worker_basic_execution"], body={"function_name": _expr(f'format("%s-{worker_label}", local.name_prefix)'), "role": _expr("aws_iam_role.worker_role.arn"), "handler": _lit(_lambda_handler(worker)), "runtime": _lit(_lambda_runtime(worker)), "filename": _expr("var.lambda_package_path"), "source_code_hash": _expr("filebase64sha256(var.lambda_package_path)"), "memory_size": _lit(int(resource_cfg(worker, "memory_size", default=512) if worker else 512)), "timeout": _lit(int(resource_cfg(worker, "timeout", default=60) if worker else 60)), "environment": _block("environment", variables=_obj(SOURCE_BUCKET=_expr(f"aws_s3_bucket.{bucket_label}.bucket"), JOB_QUEUE_URL=_expr(f"aws_sqs_queue.{queue_label}.id"), JOB_STATUS_TABLE=_expr(f"aws_dynamodb_table.{table_label}.name"))), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_lambda_event_source_mapping", name="worker_queue", file="lambda.tf", body={"event_source_arn": _expr(f"aws_sqs_queue.{queue_label}.arn"), "function_name": _expr(f"aws_lambda_function.{worker_label}.arn"), "batch_size": _lit(10)}),
            ]
        )
        if source_bucket:
            tf_plan.architecture_resource_mappings.append(_mapping(source_bucket, f"aws_s3_bucket.{bucket_label}", f"aws_s3_bucket_notification.source_events"))
        if queue:
            tf_plan.architecture_resource_mappings.append(_mapping(queue, f"aws_sqs_queue.{queue_label}", f"aws_lambda_event_source_mapping.worker_queue"))
        if worker:
            tf_plan.architecture_resource_mappings.append(_mapping(worker, f"aws_lambda_function.{worker_label}", f"aws_cloudwatch_log_group.{worker_label}"))
        if table:
            tf_plan.architecture_resource_mappings.append(_mapping(table, f"aws_dynamodb_table.{table_label}"))
        tf_plan.outputs.extend([TerraformOutput(name="source_bucket_name", value=_expr(f"aws_s3_bucket.{bucket_label}.bucket")), TerraformOutput(name="queue_url", value=_expr(f"aws_sqs_queue.{queue_label}.id"))])
        plan_data = _base_plan(self.definition, architecture, options, settings)
        plan_data["terraform_resource_plan"] = tf_plan
        plan_data["required_inputs"] = ["lambda_package_path"]
        plan_data["derived_resources"] = _derived_response_items(tf_plan.derived_resources)
        plan_data["next_steps"] = [
            "Package the worker Lambda and set lambda_package_path.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
        ]
        return TerraformGenerationPlan(**plan_data)


class SecureInternalDashboardEcsRdsCognitoPattern:
    definition = PatternDefinition(
        pattern_id="secure_internal_dashboard_ecs_rds_cognito",
        required_provider_types={"aws_lb", "aws_ecs_service", "aws_db_instance", "aws_cognito_user_pool"},
        optional_provider_types={"aws_cognito_user_pool_client", "aws_vpc", "aws_subnet", "aws_secretsmanager_secret", "aws_cloudwatch_log_group", "aws_s3_bucket"},
        derived_implementation_resources=[{"type": "aws_lb_listener_rule", "name": "authenticate_dashboard", "reason": "ALB must authenticate users with Cognito before forwarding to ECS."}],
        required_user_inputs=["container_image"],
        safe_default_values={"container_port": 80},
        generated_file_set=_generic_template_set("networking.tf", "security_groups.tf", "iam.tf", "compute.tf", "database.tf", "secrets.tf", "storage.tf", "observability.tf"),
        validation_rules=["ALB listener must authenticate with Cognito before forwarding.", "RDS must remain private.", "ECS must not be internet-facing directly."],
        warnings=[],
        required_relationships=["aws_lb -> aws_ecs_service", "aws_ecs_service -> aws_db_instance", "aws_lb -> aws_cognito_user_pool"],
        iam_synthesis="ECS task execution role and Secrets Manager access for database credentials.",
        networking_synthesis="ALB public entry, ECS private networking, private PostgreSQL, S3 audit storage.",
        file_renderer="generic_hcl_renderer",
    )

    def matches(self, architecture: NormalizedArchitecture) -> bool:
        types = {resource.provider_type for resource in architecture.resources}
        return self.definition.required_provider_types.issubset(types)

    def plan(self, architecture: NormalizedArchitecture, options: GenerateOptions, settings: Settings) -> TerraformGenerationPlan:
        alb = architecture.first("aws_lb")
        ecs = architecture.first("aws_ecs_service")
        rds = architecture.first("aws_db_instance")
        pool = architecture.first("aws_cognito_user_pool")
        pool_client = architecture.first("aws_cognito_user_pool_client")
        audit_bucket = architecture.first("aws_s3_bucket")
        tf_plan = _base_resource_plan(architecture, self.definition.pattern_id, include_random=True)
        tf_plan.variables.extend(
            [
                TerraformVariable(name="container_image", type="string", description="Dashboard container image.", required=True),
                TerraformVariable(name="vpc_id", type="string", description="VPC ID for the dashboard stack.", required=True),
                TerraformVariable(name="public_subnet_ids", type="list(string)", description="Public ALB subnets.", required=True),
                TerraformVariable(name="private_subnet_ids", type="list(string)", description="Private ECS and RDS subnets.", required=True),
            ]
        )
        alb_label = _name_from_resource(alb, "dashboard_alb")
        ecs_label = _name_from_resource(ecs, "dashboard_service")
        pool_label = _name_from_resource(pool, "dashboard_users")
        pool_client_label = _name_from_resource(pool_client, "dashboard_client")
        db_label = _name_from_resource(rds, "dashboard_db")
        bucket_label = _name_from_resource(audit_bucket, "audit_logs")
        tf_plan.resources.extend(
            [
                TerraformManagedResource(terraform_type="aws_s3_bucket", name=bucket_label, file="storage.tf", architecture_resource_id=audit_bucket.id if audit_bucket else None, body={"bucket": _expr(f'format("%s-{bucket_label.replace("_", "-")}", local.name_prefix)'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_s3_bucket_public_access_block", name=bucket_label, file="storage.tf", body={"bucket": _expr(f"aws_s3_bucket.{bucket_label}.id"), "block_public_acls": _lit(True), "block_public_policy": _lit(True), "ignore_public_acls": _lit(True), "restrict_public_buckets": _lit(True)}),
                TerraformManagedResource(terraform_type="aws_cognito_user_pool", name=pool_label, file="compute.tf", architecture_resource_id=pool.id if pool else None, body={"name": _expr(f'format("%s-{pool_label}", local.name_prefix)'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_cognito_user_pool_client", name=pool_client_label, file="compute.tf", architecture_resource_id=pool_client.id if pool_client else None, body={"name": _expr(f'format("%s-{pool_client_label}", local.name_prefix)'), "user_pool_id": _expr(f"aws_cognito_user_pool.{pool_label}.id"), "generate_secret": _lit(False), "allowed_oauth_flows_user_pool_client": _lit(True), "allowed_oauth_flows": _list(_lit("code")), "allowed_oauth_scopes": _list(_lit("openid"), _lit("email"), _lit("profile")), "callback_urls": _list(_lit("https://example.internal/callback"))}),
                TerraformManagedResource(terraform_type="aws_lb", name=alb_label, file="compute.tf", architecture_resource_id=alb.id if alb else None, body={"name": _expr('format("%s-alb", local.name_prefix)'), "load_balancer_type": _lit("application"), "internal": _lit(False), "subnets": _expr("var.public_subnet_ids"), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="random_password", name="db_password", file="secrets.tf", body={"length": _lit(32), "special": _lit(True), "override_special": _lit("!#$%&*()-_=+[]{}<>:?")}),
                TerraformManagedResource(terraform_type="aws_secretsmanager_secret", name="db_credentials", file="secrets.tf", body={"name": _expr('format("%s/dashboard-db", local.name_prefix)'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_secretsmanager_secret_version", name="db_credentials_current", file="secrets.tf", body={"secret_id": _expr("aws_secretsmanager_secret.db_credentials.id"), "secret_string": _expr(f'jsonencode({{username="nimbus_admin",password=random_password.db_password.result,database="{db_label}"}})')}),
                TerraformManagedResource(terraform_type="aws_cloudwatch_log_group", name=ecs_label, file="observability.tf", body={"name": _expr(f'format("/ecs/%s-{ecs_label}", local.name_prefix)'), "retention_in_days": _lit(7), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_ecs_cluster", name="dashboard_cluster", file="compute.tf", body={"name": _expr('format("%s-dashboard", local.name_prefix)'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_ecs_task_definition", name="dashboard_task", file="compute.tf", body={"family": _expr('format("%s-dashboard", local.name_prefix)'), "network_mode": _lit("awsvpc"), "requires_compatibilities": _list(_lit("FARGATE")), "cpu": _lit("256"), "memory": _lit("512"), "execution_role_arn": _expr("aws_iam_role.dashboard_task_execution_role.arn"), "container_definitions": _expr(f'jsonencode([{{name="{ecs_label}",image=var.container_image,essential=true,portMappings=[{{containerPort=80,hostPort=80,protocol="tcp"}}],logConfiguration={{logDriver="awslogs",options={{awslogs-group=aws_cloudwatch_log_group.{ecs_label}.name,awslogs-region=var.aws_region,awslogs-stream-prefix="ecs"}}}}}}])')}),
                TerraformManagedResource(terraform_type="aws_iam_role", name="dashboard_task_execution_role", file="iam.tf", body={"name": _expr('format("%s-dashboard-task-role", local.name_prefix)'), "assume_role_policy": _expr('jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="ecs-tasks.amazonaws.com"},Action="sts:AssumeRole"}]})'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_iam_role_policy_attachment", name="dashboard_task_basic_execution", file="iam.tf", body={"role": _expr("aws_iam_role.dashboard_task_execution_role.name"), "policy_arn": _lit("arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy")}),
                TerraformManagedResource(terraform_type="aws_iam_role_policy", name="dashboard_secret_access", file="iam.tf", body={"name": _expr('format("%s-dashboard-secret-access", local.name_prefix)'), "role": _expr("aws_iam_role.dashboard_task_execution_role.id"), "policy": _expr('jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Action=["secretsmanager:GetSecretValue"],Resource=[aws_secretsmanager_secret.db_credentials.arn]}]})')}),
                TerraformManagedResource(terraform_type="aws_ecs_service", name=ecs_label, file="compute.tf", architecture_resource_id=ecs.id if ecs else None, depends_on=["aws_iam_role_policy_attachment.dashboard_task_basic_execution"], body={"name": _expr(f'format("%s-{ecs_label}", local.name_prefix)'), "cluster": _expr("aws_ecs_cluster.dashboard_cluster.id"), "task_definition": _expr("aws_ecs_task_definition.dashboard_task.arn"), "desired_count": _lit(1), "launch_type": _lit("FARGATE"), "network_configuration": _block("network_configuration", subnets=_expr("var.private_subnet_ids"), assign_public_ip=_lit(False)), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_db_subnet_group", name="dashboard_db_subnets", file="database.tf", body={"name": _expr('format("%s-dashboard-db", local.name_prefix)'), "subnet_ids": _expr("var.private_subnet_ids"), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_db_instance", name=db_label, file="database.tf", architecture_resource_id=rds.id if rds else None, body={"identifier": _expr('format("%s-dashboard-db", local.name_prefix)'), "engine": _lit("postgres"), "engine_version": _lit(str(resource_cfg(rds, "engine_version", default="15.5") if rds else "15.5")), "instance_class": _lit(str(resource_cfg(rds, "instance_class", default="db.t3.micro") if rds else "db.t3.micro")), "allocated_storage": _lit(int(resource_cfg(rds, "allocated_storage", default=20) if rds else 20)), "db_name": _lit("dashboard"), "username": _lit("nimbus_admin"), "password": _expr("random_password.db_password.result"), "db_subnet_group_name": _expr("aws_db_subnet_group.dashboard_db_subnets.name"), "publicly_accessible": _lit(False), "skip_final_snapshot": _lit(True), "tags": _expr("local.common_tags")}),
            ]
        )
        if alb:
            tf_plan.architecture_resource_mappings.append(_mapping(alb, f"aws_lb.{alb_label}"))
        if ecs:
            tf_plan.architecture_resource_mappings.append(_mapping(ecs, f"aws_ecs_service.{ecs_label}", "aws_ecs_task_definition.dashboard_task"))
        if rds:
            tf_plan.architecture_resource_mappings.append(_mapping(rds, f"aws_db_instance.{db_label}", "aws_db_subnet_group.dashboard_db_subnets"))
        if pool:
            tf_plan.architecture_resource_mappings.append(_mapping(pool, f"aws_cognito_user_pool.{pool_label}"))
        if pool_client:
            tf_plan.architecture_resource_mappings.append(_mapping(pool_client, f"aws_cognito_user_pool_client.{pool_client_label}"))
        plan_data = _base_plan(self.definition, architecture, options, settings)
        plan_data["terraform_resource_plan"] = tf_plan
        plan_data["warnings"] = ["Deterministic secure dashboard pattern selected; validate private subnet and security-group details before deployment."]
        plan_data["required_inputs"] = ["container_image", "vpc_id", "public_subnet_ids", "private_subnet_ids"]
        plan_data["derived_resources"] = _derived_response_items(tf_plan.derived_resources)
        plan_data["next_steps"] = [
            "Provide container_image and subnet inputs in terraform.tfvars.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
        ]
        return TerraformGenerationPlan(**plan_data)


class UsageAnalyticsIngestionPipelinePattern:
    definition = PatternDefinition(
        pattern_id="usage_analytics_ingestion_pipeline",
        required_provider_types={"aws_apigatewayv2_api", "aws_sqs_queue", "aws_lambda_function", "aws_s3_bucket", "aws_dynamodb_table"},
        optional_provider_types={"aws_cloudwatch_log_group", "aws_iam_role"},
        derived_implementation_resources=[
            {"type": "aws_apigatewayv2_integration", "name": "ingestion_queue_integration", "reason": "API ingestion endpoint must enqueue events."},
            {"type": "aws_lambda_event_source_mapping", "name": "analytics_processor", "reason": "Processor must consume ingested events."},
        ],
        required_user_inputs=["lambda_package_path"],
        safe_default_values={},
        generated_file_set=_generic_template_set("api_gateway.tf", "storage.tf", "lambda.tf", "database.tf", "iam.tf", "observability.tf"),
        validation_rules=["API Gateway must write to SQS.", "Lambda must consume SQS and persist raw plus aggregate analytics."],
        warnings=[],
        required_relationships=["aws_apigatewayv2_api -> aws_sqs_queue", "aws_sqs_queue -> aws_lambda_function", "aws_lambda_function -> aws_s3_bucket", "aws_lambda_function -> aws_dynamodb_table"],
        iam_synthesis="Scoped ingestion and processor IAM for SQS, S3, DynamoDB, and logs.",
        networking_synthesis="Managed ingestion path; no VPC networking required unless explicitly modeled.",
        file_renderer="generic_hcl_renderer",
    )

    def matches(self, architecture: NormalizedArchitecture) -> bool:
        types = {resource.provider_type for resource in architecture.resources}
        return self.definition.required_provider_types.issubset(types) and _has_relationship(architecture, "aws_apigatewayv2_api", "aws_sqs_queue")

    def plan(self, architecture: NormalizedArchitecture, options: GenerateOptions, settings: Settings) -> TerraformGenerationPlan:
        api = architecture.first("aws_apigatewayv2_api")
        queue = architecture.first("aws_sqs_queue")
        processor = architecture.first("aws_lambda_function")
        bucket = architecture.first("aws_s3_bucket")
        table = architecture.first("aws_dynamodb_table")
        api_label = _name_from_resource(api, "analytics_ingestion_api")
        queue_label = _name_from_resource(queue, "analytics_ingestion_queue")
        lambda_label = _name_from_resource(processor, "analytics_processor")
        bucket_label = _name_from_resource(bucket, "raw_events")
        table_label = _name_from_resource(table, "analytics_aggregates")
        tf_plan = _base_resource_plan(architecture, self.definition.pattern_id)
        tf_plan.variables.append(TerraformVariable(name="lambda_package_path", type="string", description="Analytics processor deployment package path.", required=True))
        tf_plan.resources.extend(
            [
                TerraformManagedResource(terraform_type="aws_s3_bucket", name=bucket_label, file="storage.tf", architecture_resource_id=bucket.id if bucket else None, body={"bucket": _expr(f'format("%s-{bucket_label.replace("_", "-")}", local.name_prefix)'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_s3_bucket_public_access_block", name=bucket_label, file="storage.tf", body={"bucket": _expr(f"aws_s3_bucket.{bucket_label}.id"), "block_public_acls": _lit(True), "block_public_policy": _lit(True), "ignore_public_acls": _lit(True), "restrict_public_buckets": _lit(True)}),
                TerraformManagedResource(terraform_type="aws_dynamodb_table", name=table_label, file="database.tf", architecture_resource_id=table.id if table else None, body={"name": _expr('format("%s-analytics", local.name_prefix)'), "billing_mode": _lit("PAY_PER_REQUEST"), "hash_key": _lit("pk"), "attribute": _list(_block("attribute", name=_lit("pk"), type=_lit("S"))), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_sqs_queue", name=queue_label, file="storage.tf", architecture_resource_id=queue.id if queue else None, body={"name": _expr(f'format("%s-{queue_label.replace("_", "-")}", local.name_prefix)'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_iam_role", name="analytics_processor_role", file="iam.tf", body={"name": _expr('format("%s-analytics-role", local.name_prefix)'), "assume_role_policy": _expr('jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="lambda.amazonaws.com"},Action="sts:AssumeRole"}]})'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_iam_role_policy_attachment", name="analytics_basic_execution", file="iam.tf", body={"role": _expr("aws_iam_role.analytics_processor_role.name"), "policy_arn": _lit("arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")}),
                TerraformManagedResource(terraform_type="aws_iam_role_policy", name="analytics_pipeline_access", file="iam.tf", body={"name": _expr('format("%s-analytics-access", local.name_prefix)'), "role": _expr("aws_iam_role.analytics_processor_role.id"), "policy": _expr(f'jsonencode({{Version="2012-10-17",Statement=[{{Effect="Allow",Action=["sqs:ReceiveMessage","sqs:DeleteMessage","sqs:GetQueueAttributes"],Resource=[aws_sqs_queue.{queue_label}.arn]}},{{Effect="Allow",Action=["s3:PutObject"],Resource=[format("%s/*", aws_s3_bucket.{bucket_label}.arn)]}},{{Effect="Allow",Action=["dynamodb:GetItem","dynamodb:PutItem","dynamodb:UpdateItem"],Resource=[aws_dynamodb_table.{table_label}.arn]}}]}})')}),
                TerraformManagedResource(terraform_type="aws_cloudwatch_log_group", name=lambda_label, file="observability.tf", body={"name": _expr(f'format("/aws/lambda/%s-{lambda_label}", local.name_prefix)'), "retention_in_days": _lit(7), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_lambda_function", name=lambda_label, file="lambda.tf", architecture_resource_id=processor.id if processor else None, depends_on=["aws_iam_role_policy_attachment.analytics_basic_execution"], body={"function_name": _expr(f'format("%s-{lambda_label}", local.name_prefix)'), "role": _expr("aws_iam_role.analytics_processor_role.arn"), "handler": _lit(_lambda_handler(processor)), "runtime": _lit(_lambda_runtime(processor)), "filename": _expr("var.lambda_package_path"), "source_code_hash": _expr("filebase64sha256(var.lambda_package_path)"), "environment": _block("environment", variables=_obj(RAW_EVENTS_BUCKET=_expr(f"aws_s3_bucket.{bucket_label}.bucket"), ANALYTICS_TABLE=_expr(f"aws_dynamodb_table.{table_label}.name"))), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_lambda_event_source_mapping", name="analytics_processor", file="lambda.tf", body={"event_source_arn": _expr(f"aws_sqs_queue.{queue_label}.arn"), "function_name": _expr(f"aws_lambda_function.{lambda_label}.arn"), "batch_size": _lit(10)}),
                TerraformManagedResource(terraform_type="aws_apigatewayv2_api", name=api_label, file="api_gateway.tf", architecture_resource_id=api.id if api else None, body={"name": _expr(f'format("%s-{api_label}", local.name_prefix)'), "protocol_type": _lit("HTTP"), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_iam_role", name="api_gateway_sqs_role", file="iam.tf", body={"name": _expr('format("%s-api-gateway-sqs-role", local.name_prefix)'), "assume_role_policy": _expr('jsonencode({Version="2012-10-17",Statement=[{Effect="Allow",Principal={Service="apigateway.amazonaws.com"},Action="sts:AssumeRole"}]})'), "tags": _expr("local.common_tags")}),
                TerraformManagedResource(terraform_type="aws_iam_role_policy", name="api_gateway_sqs_access", file="iam.tf", body={"name": _expr('format("%s-api-sqs-access", local.name_prefix)'), "role": _expr("aws_iam_role.api_gateway_sqs_role.id"), "policy": _expr(f'jsonencode({{Version="2012-10-17",Statement=[{{Effect="Allow",Action=["sqs:SendMessage"],Resource=[aws_sqs_queue.{queue_label}.arn]}}]}})')}),
                TerraformManagedResource(terraform_type="aws_apigatewayv2_integration", name="ingestion_queue_integration", file="api_gateway.tf", body={"api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"), "integration_type": _lit("AWS_PROXY"), "integration_subtype": _lit("SQS-SendMessage"), "credentials_arn": _expr("aws_iam_role.api_gateway_sqs_role.arn"), "request_parameters": _obj(QueueUrl=_expr(f"aws_sqs_queue.{queue_label}.id"), MessageBody=_expr("$request.body"))}),
                TerraformManagedResource(terraform_type="aws_apigatewayv2_route", name="ingest_route", file="api_gateway.tf", body={"api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"), "route_key": _lit("POST /events"), "target": _expr('format("integrations/%s", aws_apigatewayv2_integration.ingestion_queue_integration.id)')}),
                TerraformManagedResource(terraform_type="aws_apigatewayv2_stage", name="default", file="api_gateway.tf", body={"api_id": _expr(f"aws_apigatewayv2_api.{api_label}.id"), "name": _lit("$default"), "auto_deploy": _lit(True), "tags": _expr("local.common_tags")}),
            ]
        )
        if api:
            tf_plan.architecture_resource_mappings.append(_mapping(api, f"aws_apigatewayv2_api.{api_label}", "aws_apigatewayv2_integration.ingestion_queue_integration", "aws_apigatewayv2_route.ingest_route"))
        if queue:
            tf_plan.architecture_resource_mappings.append(_mapping(queue, f"aws_sqs_queue.{queue_label}", "aws_lambda_event_source_mapping.analytics_processor"))
        if processor:
            tf_plan.architecture_resource_mappings.append(_mapping(processor, f"aws_lambda_function.{lambda_label}", f"aws_cloudwatch_log_group.{lambda_label}"))
        if bucket:
            tf_plan.architecture_resource_mappings.append(_mapping(bucket, f"aws_s3_bucket.{bucket_label}"))
        if table:
            tf_plan.architecture_resource_mappings.append(_mapping(table, f"aws_dynamodb_table.{table_label}"))
        tf_plan.outputs.extend([TerraformOutput(name="ingestion_api_endpoint", value=_expr("aws_apigatewayv2_stage.default.invoke_url")), TerraformOutput(name="analytics_queue_url", value=_expr(f"aws_sqs_queue.{queue_label}.id"))])
        plan_data = _base_plan(self.definition, architecture, options, settings)
        plan_data["terraform_resource_plan"] = tf_plan
        plan_data["required_inputs"] = ["lambda_package_path"]
        plan_data["derived_resources"] = _derived_response_items(tf_plan.derived_resources)
        plan_data["next_steps"] = [
            "Package the analytics processor Lambda and set lambda_package_path.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
        ]
        return TerraformGenerationPlan(**plan_data)


class PatternRegistry:
    def __init__(self) -> None:
        self.patterns: list[ArchitecturePattern] = [
            StaticSitePattern(),
            WebsocketLobbyLambdaDynamodbPattern(),
            UsageAnalyticsIngestionPipelinePattern(),
            AsyncProcessingS3SqsWorkerPattern(),
            ServerlessHttpApiLambdaDynamodbPattern(),
            SecureInternalDashboardEcsRdsCognitoPattern(),
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
