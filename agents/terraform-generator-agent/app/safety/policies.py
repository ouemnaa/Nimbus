"""
Safety policy definitions.

Each policy is a callable that receives (file_content, filename, plan_context)
and yields SafetyFinding instances when violations are detected.
"""

from __future__ import annotations

import re
from typing import Any, Generator

from .findings import SafetyFinding


PolicyGenerator = Generator[SafetyFinding, None, None]


# ---------------------------------------------------------------------------
# CRITICAL policies
# ---------------------------------------------------------------------------

_FORBIDDEN_TF_COMMANDS = re.compile(
    r"\bterraform\s+(apply|destroy|import|state|force-unlock)\b"
)

# AWS access key pattern: AKIA / ASIA / AROA + 16 uppercase alphanumeric
_AWS_ACCESS_KEY = re.compile(r"\b(AKIA|ASIA|AROA)[A-Z0-9]{16}\b")

# AWS secret key: 40-char base64-like string (only meaningful near "secret" keyword)
_AWS_SECRET_KEY = re.compile(
    r'(?:aws_secret_access_key|secret_access_key)\s*[=:]\s*["\']?[A-Za-z0-9+/]{40}["\']?',
    re.IGNORECASE,
)

_RDS_PUBLICLY_ACCESSIBLE_TRUE = re.compile(
    r"publicly_accessible\s*=\s*true",
    re.IGNORECASE,
)

# Plaintext DB password variable with a literal default value (not a variable reference)
_PLAINTEXT_DB_PWD = re.compile(
    r'variable\s+"[^"]*(?:password|pwd|pass)[^"]*"\s*\{[^}]*default\s*=\s*"[^"]{3,}"',
    re.IGNORECASE | re.DOTALL,
)


def policy_forbidden_commands(content: str, filename: str, _ctx: dict[str, Any]) -> PolicyGenerator:
    if _FORBIDDEN_TF_COMMANDS.search(content):
        yield SafetyFinding(
            severity="CRITICAL",
            code="FORBIDDEN_COMMAND",
            message=f"Forbidden Terraform command (apply/destroy/import/state/force-unlock) found in {filename}.",
            file=filename,
            recommendation="Remove all terraform apply/destroy/import/state/force-unlock commands. Nimbus never runs these.",
        )


def policy_aws_credentials(content: str, filename: str, _ctx: dict[str, Any]) -> PolicyGenerator:
    if _AWS_ACCESS_KEY.search(content) or _AWS_SECRET_KEY.search(content):
        yield SafetyFinding(
            severity="CRITICAL",
            code="HARDCODED_AWS_KEY",
            message=f"AWS access or secret key detected in {filename}.",
            file=filename,
            recommendation="Remove all AWS credentials from Terraform files. Use IAM roles or environment variables.",
        )


def policy_public_rds(content: str, filename: str, ctx: dict[str, Any]) -> PolicyGenerator:
    if _RDS_PUBLICLY_ACCESSIBLE_TRUE.search(content):
        explicitly_required = ctx.get("rds_publicly_accessible", False)
        if not explicitly_required:
            yield SafetyFinding(
                severity="CRITICAL",
                code="PUBLIC_RDS",
                message=f"RDS instance has publicly_accessible=true in {filename}.",
                file=filename,
                recommendation="Set publicly_accessible=false. Use a bastion host or VPN for DB access.",
            )


def policy_open_database_port(content: str, filename: str, _ctx: dict[str, Any]) -> PolicyGenerator:
    # Split content by 'resource' or 'ingress' to check individual blocks
    blocks = re.split(r"\b(?:resource|ingress)\b", content)
    for block in blocks:
        if "5432" in block and "0.0.0.0/0" in block:
            yield SafetyFinding(
                severity="CRITICAL",
                code="OPEN_DATABASE_PORT",
                message=f"Security group opens port 5432 to 0.0.0.0/0 in {filename}.",
                file=filename,
                recommendation="Restrict PostgreSQL port 5432 to the ECS security group only.",
            )


