from __future__ import annotations

from typing import Any

from app.utils.cidr import allocate_subnet
from app.utils.hcl_safety import is_fake_aws_id
from app.utils.naming import safe_name
from app.schemas.repair import RepairState

from .architecture_normalizer import NormalizedArchitecture, NormalizedResource, resource_cfg


def _is_public(resource: NormalizedResource) -> bool:
    value = resource_cfg(resource, "public", "is_public", default=None)
    if value is not None:
        return bool(value)
    tier = str(resource_cfg(resource, "subnet_type", "network_tier", "tier", default=""))
    return "public" in tier.lower() or "public" in resource.id.lower() or "public" in resource.name.lower()


def _is_private(resource: NormalizedResource) -> bool:
    value = resource_cfg(resource, "private", "is_private", default=None)
    if value is not None:
        return bool(value)
    tier = str(resource_cfg(resource, "subnet_type", "network_tier", "tier", default=""))
    return "private" in tier.lower() or "private" in resource.id.lower() or "private" in resource.name.lower()


def _next_az(region: str, existing: list[str], default_suffix: str) -> str:
    normalized = {item for item in existing if item}
    for suffix in "abcdefghijklmnopqrstuvwxyz":
        candidate = f"{region}{suffix}"
        if candidate not in normalized:
            return candidate
    return f"{region}{default_suffix}"


def _add_resource(architecture: NormalizedArchitecture, state: RepairState, *, id_: str, name: str, type_: str, config: dict[str, Any], derived_from: str, reason: str) -> NormalizedResource:
    resource = NormalizedResource(id=id_, name=safe_name(name), provider_type=type_, category=type_.removeprefix("aws_"), scope="regional", configuration=config)
    architecture.resources.append(resource)
    state.add_derived(type_, resource.label, derived_from, reason)
    return resource


