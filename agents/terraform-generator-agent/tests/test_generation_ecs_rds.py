import json
import shutil
from pathlib import Path

import pytest

from app.core.config import Settings
from app.schemas.architecture import CanonicalArchitecture, GenerateOptions
from app.services.generator_service import TerraformGeneratorService
from app.services.validator_service import TerraformValidatorService


FIXTURE = Path(__file__).parent / "fixtures" / "ecs_rds_architecture.json"


def load_fixture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(json.loads(FIXTURE.read_text()))


def file_map(response):
    return {artifact.path: artifact.content for artifact in response.files}


def test_ecs_rds_generation_contains_expected_files(tmp_path):
    service = TerraformGeneratorService(Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none"))
    response = service.generate(load_fixture(), GenerateOptions())
    files = file_map(response)

    assert response.generation_status in {"SUCCESS", "NEEDS_REVIEW"}
    expected = {
        "networking.tf", "security_groups.tf", "load_balancing.tf", "iam.tf", "observability.tf",
        "secrets.tf", "database.tf", "ecs.tf", "outputs.tf", "terraform.tfvars.example",
    }
    assert expected.issubset(files)
    assert "resource \"aws_vpc\"" in files["networking.tf"]
    assert "resource \"aws_subnet\"" in files["networking.tf"]
    assert "resource \"aws_internet_gateway\"" in files["networking.tf"]
    assert "resource \"aws_nat_gateway\"" in files["networking.tf"]
    assert "resource \"aws_eip\"" in files["networking.tf"]
    assert "allocation_id = aws_eip.dev_nat_gw_eip.id" in files["networking.tf"]
    assert "resource \"aws_route_table_association\"" in files["networking.tf"]
    assert "resource \"aws_security_group\"" in files["security_groups.tf"]
    assert "resource \"aws_lb_target_group\"" in files["load_balancing.tf"]
    assert "resource \"aws_lb_listener\"" in files["load_balancing.tf"]
    assert "resource \"aws_ecs_cluster\"" in files["ecs.tf"]
    assert "resource \"aws_ecs_task_definition\"" in files["ecs.tf"]
    assert "resource \"aws_ecs_service\"" in files["ecs.tf"]
    assert "resource \"aws_db_subnet_group\"" in files["database.tf"]
    assert "resource \"aws_db_instance\"" in files["database.tf"]
    assert "resource \"aws_secretsmanager_secret\"" in files["secrets.tf"]
    assert "resource \"aws_secretsmanager_secret_version\"" in files["secrets.tf"]
    assert "resource \"aws_cloudwatch_log_group\"" in files["observability.tf"]
    assert "output \"vpc_id\"" in files["outputs.tf"]
    assert "container_image = \"replace-with-your-image\"" in files["terraform.tfvars.example"]
    assert "password" not in files["terraform.tfvars.example"].lower()


def test_generation_repairs_single_subnets_and_missing_container_values(tmp_path):
    service = TerraformGeneratorService(Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none"))
    response = service.generate(load_fixture(), GenerateOptions())
    networking = file_map(response)["networking.tf"]
    ecs = file_map(response)["ecs.tf"]

    assert networking.count('resource "aws_subnet"') == 4
    assert 'data "aws_availability_zones" "available"' in networking
    assert "data.aws_availability_zones.available.names[1]" in networking
    assert response.repairs
    assert any(repair.action == "add_public_subnet" for repair in response.repairs)
    assert any(repair.action == "add_private_subnet" for repair in response.repairs)
    assert any(repair.action == "replace_fake_reference" for repair in response.repairs)
    assert 'variable "container_image"' in file_map(response)["variables.tf"]
    assert 'default     = 80' in file_map(response)["variables.tf"]
    assert 'image     = var.container_image' in ecs


def test_ecs_public_no_nat_generation_sets_assign_public_ip_true(tmp_path):
    # Load the new public no-NAT fixture
    public_no_nat_fixture = CanonicalArchitecture.model_validate(
        json.loads((Path(__file__).parent / "fixtures" / "ecs_public_no_nat_architecture.json").read_text())
    )
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(public_no_nat_fixture, GenerateOptions())
    files = file_map(response)

    assert response.generation_status in {"SUCCESS", "NEEDS_REVIEW"}
    assert response.generation_mode == "DETERMINISTIC_SUPPORTED"
    assert response.deployment_strategy == "public_ecs_no_nat_low_cost_dev"

    networking = files["networking.tf"]
    ecs = files["ecs.tf"]

    # NAT/EIP must not be generated
    assert "aws_nat_gateway" not in networking
    assert "aws_eip" not in networking

    # ECS service must have assign_public_ip = true
    assert "assign_public_ip = true" in ecs


def test_ecs_private_no_nat_still_generates_files_with_review_warnings(tmp_path):
    private_no_nat_fixture = CanonicalArchitecture.model_validate(
        json.loads((Path(__file__).parent / "fixtures" / "ecs_private_no_nat_architecture.json").read_text())
    )
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(private_no_nat_fixture, GenerateOptions())
    files = file_map(response)

    assert response.generation_status == "NEEDS_REVIEW"
    assert response.generation_mode == "DETERMINISTIC_SUPPORTED"
    assert response.deployment_strategy == "public_ecs_no_nat_low_cost_dev"
    assert response.files
    assert "networking.tf" in files
    assert "ecs.tf" in files
    assert "assign_public_ip = true" in files["ecs.tf"]
    assert "aws_nat_gateway" not in files["networking.tf"]
    assert any(
        "Detected private ECS without NAT/VPC endpoints and repaired by using public ECS subnets with assign_public_ip=true."
        in warning for warning in response.warnings
    )
    assert not any(
        "CRITICAL: Private ECS subnets without NAT Gateway or VPC endpoints" in warning
        for warning in response.warnings
    )
    assert any("Add a NAT Gateway in a public subnet" in step for step in response.next_steps)


def test_readme_matches_public_ecs_no_nat_strategy(tmp_path):
    private_no_nat_fixture = CanonicalArchitecture.model_validate(
        json.loads((Path(__file__).parent / "fixtures" / "ecs_private_no_nat_architecture.json").read_text())
    )
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(private_no_nat_fixture, GenerateOptions())
    readme = file_map(response)["README.generated.md"]

    assert (
        "The ECS tasks run in public subnets with public IPs for low-cost outbound internet access, while inbound traffic is restricted to the ALB security group."
        in readme
    )


def test_ecs_name_prefix_keeps_alb_name_within_aws_limit(tmp_path):
    fixture = CanonicalArchitecture.model_validate(
        json.loads((Path(__file__).parent / "fixtures" / "ecs_public_no_nat_architecture.json").read_text())
    )
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(
        fixture,
        GenerateOptions(project_name="Nimbus Super Long Platform Name For Deterministic Terraform"),
    )
    locals_tf = file_map(response)["locals.tf"]
    load_balancing_tf = file_map(response)["load_balancing.tf"]

    assert 'environment_slug_raw   = replace(lower(var.environment), "/[^a-z0-9-]/", "-")' in locals_tf
    assert 'environment_slug       = trim(replace(local.environment_slug_raw, "/-+/", "-"), "-")' in locals_tf
    assert 'project_slug_raw       = replace(lower(var.project_name), "/[^a-z0-9-]/", "-")' in locals_tf
    assert 'project_slug           = trim(replace(local.project_slug_raw, "/-+/", "-"), "-")' in locals_tf
    assert 'name_prefix          = substr("${local.short_project_slug}-${local.short_environment_slug}", 0, 24)' in locals_tf
    assert 'alb_name             = substr("${local.name_prefix}-alb", 0, 32)' in locals_tf
    assert "name               = local.alb_name" in load_balancing_tf


def test_environment_development_uses_local_is_development(tmp_path):
    fixture = CanonicalArchitecture.model_validate(
        json.loads((Path(__file__).parent / "fixtures" / "ecs_public_no_nat_architecture.json").read_text())
    )
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(
        fixture,
        GenerateOptions(environment="development"),
    )
    locals_tf = file_map(response)["locals.tf"]
    database_tf = file_map(response)["database.tf"]

    assert 'is_development       = contains(["dev", "development"], lower(var.environment))' in locals_tf
    assert "skip_final_snapshot    = local.is_development" in database_tf
    assert "deletion_protection    = !local.is_development" in database_tf
    assert "apply_immediately      = local.is_development" in database_tf


def test_random_password_uses_rds_safe_special_characters(tmp_path):
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(load_fixture(), GenerateOptions())
    secrets_tf = file_map(response)["secrets.tf"]

    assert 'override_special = "!#$%&*()-_=+[]{}<>:?"' in secrets_tf


def test_networking_uses_availability_zones_data_source(tmp_path):
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(load_fixture(), GenerateOptions())
    networking_tf = file_map(response)["networking.tf"]

    assert 'data "aws_availability_zones" "available"' in networking_tf
    assert "data.aws_availability_zones.available.names[0]" in networking_tf
    assert "data.aws_availability_zones.available.names[1]" in networking_tf


def test_conditional_https_listener_uses_acm_certificate_arn(tmp_path):
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(load_fixture(), GenerateOptions())
    load_balancing_tf = file_map(response)["load_balancing.tf"]
    variables_tf = file_map(response)["variables.tf"]

    assert 'variable "acm_certificate_arn"' in variables_tf
    assert 'count             = var.acm_certificate_arn != null ? 1 : 0' in load_balancing_tf
    assert 'certificate_arn   = var.acm_certificate_arn' in load_balancing_tf


def test_ecs_service_depends_on_listener_and_secret_policy(tmp_path):
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(load_fixture(), GenerateOptions())
    ecs_tf = file_map(response)["ecs.tf"]

    assert "aws_iam_role_policy_attachment.ecs_task_execution_role_managed" in ecs_tf
    assert "aws_iam_role_policy.ecs_task_execution_role_secrets" in ecs_tf
    assert "aws_lb_listener.application_load_balancer_listener" in ecs_tf


@pytest.mark.skipif(shutil.which("terraform") is None, reason="Terraform CLI is not installed")
def test_generated_ecs_terraform_validate_catches_unknown_functions(tmp_path):
    service = TerraformGeneratorService(
        Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none")
    )
    response = service.generate(
        load_fixture(),
        GenerateOptions(project_name="Nimbus Project", environment="development"),
    )
    locals_tf = file_map(response)["locals.tf"]
    validator = TerraformValidatorService(
        Settings(
            generated_artifacts_dir=str(tmp_path / "generated"),
            validation_enable_terraform_init=False,
        )
    )

    assert "regexreplace(" not in locals_tf

    result = validator.validate(response.files)

    assert result.validation_status == "PASSED"

