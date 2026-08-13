from __future__ import annotations

from dataclasses import dataclass

from .infrastructure_capability_plan import CapabilityType


@dataclass(frozen=True)
class AwsCapabilityDefinition:
    capability_type: CapabilityType
    service_options: list[str]
    terraform_primitives: list[str]
    notes: str


class AwsCapabilityCatalog:
    def __init__(self) -> None:
        self._definitions: dict[CapabilityType, AwsCapabilityDefinition] = {
            "PUBLIC_HTTP_ENTRYPOINT": AwsCapabilityDefinition(
                capability_type="PUBLIC_HTTP_ENTRYPOINT",
                service_options=["API Gateway HTTP API", "Application Load Balancer"],
                terraform_primitives=["aws_apigatewayv2_api", "aws_apigatewayv2_stage", "aws_lb", "aws_lb_listener"],
                notes="Prefer API Gateway for serverless compute and ALB for container workloads.",
            ),
            "REALTIME_CONNECTIONS": AwsCapabilityDefinition(
                capability_type="REALTIME_CONNECTIONS",
                service_options=["API Gateway WebSocket API"],
                terraform_primitives=["aws_apigatewayv2_api", "aws_apigatewayv2_route", "aws_apigatewayv2_integration"],
                notes="Use WebSocket APIs for persistent bidirectional sessions.",
            ),
            "ASYNC_QUEUE": AwsCapabilityDefinition(
                capability_type="ASYNC_QUEUE",
                service_options=["SQS"],
                terraform_primitives=["aws_sqs_queue"],
                notes="Optionally pair with DLQs and redrive policies.",
            ),
            "BACKGROUND_WORKER": AwsCapabilityDefinition(
                capability_type="BACKGROUND_WORKER",
                service_options=["Lambda", "ECS Fargate"],
                terraform_primitives=["aws_lambda_function", "aws_ecs_service", "aws_ecs_task_definition"],
                notes="Prefer Lambda for event-driven jobs and ECS for long-running worker containers.",
            ),
            "OBJECT_STORAGE": AwsCapabilityDefinition(
                capability_type="OBJECT_STORAGE",
                service_options=["S3"],
                terraform_primitives=["aws_s3_bucket", "aws_s3_bucket_public_access_block"],
                notes="Default to private buckets with public access blocked.",
            ),
            "RELATIONAL_DATABASE": AwsCapabilityDefinition(
                capability_type="RELATIONAL_DATABASE",
                service_options=["RDS"],
                terraform_primitives=["aws_db_instance", "aws_db_subnet_group"],
                notes="Prefer non-public database placement.",
            ),
            "KEY_VALUE_STORE": AwsCapabilityDefinition(
                capability_type="KEY_VALUE_STORE",
                service_options=["DynamoDB"],
                terraform_primitives=["aws_dynamodb_table"],
                notes="Good fit for session state and low-latency key/value access.",
            ),
            "JOB_STATUS_STORE": AwsCapabilityDefinition(
                capability_type="JOB_STATUS_STORE",
                service_options=["DynamoDB"],
                terraform_primitives=["aws_dynamodb_table"],
                notes="Use DynamoDB for durable job status tracking.",
            ),
            "SECRET_STORAGE": AwsCapabilityDefinition(
                capability_type="SECRET_STORAGE",
                service_options=["Secrets Manager"],
                terraform_primitives=["aws_secretsmanager_secret", "aws_secretsmanager_secret_version"],
                notes="Keep actual secret values out of source control.",
            ),
            "AUTHENTICATION": AwsCapabilityDefinition(
                capability_type="AUTHENTICATION",
                service_options=["Cognito", "External identity provider"],
                terraform_primitives=["aws_cognito_user_pool"],
                notes="External auth providers should be mapped as EXTERNAL.",
            ),
            "SERVERLESS_COMPUTE": AwsCapabilityDefinition(
                capability_type="SERVERLESS_COMPUTE",
                service_options=["Lambda"],
                terraform_primitives=["aws_lambda_function", "aws_iam_role", "aws_cloudwatch_log_group"],
                notes="Lambda requires execution IAM and observability support.",
            ),
            "CONTAINER_COMPUTE": AwsCapabilityDefinition(
                capability_type="CONTAINER_COMPUTE",
                service_options=["ECS Fargate"],
                terraform_primitives=["aws_ecs_cluster", "aws_ecs_task_definition", "aws_ecs_service"],
                notes="Expose via ALB when internet-facing HTTP ingress is required.",
            ),
            "PRIVATE_NETWORKING": AwsCapabilityDefinition(
                capability_type="PRIVATE_NETWORKING",
                service_options=["VPC", "Subnets", "Route tables", "NAT or VPC endpoints"],
                terraform_primitives=["aws_vpc", "aws_subnet", "aws_route_table", "aws_nat_gateway"],
                notes="Required for private data tiers and isolated services.",
            ),
            "OBSERVABILITY_LOGS": AwsCapabilityDefinition(
                capability_type="OBSERVABILITY_LOGS",
                service_options=["CloudWatch Logs"],
                terraform_primitives=["aws_cloudwatch_log_group"],
                notes="Provision log groups for managed compute services when appropriate.",
            ),
            "IAM_EXECUTION_ROLE": AwsCapabilityDefinition(
                capability_type="IAM_EXECUTION_ROLE",
                service_options=["IAM Role", "IAM Policy", "IAM Role Policy Attachment"],
                terraform_primitives=["aws_iam_role", "aws_iam_role_policy", "aws_iam_role_policy_attachment"],
                notes="Compute services need least-privilege execution roles.",
            ),
            "EVENT_ROUTING": AwsCapabilityDefinition(
                capability_type="EVENT_ROUTING",
                service_options=["API Gateway routes", "EventBridge rules"],
                terraform_primitives=["aws_apigatewayv2_route", "aws_cloudwatch_event_rule", "aws_cloudwatch_event_target"],
                notes="Relationships should become explicit routing resources.",
            ),
            "SCHEDULED_TASKS": AwsCapabilityDefinition(
                capability_type="SCHEDULED_TASKS",
                service_options=["EventBridge schedules"],
                terraform_primitives=["aws_cloudwatch_event_rule", "aws_cloudwatch_event_target"],
                notes="Use schedules for cron-like periodic execution.",
            ),
            "CDN_STATIC_HOSTING": AwsCapabilityDefinition(
                capability_type="CDN_STATIC_HOSTING",
                service_options=["S3 + CloudFront + ACM + Route 53"],
                terraform_primitives=["aws_s3_bucket", "aws_cloudfront_distribution", "aws_acm_certificate", "aws_route53_record"],
                notes="Use the deterministic static-site renderer when the known pattern matches.",
            ),
        }

    def definition(self, capability_type: CapabilityType) -> AwsCapabilityDefinition:
        return self._definitions[capability_type]

    def terraform_primitives_for(self, capability_type: CapabilityType) -> list[str]:
        return list(self._definitions[capability_type].terraform_primitives)

    def prompt_payload(self) -> dict[str, dict[str, object]]:
        return {
            key: {
                "service_options": definition.service_options,
                "terraform_primitives": definition.terraform_primitives,
                "notes": definition.notes,
            }
            for key, definition in self._definitions.items()
        }
