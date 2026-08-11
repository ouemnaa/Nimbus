from __future__ import annotations

import logging
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
from app.schemas.plan import TerraformGenerationPlan
from app.schemas.terraform import GenerationMetadata, GenerationResponse

from .architecture_normalizer import normalize_architecture
from .architecture_validator import validate_architecture
from .artifact_writer import ArtifactWriter
from .pattern_registry import PatternRegistry

logger = logging.getLogger(__name__)


class TerraformGeneratorService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.registry = PatternRegistry()
        self.common_renderer = CommonFilesRenderer()
        self.ecs_renderers = [
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

    def generate(
        self,
        architecture: CanonicalArchitecture,
        options: GenerateOptions | None = None,
    ) -> GenerationResponse:
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
                next_steps=[
                    "Add a pattern definition and renderer support for the unsupported provider/resource types."
                ],
                metadata=GenerationMetadata(**metadata_base),
                error=(
                    "No supported Terraform pattern can render these provider types: "
                    + ", ".join(validation.unsupported_resources)
                ),
            )
        plan = self.registry.detect(normalized, options, self.settings)
        if plan is None:
            return GenerationResponse(
                generation_status="UNSUPPORTED",
                supported_resources=sorted(set(validation.supported_resources)),
                warnings=validation.warnings,
                next_steps=[
                    "Create a PatternDefinition with required provider types, repair rules, validation rules, and renderer templates."
                ],
                metadata=GenerationMetadata(**metadata_base),
                error=self.registry.missing_pattern_message(normalized),
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

        try:
            files = self._render_plan(plan)
            self.writer.write(files)
        except Exception as exc:
            logger.exception("Terraform template rendering failed")
            return GenerationResponse(
                generation_status="FAILED",
                supported_resources=plan.supported_resources,
                warnings=plan.warnings,
                repairs=plan.repairs,
                derived_resources=plan.derived_resources,
                metadata=GenerationMetadata(**metadata_base),
                error=f"Template rendering failed: {type(exc).__name__}: {exc}",
            )

        metadata_base["generated_file_count"] = len(files)
        return GenerationResponse(
            generation_status="SUCCESS",
            supported_resources=plan.supported_resources,
            files=files,
            derived_resources=plan.derived_resources,
            repairs=plan.repairs,
            warnings=plan.warnings,
            next_steps=plan.next_steps,
            metadata=GenerationMetadata(**metadata_base),
        )

    def _render_plan(self, plan: TerraformGenerationPlan) -> list[dict[str, str]]:
        if plan.pattern_id == "static_site_s3_cloudfront_route53_https":
            files_by_path = self._render_static_site(plan)
        else:
            context = plan.renderer_context()
            files_by_path = self.common_renderer.render_files(context)
            for renderer in self.ecs_renderers:
                files_by_path.update(renderer.render_files(context))

        return [
            {"path": path, "content": files_by_path[path]}
            for path in plan.template_set
            if path in files_by_path
        ]

    def _render_static_site(self, plan: TerraformGenerationPlan) -> dict[str, str]:
        context = plan.renderer_context()
        return {
            "versions.tf": _static_versions_tf(),
            "providers.tf": _static_providers_tf(),
            "variables.tf": _static_variables_tf(context),
            "locals.tf": _static_locals_tf(),
            "s3.tf": _static_s3_tf(context),
            "acm.tf": _static_acm_tf(context),
            "cloudfront.tf": _static_cloudfront_tf(context),
            "dns.tf": _static_dns_tf(context),
            "outputs.tf": _static_outputs_tf(context),
            "terraform.tfvars.example": _static_tfvars(context),
            "README.generated.md": _static_readme(context),
        }


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


def _static_providers_tf() -> str:
    return """provider "aws" {
  region = var.aws_region

  default_tags {
    tags = local.common_tags
  }
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

  default_tags {
    tags = local.common_tags
  }
}
"""


def _static_variables_tf(context: dict[str, Any]) -> str:
    return f'''variable "aws_region" {{
  description = "AWS region for S3 and Route 53 management."
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
}}

variable "hosted_zone_name" {{
  description = "Route 53 hosted zone name."
  type        = string
}}

variable "bucket_name" {{
  description = "Globally unique S3 bucket name for static website assets."
  type        = string
}}
'''


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


def _static_s3_tf(context: dict[str, Any]) -> str:
    return f'''resource "aws_s3_bucket" "{context["bucket_label"]}" {{
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
'''


def _static_acm_tf(context: dict[str, Any]) -> str:
    return f'''resource "aws_acm_certificate" "{context["certificate_label"]}" {{
  provider          = aws.us_east_1
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
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.{context["certificate_label"]}.arn
  validation_record_fqdns = [for record in aws_route53_record.{context["certificate_label"]}_validation : record.fqdn]
}}
'''


def _static_cloudfront_tf(context: dict[str, Any]) -> str:
    spa_block = """
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }
""" if context.get("spa_mode") else ""
    return f'''resource "aws_cloudfront_origin_access_control" "{context["oac_label"]}" {{
  name                              = "${{local.name_prefix}}-oac"
  description                       = "Allow CloudFront to access the private S3 origin."
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
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
{spa_block}
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
'''


def _static_dns_tf(context: dict[str, Any]) -> str:
    return f'''data "aws_route53_zone" "{context["zone_label"]}" {{
  name         = var.hosted_zone_name
  private_zone = false
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


def _static_tfvars(context: dict[str, Any]) -> str:
    return f'''aws_region       = "{context["region"]}"
project_name     = "{context["project_name"]}"
environment      = "{context["environment"]}"
domain_name      = "{context["domain_name"]}"
hosted_zone_name = "{context["hosted_zone_name"]}"
bucket_name      = "{context["bucket_name"]}"
'''


def _static_readme(context: dict[str, Any]) -> str:
    return f"""# Generated Terraform for {context["architecture_id"]}

This Terraform creates a private S3 static website origin, CloudFront Origin Access Control, ACM DNS validation in `us-east-1`, CloudFront distribution, S3 bucket policy, and Route 53 alias record.

## Before running Terraform

1. Review `terraform.tfvars.example`.
2. Create an uncommitted `terraform.tfvars` with real `domain_name`, `hosted_zone_name`, and a globally unique `bucket_name`.
3. Confirm the Route 53 hosted zone already exists.

## Terraform commands

```bash
terraform fmt
terraform init -backend=false
terraform validate
terraform plan
```

## Deploying React/Vite assets

Terraform does not upload frontend build files.

```bash
npm run build
aws s3 sync dist/ s3://<bucket-name>/ --delete
aws cloudfront create-invalidation --distribution-id <distribution-id> --paths "/*"
```
"""
