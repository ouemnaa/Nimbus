"""
Per-strategy validation assertion constants.

These are injected into TerraformGenerationPlan.validation_assertions
so renderers and the reviewer can enforce them.
"""

from __future__ import annotations

ECS_PUBLIC_NO_NAT: list[str] = [
    "ECS service must use public subnets for low-cost no-NAT strategy.",
    "ECS assign_public_ip must be true when no NAT or VPC endpoints exist.",
    "RDS must remain publicly_accessible=false.",
    "RDS security group must allow PostgreSQL only from ECS security group.",
    "ECS security group must allow inbound only from ALB security group, not 0.0.0.0/0.",
    "No NAT Gateway or private route to NAT should be present.",
]

ECS_PRIVATE_NAT: list[str] = [
    "ECS service must use private subnets.",
    "ECS assign_public_ip must be false.",
    "A NAT Gateway must exist in a public subnet.",
    "Private route table must have a default route (0.0.0.0/0) through the NAT Gateway.",
    "RDS must remain publicly_accessible=false.",
    "RDS security group must allow PostgreSQL only from ECS security group.",
]

STATIC_SITE: list[str] = [
    "S3 bucket must have public access block enabled.",
    "CloudFront OAC must be configured — bucket policy allows only CloudFront distribution ARN.",
    "ACM certificate must use provider alias aws.us_east_1.",
    "Route53 hosted zone must be looked up via data.aws_route53_zone.",
    "domain_name, hosted_zone_name, and bucket_name are required user inputs.",
    "Terraform must not upload static assets — README must explain aws s3 sync.",
]

ASSERTIONS_BY_STRATEGY: dict[str, list[str]] = {
    "public_ecs_no_nat_low_cost_dev": ECS_PUBLIC_NO_NAT,
    "private_ecs_with_nat": ECS_PRIVATE_NAT,
    "static_site_s3_cloudfront_route53_https": STATIC_SITE,
}