def policy_plaintext_db_password(content: str, filename: str, _ctx: dict[str, Any]) -> PolicyGenerator:
    if _PLAINTEXT_DB_PWD.search(content):
        yield SafetyFinding(
            severity="CRITICAL",
            code="PLAINTEXT_DB_PASSWORD",
            message=f"Plaintext database password variable with literal default found in {filename}.",
            file=filename,
            recommendation=(
                "Do not use plaintext password defaults. Use random_password + Secrets Manager. "
                "Nimbus generates passwords via random_password resource."
            ),
        )


# ---------------------------------------------------------------------------
# HIGH policies
# ---------------------------------------------------------------------------

_ADMIN_IAM = re.compile(r"AdministratorAccess", re.IGNORECASE)

_WILDCARD_IAM_ACTIONS = re.compile(
    r'"Action"\s*:\s*(?:"[^"]*\*[^"]*"|\[.*?"\*".*?\])',
    re.IGNORECASE | re.DOTALL,
)
_WILDCARD_IAM_ACTIONS_TF = re.compile(
    r"actions\s*=\s*\[.*?\"[^\"]*\*[^\"]*\"",
    re.IGNORECASE | re.DOTALL,
)

# ECS task has public IP (assign_public_ip=true)
_ECS_PUBLIC_IP = re.compile(r"assign_public_ip\s*=\s*true", re.IGNORECASE)

_S3_PUBLIC_ACCESS_DISABLED = re.compile(
    r"block_public_acls\s*=\s*false|block_public_policy\s*=\s*false"
    r"|restrict_public_buckets\s*=\s*false|ignore_public_acls\s*=\s*false",
    re.IGNORECASE,
)


def policy_admin_iam(content: str, filename: str, _ctx: dict[str, Any]) -> PolicyGenerator:
    if _ADMIN_IAM.search(content):
        yield SafetyFinding(
            severity="HIGH",
            code="ADMIN_IAM",
            message=f"IAM AdministratorAccess policy attachment detected in {filename}.",
            file=filename,
            recommendation="Use least-privilege IAM policies. Never attach AdministratorAccess to application roles.",
        )


def policy_wildcard_iam(content: str, filename: str, _ctx: dict[str, Any]) -> PolicyGenerator:
    if _WILDCARD_IAM_ACTIONS.search(content) or _WILDCARD_IAM_ACTIONS_TF.search(content):
        yield SafetyFinding(
            severity="HIGH",
            code="WILDCARD_IAM",
            message=f"Wildcard IAM action (*) detected in {filename}.",
            file=filename,
            recommendation="Restrict IAM actions to the minimum required. Avoid action wildcards.",
        )


def policy_ecs_public_direct_ingress(content: str, filename: str, ctx: dict[str, Any]) -> PolicyGenerator:
    """
    Flag when ECS has public IP AND a security group in the same file allows 0.0.0.0/0
    on a port that is NOT the ALB-only port (80/443). Only flag when both conditions
    co-exist in the same file.
    """
    if _ECS_PUBLIC_IP.search(content):
        blocks = re.split(r"\b(?:resource|ingress)\b", content)
        for block in blocks:
            # Look for 0.0.0.0/0 and a port that is not 80 or 443
            if "0.0.0.0/0" in block:
                # Find all numbers that look like from_port / to_port
                ports = [int(p) for p in re.findall(r"\b(?:from_port|to_port|port)\s*=\s*(\d+)\b", block)]
                # If there are any ports other than 80 and 443, flag it
                has_unsafe_port = any(port not in (80, 443) for port in ports)
                if has_unsafe_port:
                    yield SafetyFinding(
                        severity="HIGH",
                        code="PUBLIC_ECS_DIRECT_INGRESS",
                        message=(
                            f"ECS task has assign_public_ip=true AND a security group allows direct "
                            f"ingress from 0.0.0.0/0 on a non-HTTP port in {filename}."
                        ),
                        file=filename,
                        recommendation=(
                            "ECS security group should allow inbound only from the ALB security group, "
                            "not from 0.0.0.0/0. The ALB is the public entry point."
                        ),
                    )


def policy_s3_public_access(content: str, filename: str, ctx: dict[str, Any]) -> PolicyGenerator:
    if _S3_PUBLIC_ACCESS_DISABLED.search(content):
        explicitly_required = ctx.get("s3_public_access_required", False)
        if not explicitly_required:
            yield SafetyFinding(
                severity="HIGH",
                code="S3_PUBLIC_ACCESS",
                message=f"S3 public access block is disabled in {filename}.",
                file=filename,
                recommendation="Enable all four S3 public access block settings unless explicitly required.",
            )


