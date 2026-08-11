import pytest

from app.utils.hcl_safety import contains_forbidden_terraform_command, validate_artifact_path
from app.utils.naming import safe_identifier


def test_unsafe_identifiers_are_normalized():
    assert safe_identifier("dev-ecs-service") == "dev_ecs_service"
    assert safe_identifier("123-service") == "r_123_service"


def test_paths_are_relative_and_safe():
    assert validate_artifact_path("networking.tf") == "networking.tf"
    with pytest.raises(ValueError):
        validate_artifact_path("../secret.txt")
    with pytest.raises(ValueError):
        validate_artifact_path("/tmp/secret.txt")


def test_forbidden_terraform_commands():
    assert contains_forbidden_terraform_command(["terraform", "apply"])
    assert contains_forbidden_terraform_command(["terraform", "destroy", "-auto-approve"])
    assert not contains_forbidden_terraform_command(["terraform", "validate"])
