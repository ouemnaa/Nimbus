from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from app.core.config import Settings
from app.renderers.common_files_renderer import CommonFilesRenderer
from app.renderers.database_renderer import DatabaseRenderer
from app.renderers.ecs_renderer import EcsRenderer
from app.renderers.iam_renderer import IamRenderer
from app.renderers.load_balancing_renderer import LoadBalancingRenderer
from app.renderers.networking_renderer import NetworkingRenderer
from app.renderers.observability_renderer import ObservabilityRenderer
from app.renderers.outputs_renderer import OutputsRenderer
from app.renderers.security_groups_renderer import SecurityGroupsRenderer
from app.renderers.secrets_renderer import SecretsRenderer
from app.schemas.architecture import CanonicalArchitecture, GenerateOptions
from app.schemas.terraform import GenerationMetadata, GenerationResponse
from app.utils.naming import safe_identifier, safe_name

from .architecture_normalizer import NormalizedArchitecture, NormalizedResource, normalize_architecture, resource_cfg
from .architecture_validator import validate_architecture
from .artifact_writer import ArtifactWriter
from .repair_service import apply_repairs

logger = logging.getLogger(__name__)


class TerraformGeneratorService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.common_renderer = CommonFilesRenderer()
        self.renderers = [
            NetworkingRenderer(),
            SecurityGroupsRenderer(),
            LoadBalancingRenderer(),
            IamRenderer(),
            ObservabilityRenderer(),
            SecretsRenderer(),
            DatabaseRenderer(),
            EcsRenderer(),
            OutputsRenderer(),
        ]
        self.writer = ArtifactWriter(settings.generated_artifacts_dir)

    def generate(self, architecture: CanonicalArchitecture, options: GenerateOptions | None = None) -> GenerationResponse:
        options = options or GenerateOptions()
        normalized = normalize_architecture(architecture, self.settings.default_aws_region)
        validation = validate_architecture(normalized)
        metadata_base = {
            "generator_version": self.settings.generator_version,
            "generated_file_count": 0,
            "llm_provider": self.settings.llm_provider,
            "architecture_id": normalized.architecture_id,
            "architecture_version": normalized.architecture_version,
        }

        if validation.unsupported_resources:
            return GenerationResponse(
                generation_status="UNSUPPORTED",
                supported_resources=sorted(set(validation.supported_resources)),
                unsupported_resources=validation.unsupported_resources,
                warnings=validation.warnings,
                next_steps=["Implement a renderer for the unsupported provider/resource types before generating Terraform."],
                metadata=GenerationMetadata(**metadata_base),
                error="The architecture contains unsupported resources.",
            )
        if validation.errors:
            return GenerationResponse(
                generation_status="NEEDS_INPUT",
                supported_resources=sorted(set(validation.supported_resources)),
                warnings=validation.warnings,
                next_steps=["Provide the missing deterministic architecture inputs and retry generation."],
                metadata=GenerationMetadata(**metadata_base),
                error=" ".join(validation.errors),
            )

        if self._is_static_site(normalized):
            return self._generate_static_site(normalized, options, validation, metadata_base)

        repair_state = apply_repairs(normalized) if options.allow_repairs else self._empty_repair_state()
        warnings = list(validation.warnings) + list(repair_state.warnings)
        repairs = list(repair_state.repairs)
        derived = list(repair_state.derived_resources)
        alb = normalized.first("aws_lb")
        if alb:
            certificate_arn = resource_cfg(alb, "certificate_arn", "acm_certificate_arn", "CertificateArn")
            if certificate_arn:
                warnings.append("An ACM certificate ARN was provided, but this version renders HTTP only; HTTPS support is on the roadmap.")
            else:
                warnings.append("HTTPS is not configured because no ACM certificate ARN was provided; the generated ALB listener uses HTTP port 80 only.")
        rds = normalized.first("aws_db_instance")
        if rds and not resource_cfg(rds, "username", "master_username", "MasterUsername"):
            warnings.append("RDS username was missing; generated Terraform uses the safe variable default nimbus_admin.")
            repairs.append({
                "path": f"resources[{rds.id}].configuration.username",
                "action": "use_variable_default",
                "reason": "RDS username is required but can be safely represented as a configurable Terraform variable.",
                "result": "Created db_username with example default nimbus_admin.",
            })
        
        self._record_implementation_derivations(normalized, derived)

        try:
            context = self._build_context(normalized, options, warnings, repairs)
            files_by_path = self.common_renderer.render_files(context)
            for renderer in self.renderers:
                files_by_path.update(renderer.render_files(context))
            ordered_paths = [
                "versions.tf", "providers.tf", "variables.tf", "locals.tf", "networking.tf", "security_groups.tf",
                "load_balancing.tf", "iam.tf", "observability.tf", "secrets.tf", "database.tf", "ecs.tf",
                "outputs.tf", "terraform.tfvars.example", "README.generated.md",
            ]
            files = [{"path": path, "content": files_by_path[path]} for path in ordered_paths if path in files_by_path]
            self.writer.write(files)
        except Exception as exc:
            logger.exception("Terraform template rendering failed")
            return GenerationResponse(
                generation_status="FAILED",
                supported_resources=sorted(set(validation.supported_resources)),
                warnings=warnings,
                repairs=repairs,
                derived_resources=derived,
                metadata=GenerationMetadata(**metadata_base),
                error=f"Template rendering failed: {type(exc).__name__}: {exc}",
            )

        metadata_base["generated_file_count"] = len(files)
        next_steps = [
            "Review terraform.tfvars.example and provide a real container_image in an uncommitted terraform.tfvars file.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
            "Review the generated plan and AWS costs before any deployment.",
        ]
        if not options.validate:
            next_steps.append("Call /api/v1/terraform/validate or /api/v1/terraform/generate-and-validate for CLI validation.")
        return GenerationResponse(
            generation_status="SUCCESS",
            supported_resources=sorted(set(validation.supported_resources)),
            files=files,
            derived_resources=derived,
            repairs=repairs,
            warnings=warnings,
            next_steps=next_steps,
            metadata=GenerationMetadata(**metadata_base),
        )

    def _is_static_site(self, architecture: NormalizedArchitecture) -> bool:
        return bool(
            architecture.first("aws_s3_bucket")
            and architecture.first("aws_cloudfront_distribution")
            and not architecture.first("aws_ecs_service")
            and not architecture.first("aws_db_instance")
        )

    def _generate_static_site(
        self,
        architecture: NormalizedArchitecture,
        options: GenerateOptions,
        validation,
        metadata_base: dict[str, Any],
    ) -> GenerationResponse:
        bucket = architecture.first("aws_s3_bucket")
        distribution = architecture.first("aws_cloudfront_distribution")
        certificate = architecture.first("aws_acm_certificate")
        zone = architecture.first("aws_route53_zone")
        oac = architecture.first("aws_cloudfront_origin_access_control")
        bucket_label = bucket.label if bucket else "site_bucket"
        distribution_label = distribution.label if distribution else "cdn"
        certificate_label = certificate.label if certificate else "site_certificate"
        zone_label = zone.label if zone else "site_zone"
        oac_label = oac.label if oac else "cloudfront_oac"
        project_name = safe_name(options.project_name or self.settings.default_project_name)
        environment = safe_name(options.environment or self.settings.default_environment)
        domain_name = str(resource_cfg(certificate, "domain_name", default="dev.example.com") if certificate else "dev.example.com")
        zone_name = str(resource_cfg(zone, "domain_name", "name", default="example.com") if zone else "example.com")
        bucket_name = str(resource_cfg(bucket, "bucket_name", "bucket", default="") if bucket else "")
        if not bucket_name:
            bucket_name = f"${{local.name_prefix}}-site"
        price_class = str(resource_cfg(distribution, "price_class", default="PriceClass_100") if distribution else "PriceClass_100")
        root_object = str(resource_cfg(distribution, "default_root_object", default="index.html") if distribution else "index.html")
        viewer_policy = str(resource_cfg(distribution, "viewer_protocol_policy", default="redirect-to-https") if distribution else "redirect-to-https")
        context = {
            "architecture_id": architecture.architecture_id,
            "architecture_version": architecture.architecture_version,
            "project_name": project_name,
            "environment": environment,
            "region": options.aws_region or architecture.region,
            "bucket_label": bucket_label,
            "distribution_label": distribution_label,
            "certificate_label": certificate_label,
            "zone_label": zone_label,
            "oac_label": oac_label,
            "bucket_name": bucket_name,
            "domain_name": domain_name,
            "zone_name": zone_name,
            "price_class": price_class,
            "root_object": root_object,
            "viewer_policy": viewer_policy,
        }
        files = [
            {"path": "versions.tf", "content": self._static_versions_tf()},
            {"path": "providers.tf", "content": self._static_providers_tf()},
            {"path": "variables.tf", "content": self._static_variables_tf(context)},
            {"path": "locals.tf", "content": self._static_locals_tf()},
            {"path": "static_site.tf", "content": self._static_site_tf(context)},
            {"path": "outputs.tf", "content": self._static_outputs_tf(context)},
            {"path": "terraform.tfvars.example", "content": self._static_tfvars(context)},
            {"path": "README.generated.md", "content": self._static_readme(context)},
        ]
        self.writer.write(files)
        metadata_base["generated_file_count"] = len(files)
        warnings = list(validation.warnings)
        next_steps = [
            "Review terraform.tfvars.example and set a real domain_name and hosted_zone_name before planning.",
            "Run terraform fmt -check, terraform init -backend=false, and terraform validate.",
            "Upload built static assets to the generated S3 bucket after infrastructure is created.",
        ]
        return GenerationResponse(
            generation_status="SUCCESS",
            supported_resources=sorted(set(validation.supported_resources)),
            files=files,
            warnings=warnings,
            next_steps=next_steps,
            metadata=GenerationMetadata(**metadata_base),
        )

    @staticmethod
    def _static_versions_tf() -> str:
        return """terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
"""

    @staticmethod
    def _static_providers_tf() -> str:
        return """provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}
"""

    @staticmethod
    def _static_variables_tf(context: dict[str, Any]) -> str:
        return f'''variable "aws_region" {{
  description = "AWS region for S3, ACM, Route 53, and CloudFront management."
  type        = string
  default     = "{context["region"]}"
}}

variable "project_name" {{
  description = "Short project name used in resource names and tags."
  type        = string
  default     = "{context["project_name"]}"
}}

variable "environment" {{
  description = "Deployment environment."
  type        = string
  default     = "{context["environment"]}"
}}

variable "domain_name" {{
  description = "Fully qualified website domain name."
  type        = string
  default     = "{context["domain_name"]}"
}}

variable "hosted_zone_name" {{
  description = "Route 53 hosted zone name."
  type        = string
  default     = "{context["zone_name"]}"
}}

variable "bucket_name" {{
  description = "Globally unique S3 bucket name for static website assets."
  type        = string
  default     = "{context["bucket_name"]}"
}}
'''

    @staticmethod
    def _static_locals_tf() -> str:
        return """locals {
  name_prefix = lower(replace("${var.project_name}-${var.environment}", "_", "-"))

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "nimbus-terraform-generator"
  }
}
"""

    @staticmethod
    def _static_site_tf(context: dict[str, Any]) -> str:
        return f'''data "aws_route53_zone" "{context["zone_label"]}" {{
  name         = var.hosted_zone_name
  private_zone = false
}}

resource "aws_s3_bucket" "{context["bucket_label"]}" {{
  bucket = var.bucket_name
}}

resource "aws_s3_bucket_public_access_block" "{context["bucket_label"]}" {{
  bucket = aws_s3_bucket.{context["bucket_label"]}.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}}

resource "aws_s3_bucket_server_side_encryption_configuration" "{context["bucket_label"]}" {{
  bucket = aws_s3_bucket.{context["bucket_label"]}.id

  rule {{
    apply_server_side_encryption_by_default {{
      sse_algorithm = "AES256"
    }}
  }}
}}

resource "aws_cloudfront_origin_access_control" "{context["oac_label"]}" {{
  name                              = "${{local.name_prefix}}-oac"
  description                       = "Allow CloudFront to access the private S3 origin."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}}

resource "aws_acm_certificate" "{context["certificate_label"]}" {{
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {{
    create_before_destroy = true
  }}
}}

resource "aws_route53_record" "{context["certificate_label"]}_validation" {{
  for_each = {{
    for option in aws_acm_certificate.{context["certificate_label"]}.domain_validation_options :
    option.domain_name => {{
      name   = option.resource_record_name
      record = option.resource_record_value
      type   = option.resource_record_type
    }}
  }}

  zone_id = data.aws_route53_zone.{context["zone_label"]}.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}}

resource "aws_acm_certificate_validation" "{context["certificate_label"]}" {{
  certificate_arn         = aws_acm_certificate.{context["certificate_label"]}.arn
  validation_record_fqdns = [for record in aws_route53_record.{context["certificate_label"]}_validation : record.fqdn]
}}

resource "aws_cloudfront_distribution" "{context["distribution_label"]}" {{
  enabled             = true
  default_root_object = "{context["root_object"]}"
  price_class         = "{context["price_class"]}"

  aliases = [var.domain_name]

  origin {{
    domain_name              = aws_s3_bucket.{context["bucket_label"]}.bucket_regional_domain_name
    origin_id                = "s3-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.{context["oac_label"]}.id
  }}

  default_cache_behavior {{
    target_origin_id       = "s3-origin"
    viewer_protocol_policy = "{context["viewer_policy"]}"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    forwarded_values {{
      query_string = false

      cookies {{
        forward = "none"
      }}
    }}
  }}

  restrictions {{
    geo_restriction {{
      restriction_type = "none"
    }}
  }}

  viewer_certificate {{
    acm_certificate_arn      = aws_acm_certificate_validation.{context["certificate_label"]}.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }}
}}

resource "aws_s3_bucket_policy" "{context["bucket_label"]}" {{
  bucket = aws_s3_bucket.{context["bucket_label"]}.id

  policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [
      {{
        Sid       = "AllowCloudFrontServicePrincipalReadOnly"
        Effect    = "Allow"
        Principal = {{
          Service = "cloudfront.amazonaws.com"
        }}
        Action   = "s3:GetObject"
        Resource = "${{aws_s3_bucket.{context["bucket_label"]}.arn}}/*"
        Condition = {{
          StringEquals = {{
            "AWS:SourceArn" = aws_cloudfront_distribution.{context["distribution_label"]}.arn
          }}
        }}
      }}
    ]
  }})
}}

resource "aws_route53_record" "{context["distribution_label"]}" {{
  zone_id = data.aws_route53_zone.{context["zone_label"]}.zone_id
  name    = var.domain_name
  type    = "A"

  alias {{
    name                   = aws_cloudfront_distribution.{context["distribution_label"]}.domain_name
    zone_id                = aws_cloudfront_distribution.{context["distribution_label"]}.hosted_zone_id
    evaluate_target_health = false
  }}
}}
'''

    @staticmethod
    def _static_outputs_tf(context: dict[str, Any]) -> str:
        return f'''output "website_domain_name" {{
  description = "Website domain name."
  value       = var.domain_name
}}

output "s3_bucket_name" {{
  description = "S3 bucket that stores static assets."
  value       = aws_s3_bucket.{context["bucket_label"]}.bucket
}}

output "cloudfront_distribution_id" {{
  description = "CloudFront distribution ID."
  value       = aws_cloudfront_distribution.{context["distribution_label"]}.id
}}

output "cloudfront_domain_name" {{
  description = "CloudFront distribution domain name."
  value       = aws_cloudfront_distribution.{context["distribution_label"]}.domain_name
}}
'''

    @staticmethod
    def _static_tfvars(context: dict[str, Any]) -> str:
        return f'''aws_region       = "{context["region"]}"
project_name     = "{context["project_name"]}"
environment      = "{context["environment"]}"
domain_name      = "{context["domain_name"]}"
hosted_zone_name = "{context["zone_name"]}"
bucket_name      = "{context["bucket_name"]}"
'''

    @staticmethod
    def _static_readme(context: dict[str, Any]) -> str:
        return f"""# Generated Terraform for {context["architecture_id"]}

This Terraform creates a private S3 static website origin, CloudFront Origin Access Control, ACM DNS validation, CloudFront distribution, S3 bucket policy, and Route 53 alias record.

## Before running

1. Review `terraform.tfvars.example`.
2. Create an uncommitted `terraform.tfvars` with a globally unique `bucket_name`.
3. Confirm the Route 53 hosted zone exists for `hosted_zone_name`.

## Commands

```bash
terraform fmt
terraform init -backend=false
terraform validate
terraform plan
```
"""

    def _empty_repair_state(self):
        class EmptyState:
            repairs: list[dict[str, str]] = []
            derived_resources: list[dict[str, str]] = []
            warnings: list[str] = []
        return EmptyState()

    def _record_implementation_derivations(self, architecture: NormalizedArchitecture, derived: list[dict[str, str]]) -> None:
        def add(type_: str, name: str, derived_from: str, reason: str) -> None:
            if not any(item["type"] == type_ and item["name"] == name for item in derived):
                derived.append({"type": type_, "name": name, "derived_from": derived_from, "reason": reason})

        public_subnets = self._subnets(architecture, True)
        private_subnets = self._subnets(architecture, False)
        if architecture.first("aws_nat_gateway"):
            add("aws_eip", safe_identifier(f"{architecture.first('aws_nat_gateway').name}_eip"), architecture.first("aws_nat_gateway").id, "NAT Gateway requires an Elastic IP allocation.")
        if public_subnets:
            add("aws_route_table", "public", architecture.first("aws_vpc").id, "Public subnets require a route table.")
            for subnet in public_subnets:
                add("aws_route_table_association", f"{subnet['label']}_public", subnet["id"], "Public subnets require route table associations.")
            add("aws_route", "public_internet", architecture.first("aws_vpc").id, "The Internet Gateway route is required for public subnets.")
        if private_subnets:
            add("aws_route_table", "private", architecture.first("aws_vpc").id, "Private subnets require a route table.")
            for subnet in private_subnets:
                add("aws_route_table_association", f"{subnet['label']}_private", subnet["id"], "Private subnets require route table associations.")
            if architecture.first("aws_nat_gateway"):
                add("aws_route", "private_nat", architecture.first("aws_nat_gateway").id, "Private subnets require a NAT route for outbound access.")

    def _subnets(self, architecture: NormalizedArchitecture, public: bool) -> list[dict[str, Any]]:
        resources = architecture.by_type("aws_subnet")
        selected: list[NormalizedResource] = []
        for resource in resources:
            value = resource_cfg(resource, "public", "is_public", default=None)
            tier = str(resource_cfg(resource, "subnet_type", "network_tier", "tier", default=""))
            inferred_public = bool(value) if value is not None else ("public" in tier.lower() or "public" in resource.id.lower() or "public" in resource.name.lower())
            if inferred_public == public:
                selected.append(resource)
        used = {str(resource_cfg(item, "cidr_block", "cidr", "CidrBlock", default="")) for item in resources}
        vpc = architecture.first("aws_vpc")
        vpc_cidr = resource_cfg(vpc, "cidr_block", "cidr", "CidrBlock", default="10.0.0.0/16") if vpc else "10.0.0.0/16"
        result = []
        for index, resource in enumerate(selected):
            cidr = resource_cfg(resource, "cidr_block", "cidr", "CidrBlock")
            if not cidr:
                cidr = f"10.0.{index + (1 if public else 10)}.0/24"
            az = resource_cfg(resource, "availability_zone", "az", "AvailabilityZone", default=f"{architecture.region}{chr(97 + index)}")
            result.append({"id": resource.id, "label": resource.label, "cidr": cidr, "az": az})
        return result

    def _build_context(self, architecture: NormalizedArchitecture, options: GenerateOptions, warnings: list[str], repairs: list[dict[str, str]]) -> dict[str, Any]:
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
        listener = architecture.first("aws_lb_listener")
        execution_role = architecture.first("aws_iam_role")
        log_group = architecture.first("aws_cloudwatch_log_group")
        secret = architecture.first("aws_secretsmanager_secret")
        secret_version = architecture.first("aws_secretsmanager_secret_version")
        password = architecture.first("random_password")
        db_subnet_group = architecture.first("aws_db_subnet_group")
        public_subnets = self._subnets(architecture, True)
        private_subnets = self._subnets(architecture, False)
        if not public_subnets:
            public_subnets = private_subnets
        if not private_subnets:
            private_subnets = public_subnets

        project_name = safe_name(options.project_name or self.settings.default_project_name)
        environment = safe_name(options.environment or self.settings.default_environment)
        vpc_cidr = str(resource_cfg(vpc, "cidr_block", "cidr", "CidrBlock", default="10.0.0.0/16"))
        container_port = int(resource_cfg(ecs, "container_port", "port", "containerPort", default=80) if ecs else 80)
        context = {
            "architecture_id": architecture.architecture_id,
            "architecture_version": architecture.architecture_version,
            "generator_version": self.settings.generator_version,
            "project_name": project_name,
            "environment": environment,
            "region": options.aws_region or architecture.region,
            "vpc_cidr": vpc_cidr,
            "container_port": container_port,
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
            "ecs_subnets": private_subnets or public_subnets,
            "vpc_label": vpc.label if vpc else "vpc",
            "igw_label": igw.label if igw else "internet_gateway",
            "nat_label": nat.label if nat else None,
            "eip_label": safe_identifier(f"{nat.name}_eip") if nat else "nat_eip",
            "alb_label": alb.label if alb else None,
            "alb_sg_label": alb_sg.label if alb_sg else "alb_sg",
            "ecs_sg_label": ecs_sg.label if ecs_sg else "ecs_sg",
            "rds_sg_label": rds_sg.label if rds_sg else "rds_sg",
            "target_group_label": target_group.label if target_group else "target_group",
            "listener_label": listener.label if listener else "http",
            "ecs_cluster_label": (architecture.first("aws_ecs_cluster").label if architecture.first("aws_ecs_cluster") else "ecs_cluster"),
            "ecs_service_label": ecs.label if ecs else "ecs_service",
            "task_definition_label": (architecture.first("aws_ecs_task_definition").label if architecture.first("aws_ecs_task_definition") else "task_definition"),
            "ecs_execution_role_label": execution_role.label if execution_role else "ecs_execution_role",
            "log_group_label": log_group.label if log_group else "ecs_logs",
            "log_retention_days": int(resource_cfg(log_group, "retention_in_days", "retention", default=7) if log_group else 7),
            "health_check_path": str(resource_cfg(target_group, "health_check_path", "path", default="/") if target_group else "/"),
            "warnings": warnings,
            "repairs": repairs,
        }
        return context
