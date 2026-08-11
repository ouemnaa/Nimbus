import json
from pathlib import Path

from app.core.config import Settings
from app.schemas.architecture import CanonicalArchitecture, GenerateOptions
from app.services.generator_service import TerraformGeneratorService


FIXTURE = Path(__file__).parent / "fixtures" / "ecs_rds_architecture.json"


def load_fixture() -> CanonicalArchitecture:
    return CanonicalArchitecture.model_validate(json.loads(FIXTURE.read_text()))


def file_map(response):
    return {artifact.path: artifact.content for artifact in response.files}


def test_ecs_rds_generation_contains_expected_files(tmp_path):
    service = TerraformGeneratorService(Settings(generated_artifacts_dir=str(tmp_path / "generated"), llm_provider="none"))
    response = service.generate(load_fixture(), GenerateOptions())
    files = file_map(response)

    assert response.generation_status == "SUCCESS"
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
    assert "us-east-1b" in networking
    assert response.repairs
    assert any(repair.action == "add_public_subnet" for repair in response.repairs)
    assert any(repair.action == "add_private_subnet" for repair in response.repairs)
    assert any(repair.action == "replace_fake_reference" for repair in response.repairs)
    assert 'variable "container_image"' in file_map(response)["variables.tf"]
    assert 'default     = 80' in file_map(response)["variables.tf"]
    assert 'image     = var.container_image' in ecs