# ---------------------------------------------------------------------------
# MEDIUM policies
# ---------------------------------------------------------------------------

_HTTP_ONLY_ALB = re.compile(
    r"aws_lb_listener.*?protocol\s*=\s*\"HTTP\"",
    re.IGNORECASE | re.DOTALL,
)

_SINGLE_AZ_RDS = re.compile(r"multi_az\s*=\s*false", re.IGNORECASE)

_DELETION_PROTECTION_OFF = re.compile(r"deletion_protection\s*=\s*false", re.IGNORECASE)

_SKIP_FINAL_SNAPSHOT = re.compile(r"skip_final_snapshot\s*=\s*true", re.IGNORECASE)

_ECS_LOG_CONFIG = re.compile(r"logDriver|awslogs", re.IGNORECASE)


def policy_http_only_alb(content: str, filename: str, _ctx: dict[str, Any]) -> PolicyGenerator:
    if _HTTP_ONLY_ALB.search(content):
        yield SafetyFinding(
            severity="MEDIUM",
            code="HTTP_ONLY_ALB",
            message=f"ALB listener uses HTTP only (no HTTPS) in {filename}.",
            file=filename,
            recommendation="Add an HTTPS listener with an ACM certificate for production workloads.",
        )


def policy_single_az_rds(content: str, filename: str, ctx: dict[str, Any]) -> PolicyGenerator:
    env = ctx.get("environment", "dev")
    if _SINGLE_AZ_RDS.search(content) and env not in ("dev", "development", "local", "test"):
        yield SafetyFinding(
            severity="MEDIUM",
            code="SINGLE_AZ_RDS",
            message=f"RDS has multi_az=false in {filename} (non-dev environment: {env}).",
            file=filename,
            recommendation="Enable multi_az=true for production RDS to ensure high availability.",
        )


def policy_deletion_protection(content: str, filename: str, ctx: dict[str, Any]) -> PolicyGenerator:
    env = ctx.get("environment", "dev")
    if _DELETION_PROTECTION_OFF.search(content) and env not in ("dev", "development", "local", "test"):
        yield SafetyFinding(
            severity="MEDIUM",
            code="UNKNOWN",
            message=f"deletion_protection=false on a resource in {filename} (non-dev: {env}).",
            file=filename,
            recommendation="Enable deletion_protection for production databases and load balancers.",
        )


def policy_skip_final_snapshot(content: str, filename: str, ctx: dict[str, Any]) -> PolicyGenerator:
    env = ctx.get("environment", "dev")
    if _SKIP_FINAL_SNAPSHOT.search(content) and env not in ("dev", "development", "local", "test"):
        yield SafetyFinding(
            severity="MEDIUM",
            code="UNKNOWN",
            message=f"skip_final_snapshot=true in {filename} (non-dev: {env}). Data loss risk.",
            file=filename,
            recommendation="Set skip_final_snapshot=false for production RDS instances.",
        )


def policy_no_ecs_logs(content: str, filename: str, _ctx: dict[str, Any]) -> PolicyGenerator:
    if "aws_ecs_task_definition" in content and not _ECS_LOG_CONFIG.search(content):
        yield SafetyFinding(
            severity="MEDIUM",
            code="NO_ECS_LOGS",
            message=f"ECS task definition has no CloudWatch log configuration in {filename}.",
            file=filename,
            recommendation="Add awslogs logDriver configuration to ECS container definitions.",
        )


# ---------------------------------------------------------------------------
# Ordered list of all policies
# ---------------------------------------------------------------------------

ALL_POLICIES = [
    # CRITICAL
    policy_forbidden_commands,
    policy_aws_credentials,
    policy_public_rds,
    policy_open_database_port,
    policy_plaintext_db_password,
    # HIGH
    policy_admin_iam,
    policy_wildcard_iam,
    policy_ecs_public_direct_ingress,
    policy_s3_public_access,
    # MEDIUM
    policy_http_only_alb,
    policy_single_az_rds,
    policy_deletion_protection,
    policy_skip_final_snapshot,
    policy_no_ecs_logs,
]
