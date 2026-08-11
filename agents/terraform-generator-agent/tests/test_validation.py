from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.schemas.architecture import FileArtifact, ValidateOptions
from app.services import validator_service as validator_module
from app.services.validator_service import TerraformValidatorService


def validator():
    return TerraformValidatorService(Settings(terraform_binary="terraform", validation_enable_terraform_init=True, validation_enable_terraform_plan=False))


def test_safe_file_paths_accepted(tmp_path):
    validator()._write_files(tmp_path, [FileArtifact(path="versions.tf", content="terraform {}\n")])
    assert (tmp_path / "versions.tf").exists()


@pytest.mark.parametrize("path", ["/tmp/versions.tf", "../versions.tf", "nested/../../versions.tf", "nested\\versions.tf"])
def test_unsafe_file_paths_rejected(tmp_path, path):
    with pytest.raises(ValueError):
        validator()._write_files(tmp_path, [FileArtifact(path=path, content="")])


def test_missing_terraform_returns_skipped(monkeypatch):
    monkeypatch.setattr(validator_module.shutil, "which", lambda _: None)
    result = validator().validate([FileArtifact(path="versions.tf", content="terraform {}\n")])
    assert result.validation_status == "SKIPPED"
    assert "not found" in result.warnings[0].lower()


def test_failed_validate_returns_structured_error(monkeypatch):
    monkeypatch.setattr(validator_module.shutil, "which", lambda _: "/usr/bin/terraform")

    def fake_run(command, **kwargs):
        is_validate = "validate" in command
        return SimpleNamespace(returncode=1 if is_validate else 0, stdout="", stderr="invalid configuration" if is_validate else "")

    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    result = validator().validate([FileArtifact(path="versions.tf", content="terraform {}\n")])
    assert result.validation_status == "FAILED"
    assert any("terraform_validate" in item for item in result.errors)


def test_forbidden_commands_are_never_run(monkeypatch):
    monkeypatch.setattr(validator_module.shutil, "which", lambda _: "/usr/bin/terraform")
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(validator_module.subprocess, "run", fake_run)
    validator().validate([FileArtifact(path="versions.tf", content="terraform {}\n")], ValidateOptions(enable_plan=False))
    assert all(not any(part in {"apply", "destroy", "import", "state", "force-unlock"} for part in command) for command in commands)
