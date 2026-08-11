"""Tests for TerraformSafetyPolicyChecker — HCL text scan for dangerous configurations."""

from __future__ import annotations

import pytest

from app.schemas.architecture import FileArtifact
from app.schemas.plan import TerraformGenerationPlan
from app.safety.policy_checker import TerraformSafetyPolicyChecker


def _checker() -> TerraformSafetyPolicyChecker:
    return TerraformSafetyPolicyChecker()


def _dummy_plan(env: str = "dev", rds_public: bool = False) -> TerraformGenerationPlan:
    return TerraformGenerationPlan(
        pattern_id="ecs_fargate_alb_rds_dev",
        project_name="nimbus",
        environment=env,
        aws_region="us-east-1",
        architecture_id="arch-123",
        architecture_version="1.0.0",
        resources={"rds_publicly_accessible": rds_public},
    )


# ---------------------------------------------------------------------------
# Test 1: Detects RDS publicly_accessible=true
# ---------------------------------------------------------------------------

def test_detects_public_rds() -> None:
    files = [
        FileArtifact(
            path="database.tf",
            content="""
            resource "aws_db_instance" "db" {
              allocated_storage   = 20
              engine              = "postgres"
              publicly_accessible = true
            }
            """
        )
    ]
    result = _checker().check(files, _dummy_plan())
    assert result.has_critical is True
    assert any(f.code == "PUBLIC_RDS" for f in result.findings)


# ---------------------------------------------------------------------------
# Test 2: Detects 5432 open to 0.0.0.0/0
# ---------------------------------------------------------------------------

def test_detects_open_database_port() -> None:
    files = [
        FileArtifact(
            path="security_groups.tf",
            content="""
            resource "aws_security_group" "rds_sg" {
              ingress {
                from_port   = 5432
                to_port     = 5432
                protocol    = "tcp"
                cidr_blocks = ["0.0.0.0/0"]
              }
            }
            """
        )
    ]
    result = _checker().check(files, _dummy_plan())
    assert result.has_critical is True
    assert any(f.code == "OPEN_DATABASE_PORT" for f in result.findings)


# ---------------------------------------------------------------------------
# Test 3: Detects AWS access keys
# ---------------------------------------------------------------------------

def test_detects_aws_credentials() -> None:
    files = [
        FileArtifact(
            path="providers.tf",
            content="""
            provider "aws" {
              region     = "us-east-1"
              access_key = "AKIA1234567890ABCDEF"
              secret_key = "abc/123+456XYZ"
            }
            """
        )
    ]
    result = _checker().check(files, _dummy_plan())
    assert result.has_critical is True
    assert any(f.code == "HARDCODED_AWS_KEY" for f in result.findings)


# ---------------------------------------------------------------------------
# Test 4: Detects plaintext DB password default
# ---------------------------------------------------------------------------

def test_detects_plaintext_db_password() -> None:
    files = [
        FileArtifact(
            path="variables.tf",
            content="""
            variable "db_password" {
              type      = string
              default   = "supersecretpassword123"
              sensitive = true
            }
            """
        )
    ]
    result = _checker().check(files, _dummy_plan())
    assert result.has_critical is True
    assert any(f.code == "PLAINTEXT_DB_PASSWORD" for f in result.findings)


# ---------------------------------------------------------------------------
# Test 5: Detects Admin IAM policy
# ---------------------------------------------------------------------------

def test_detects_admin_iam_policy() -> None:
    files = [
        FileArtifact(
            path="iam.tf",
            content="""
            resource "aws_iam_role_policy_attachment" "admin" {
              role       = aws_iam_role.role.name
              policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
            }
            """
        )
    ]
    result = _checker().check(files, _dummy_plan())
    # Admin IAM is high, not critical
    assert any(f.code == "ADMIN_IAM" and f.severity == "HIGH" for f in result.findings)


# ---------------------------------------------------------------------------
# Test 6: Detects ECS public IP with open direct container ingress
# ---------------------------------------------------------------------------

def test_detects_ecs_public_ip_with_open_direct_ingress() -> None:
    files = [
        FileArtifact(
            path="ecs.tf",
            content="""
            resource "aws_ecs_service" "svc" {
              network_configuration {
                assign_public_ip = true
              }
            }

            resource "aws_security_group" "direct_sg" {
              ingress {
                from_port   = 8080
                to_port     = 8080
                protocol    = "tcp"
                cidr_blocks = ["0.0.0.0/0"]
              }
            }
            """
        )
    ]
    result = _checker().check(files, _dummy_plan())
    assert any(f.code == "PUBLIC_ECS_DIRECT_INGRESS" and f.severity == "HIGH" for f in result.findings)


# ---------------------------------------------------------------------------
# Test 7: Allows ECS public IP when inbound is restricted to ALB (or port 80 only)
# ---------------------------------------------------------------------------

def test_allows_ecs_public_ip_with_restricted_ingress() -> None:
    files = [
        FileArtifact(
            path="ecs.tf",
            content="""
            resource "aws_ecs_service" "svc" {
              network_configuration {
                assign_public_ip = true
              }
            }

            resource "aws_security_group" "restricted_sg" {
              ingress {
                from_port       = 80
                to_port         = 80
                protocol        = "tcp"
                security_groups = ["sg-123456"]
              }
            }
            """
        )
    ]
    result = _checker().check(files, _dummy_plan())
    assert not any(f.code == "PUBLIC_ECS_DIRECT_INGRESS" for f in result.findings)
