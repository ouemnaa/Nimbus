from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas.architecture import CanonicalArchitecture
from app.utils.naming import resource_label, safe_name


PROVIDER_TYPE_MAP = {
    "AWS::EC2::VPC": "aws_vpc",
    "AWS::EC2::Subnet": "aws_subnet",
    "AWS::EC2::InternetGateway": "aws_internet_gateway",
    "AWS::EC2::NatGateway": "aws_nat_gateway",
    "AWS::EC2::SecurityGroup": "aws_security_group",
    "AWS::ElasticLoadBalancingV2::LoadBalancer": "aws_lb",
    "AWS::ElasticLoadBalancingV2::TargetGroup": "aws_lb_target_group",
    "AWS::ElasticLoadBalancingV2::Listener": "aws_lb_listener",
    "AWS::ECS::Cluster": "aws_ecs_cluster",
    "AWS::ECS::Service": "aws_ecs_service",
    "AWS::ECS::TaskDefinition": "aws_ecs_task_definition",
    "AWS::RDS::DBInstance": "aws_db_instance",
    "AWS::RDS::DBSubnetGroup": "aws_db_subnet_group",
    "AWS::SecretsManager::Secret": "aws_secretsmanager_secret",
    "AWS::SecretsManager::SecretVersion": "aws_secretsmanager_secret_version",
    "AWS::IAM::Role": "aws_iam_role",
    "AWS::IAM::Policy": "aws_iam_policy",
    "AWS::IAM::RolePolicyAttachment": "aws_iam_role_policy_attachment",
    "AWS::Logs::LogGroup": "aws_cloudwatch_log_group",
    "AWS::Lambda::Function": "aws_lambda_function",
    "AWS::ApiGatewayV2::Api": "aws_apigatewayv2_api",
    "AWS::ApiGatewayV2::Stage": "aws_apigatewayv2_stage",
    "AWS::ApiGateway::RestApi": "aws_api_gateway_rest_api",
    "AWS::DynamoDB::Table": "aws_dynamodb_table",
    "AWS::SQS::Queue": "aws_sqs_queue",
    "AWS::Cognito::UserPool": "aws_cognito_user_pool",
    "AWS::Cognito::UserPoolClient": "aws_cognito_user_pool_client",
    "AWS::MediaConvert::Queue": "aws_media_convert_queue",
    "AWS::S3::Bucket": "aws_s3_bucket",
    "AWS::S3::BucketPolicy": "aws_s3_bucket_policy",
    "AWS::CloudFront::Distribution": "aws_cloudfront_distribution",
    "AWS::CloudFront::OriginAccessControl": "aws_cloudfront_origin_access_control",
    "AWS::CertificateManager::Certificate": "aws_acm_certificate",
    "AWS::Route53::HostedZone": "aws_route53_zone",
    "AWS::Route53::RecordSet": "aws_route53_record",
    "aws_eip": "aws_eip",
    "aws_route_table": "aws_route_table",
    "aws_route": "aws_route",
    "aws_route_table_association": "aws_route_table_association",
    "random_password": "random_password",
    # Historical and conceptual aliases accepted at the compiler boundary.
    "aws_mediaconvert_queue": "aws_media_convert_queue",
    "serverless_compute": "aws_lambda_function",
    "object_storage": "aws_s3_bucket",
    "async_queue": "aws_sqs_queue",
    "key_value_store": "aws_dynamodb_table",
    "relational_database": "aws_db_instance",
    "container_compute": "aws_ecs_service",
}

SUPPORTED_PROVIDER_TYPES = set(PROVIDER_TYPE_MAP.values())


@dataclass
class NormalizedResource:
    id: str
    name: str
    provider_type: str
    category: str
    scope: str
    configuration: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return resource_label(self.id, self.name)


@dataclass
class NormalizedArchitecture:
    architecture_id: str
    architecture_version: str
    provider: str
    region: str
    resources: list[NormalizedResource]
    relationships: list[dict[str, Any]]

    def by_type(self, *types: str) -> list[NormalizedResource]:
        wanted = set(types)
        return [resource for resource in self.resources if resource.provider_type in wanted]

    def first(self, *types: str) -> NormalizedResource | None:
        return next(iter(self.by_type(*types)), None)

    def resource(self, resource_id: str) -> NormalizedResource | None:
        return next((resource for resource in self.resources if resource.id == resource_id), None)


def normalize_provider_type(value: str) -> str:
    if not value:
        return ""
    return PROVIDER_TYPE_MAP.get(value, PROVIDER_TYPE_MAP.get(value.lower(), value.lower()))


def cfg(config: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    config = config or {}
    lowered = {str(key).lower(): value for key, value in config.items()}
    for key in keys:
        if key in config:
            return config[key]
        if key.lower() in lowered:
            return lowered[key.lower()]
    return default


def resource_cfg(resource: NormalizedResource, *keys: str, default: Any = None) -> Any:
    return cfg(resource.configuration, *keys, default=default)


def normalize_architecture(architecture: CanonicalArchitecture, default_region: str) -> NormalizedArchitecture:
    normalized_resources: list[NormalizedResource] = []
    for resource in architecture.resources:
        provider_type = normalize_provider_type(resource.provider_type)
        normalized_resources.append(
            NormalizedResource(
                id=resource.id,
                name=safe_name(resource.name or resource.id),
                provider_type=provider_type,
                category=resource.category or provider_type.removeprefix("aws_").replace("_", " "),
                scope=resource.scope or "regional",
                configuration=dict(resource.configuration or {}),
                depends_on=list(resource.depends_on or []),
            )
        )
    return NormalizedArchitecture(
        architecture_id=architecture.architecture_id,
        architecture_version=architecture.architecture_version,
        provider=architecture.provider(),
        region=architecture.region(default_region),
        resources=normalized_resources,
        relationships=list(architecture.relationships or []),
    )
