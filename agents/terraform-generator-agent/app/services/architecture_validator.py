from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .architecture_normalizer import NormalizedArchitecture, NormalizedResource, resource_cfg


@dataclass
class ArchitectureValidation:
    supported_resources: list[str] = field(default_factory=list)
    unsupported_resources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.unsupported_resources:
            return "UNSUPPORTED"
        if self.errors:
            return "NEEDS_INPUT"
        return "VALID"


def validate_architecture(architecture: NormalizedArchitecture) -> ArchitectureValidation:
    result = ArchitectureValidation()
    if architecture.provider != "aws":
        result.unsupported_resources.append(f"cloud.provider={architecture.provider}")
        return result

    for resource in architecture.resources:
        if resource.provider_type not in {
            "aws_vpc", "aws_subnet", "aws_internet_gateway", "aws_nat_gateway", "aws_security_group",
            "aws_lb", "aws_lb_target_group", "aws_lb_listener", "aws_ecs_cluster", "aws_ecs_service",
            "aws_ecs_task_definition", "aws_db_instance", "aws_db_subnet_group", "aws_secretsmanager_secret",
            "aws_secretsmanager_secret_version", "aws_iam_role", "aws_iam_policy", "aws_iam_role_policy_attachment",
            "aws_cloudwatch_log_group", "aws_eip", "aws_route_table", "aws_route", "aws_route_table_association",
            "random_password", "aws_s3_bucket", "aws_s3_bucket_policy", "aws_cloudfront_distribution",
            "aws_cloudfront_origin_access_control", "aws_acm_certificate", "aws_route53_zone", "aws_route53_record",
        }:
            result.unsupported_resources.append(resource.provider_type)
        else:
            result.supported_resources.append(resource.provider_type)

    if result.unsupported_resources:
        result.unsupported_resources = sorted(set(result.unsupported_resources))
        return result

    static_site = architecture.first("aws_s3_bucket") and architecture.first("aws_cloudfront_distribution")
    if static_site and not architecture.first("aws_ecs_service") and not architecture.first("aws_db_instance"):
        if not architecture.first("aws_acm_certificate"):
            result.warnings.append("No ACM certificate resource was found; generated Terraform will expose a certificate variable.")
        if not architecture.first("aws_route53_zone"):
            result.warnings.append("No Route 53 hosted zone was found; generated Terraform will expose domain variables.")
        return result

    vpc = architecture.first("aws_vpc")
    if not vpc:
        result.errors.append("A VPC resource is required for the supported ECS/RDS architecture.")
    elif not resource_cfg(vpc, "cidr_block", "cidr", "CidrBlock"):
        result.errors.append("VPC configuration must include cidr_block so subnet CIDRs can be inferred safely.")

    if architecture.first("aws_nat_gateway") and len(architecture.by_type("aws_nat_gateway")) == 1:
        result.warnings.append("A single NAT Gateway is a low-cost development choice and is not highly available.")

    rds = architecture.first("aws_db_instance")
    if rds and not bool(resource_cfg(rds, "multi_az", "MultiAZ", default=False)):
        result.warnings.append("RDS is configured as single-AZ for development cost control.")

    if architecture.first("aws_lb") and not architecture.by_type("aws_subnet"):
        result.errors.append("An ALB requires public subnet information or a VPC CIDR from which public subnets can be derived.")

    return result