def apply_repairs(architecture: NormalizedArchitecture) -> RepairState:
    state = RepairState(resources=[])
    vpc = architecture.first("aws_vpc")
    if not vpc:
        return state
    vpc_cidr = resource_cfg(vpc, "cidr_block", "cidr", "CidrBlock")
    existing_subnets = architecture.by_type("aws_subnet")
    used_cidrs = [str(resource_cfg(item, "cidr_block", "cidr", "CidrBlock", default="")) for item in existing_subnets]
    existing_azs = [str(resource_cfg(item, "availability_zone", "az", "AvailabilityZone", default="")) for item in existing_subnets]

    public_subnets = [item for item in existing_subnets if _is_public(item)]
    private_subnets = [item for item in existing_subnets if _is_private(item)]

    if architecture.first("aws_lb") and len(public_subnets) < 2 and vpc_cidr:
        cidr = allocate_subnet(str(vpc_cidr), used_cidrs, preferred="10.0.3.0/24")
        if cidr:
            subnet = _add_resource(
                architecture, state, id_="derived-public-subnet-2", name="public-subnet-2", type_="aws_subnet",
                config={"cidr_block": cidr, "availability_zone": _next_az(architecture.region, existing_azs, "b"), "subnet_type": "public", "public": True},
                derived_from=architecture.first("aws_lb").id, reason="ALB requires subnets in at least two Availability Zones.",
            )
            public_subnets.append(subnet)
            used_cidrs.append(cidr)
            state.add_repair("resources", "add_public_subnet", "ALB requires at least two Availability Zone subnets.", f"Added {subnet.id} with CIDR {cidr}.")
        else:
            state.warnings.append("ALB has fewer than two public subnets, and no non-overlapping subnet CIDR could be allocated.")

    if architecture.first("aws_db_instance") and len(private_subnets) < 2 and vpc_cidr:
        cidr = allocate_subnet(str(vpc_cidr), used_cidrs, preferred="10.0.4.0/24")
        if cidr:
            subnet = _add_resource(
                architecture, state, id_="derived-private-subnet-2", name="private-subnet-2", type_="aws_subnet",
                config={"cidr_block": cidr, "availability_zone": _next_az(architecture.region, existing_azs, "b"), "subnet_type": "private", "private": True},
                derived_from=architecture.first("aws_db_instance").id, reason="RDS DB subnet groups should cover at least two Availability Zones.",
            )
            private_subnets.append(subnet)
            used_cidrs.append(cidr)
            state.add_repair("resources", "add_private_subnet", "RDS DB subnet groups should cover at least two Availability Zones.", f"Added {subnet.id} with CIDR {cidr}.")
        else:
            state.warnings.append("RDS has fewer than two private subnets, and no non-overlapping subnet CIDR could be allocated.")

    for nat in architecture.by_type("aws_nat_gateway"):
        allocation_id = resource_cfg(nat, "allocation_id", "AllocationId")
        if not allocation_id or is_fake_aws_id(allocation_id, "eip"):
            eip_id = f"{nat.id}-eip"
            if not architecture.resource(eip_id):
                _add_resource(architecture, state, id_=eip_id, name=f"{nat.name}-eip", type_="aws_eip", config={"domain": "vpc"}, derived_from=nat.id, reason="NAT Gateway requires an Elastic IP allocation.")
            nat.configuration["allocation_id"] = f"aws_eip.{safe_name(nat.name)}_eip.id"
            state.add_repair(f"resources[{nat.id}].configuration.allocation_id", "replace_fake_reference", "Fake EIP allocation IDs cannot be used in Terraform.", "Generated aws_eip resource for NAT Gateway.")

    alb = architecture.first("aws_lb")
    if alb and not architecture.first("aws_lb_target_group"):
        _add_resource(architecture, state, id_=f"{alb.id}-target-group", name=f"{alb.name}-target-group", type_="aws_lb_target_group", config={"port": 80, "protocol": "HTTP", "target_type": "ip", "health_check_path": "/"}, derived_from=alb.id, reason="ECS services need an ALB target group for traffic registration.")
    if alb and not architecture.first("aws_lb_listener"):
        _add_resource(architecture, state, id_=f"{alb.id}-listener", name=f"{alb.name}-listener", type_="aws_lb_listener", config={"port": 80, "protocol": "HTTP"}, derived_from=alb.id, reason="An ALB needs a listener to route HTTP traffic to ECS.")

    ecs = architecture.first("aws_ecs_service")
    if ecs:
        image = resource_cfg(ecs, "container_image", "image", "containerImage")
        if not image:
            state.warnings.append("ECS container image is missing; generated Terraform uses required variable container_image.")
            state.add_repair(f"resources[{ecs.id}].configuration.image", "use_variable", "No safe real image can be invented.", "Terraform variable container_image will be used.")
        port = resource_cfg(ecs, "container_port", "port", "containerPort")
        if not port:
            ecs.configuration["container_port"] = 80
            state.warnings.append("ECS container port was missing and defaulted to 80.")
            state.add_repair(f"resources[{ecs.id}].configuration.port", "default_value", "A deterministic HTTP default is safe for the first development architecture.", "Set container port to 80.")
        if not architecture.first("aws_ecs_task_definition"):
            _add_resource(architecture, state, id_=f"{ecs.id}-task-definition", name=f"{ecs.name}-task-definition", type_="aws_ecs_task_definition", config={}, derived_from=ecs.id, reason="ECS service requires a task definition.")
        if not architecture.first("aws_iam_role"):
            _add_resource(architecture, state, id_=f"{ecs.id}-execution-role", name=f"{ecs.name}-execution-role", type_="aws_iam_role", config={"purpose": "ecs_execution"}, derived_from=ecs.id, reason="Fargate tasks require an ECS execution role.")
        if not architecture.first("aws_cloudwatch_log_group"):
            _add_resource(architecture, state, id_=f"{ecs.id}-logs", name=f"{ecs.name}-logs", type_="aws_cloudwatch_log_group", config={"retention_in_days": 7}, derived_from=ecs.id, reason="ECS task logging requires a CloudWatch log group.")

    rds = architecture.first("aws_db_instance")
    if rds:
        if not architecture.first("aws_db_subnet_group"):
            _add_resource(architecture, state, id_=f"{rds.id}-subnet-group", name=f"{rds.name}-subnet-group", type_="aws_db_subnet_group", config={}, derived_from=rds.id, reason="RDS requires a DB subnet group.")
        if not architecture.first("random_password"):
            _add_resource(architecture, state, id_=f"{rds.id}-password", name=f"{rds.name}-password", type_="random_password", config={"length": 32}, derived_from=rds.id, reason="Database credentials require a generated password rather than plaintext input.")
        if not architecture.first("aws_secretsmanager_secret"):
            _add_resource(architecture, state, id_=f"{rds.id}-secret", name=f"{rds.name}-secret", type_="aws_secretsmanager_secret", config={}, derived_from=rds.id, reason="Database credentials are stored in Secrets Manager.")
        if not architecture.first("aws_secretsmanager_secret_version"):
            _add_resource(architecture, state, id_=f"{rds.id}-secret-version", name=f"{rds.name}-secret-version", type_="aws_secretsmanager_secret_version", config={}, derived_from=rds.id, reason="The generated database credential payload needs a Secrets Manager version.")

    return state
