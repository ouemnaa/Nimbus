from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from shlex import join

from app.core.config import Settings
from app.schemas.architecture import FileArtifact, ValidateOptions
from app.schemas.validation import ValidationCheck, ValidationResponse
from app.utils.hcl_safety import contains_forbidden_terraform_command, validate_artifact_path


class TerraformValidatorService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate(self, files: list[FileArtifact], options: ValidateOptions | None = None) -> ValidationResponse:
        options = options or ValidateOptions()
        binary = shutil.which(self.settings.terraform_binary)
        if not binary:
            return ValidationResponse(
                validation_status="SKIPPED",
                warnings=["Terraform CLI was not found. Install Terraform and rerun validation."],
            )

        temp_path: Path | None = None
        try:
            if options.debug:
                temp_path = Path(tempfile.mkdtemp(prefix="nimbus-terraform-"))
                self._write_files(temp_path, files)
                return self._run_checks(temp_path, options)
            with tempfile.TemporaryDirectory(prefix="nimbus-terraform-") as temp_dir:
                temp_path = Path(temp_dir)
                self._write_files(temp_path, files)
                return self._run_checks(temp_path, options)
        except ValueError as exc:
            return ValidationResponse(validation_status="FAILED", errors=[str(exc)])
        except Exception as exc:
            return ValidationResponse(validation_status="FAILED", errors=[f"Validation failed: {type(exc).__name__}: {exc}"])

    def _write_files(self, root: Path, files: list[FileArtifact]) -> None:
        for artifact in files:
            relative = validate_artifact_path(artifact.path)
            destination = (root / relative).resolve()
            if root not in destination.parents:
                raise ValueError(f"Artifact path escapes temporary directory: {artifact.path}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(artifact.content, encoding="utf-8")

    def _run_checks(self, root: Path, options: ValidateOptions) -> ValidationResponse:
        checks: list[ValidationCheck] = []
        errors: list[str] = []
        warnings: list[str] = []

        fmt = self._run(root, [self.settings.terraform_binary, "fmt", "-check"], "terraform_fmt")
        checks.append(fmt)
        if fmt.status == "FAILED":
            errors.append(self._check_error(fmt))

        enable_init = self.settings.validation_enable_terraform_init if options.enable_init is None else options.enable_init
        if enable_init:
            init = self._run(root, [self.settings.terraform_binary, "init", "-backend=false", "-input=false"], "terraform_init")
            checks.append(init)
            if init.status == "FAILED":
                errors.append(self._check_error(init))
        else:
            warnings.append("Terraform init was disabled for this validation request.")

        if not errors or not any(check.name == "terraform_init" and check.status == "FAILED" for check in checks):
            validate = self._run(root, [self.settings.terraform_binary, "validate"], "terraform_validate")
            checks.append(validate)
            if validate.status == "FAILED":
                errors.append(self._check_error(validate))

        if options.enable_plan:
            if self.settings.validation_enable_terraform_plan:
                plan_command = [self.settings.terraform_binary, "plan", "-input=false", "-lock=false"]
                plan = self._run(root, plan_command, "terraform_plan")
                checks.append(plan)
                if plan.status == "FAILED":
                    errors.append(self._check_error(plan))
            else:
                warnings.append("Terraform plan was requested but disabled by VALIDATION_ENABLE_TERRAFORM_PLAN.")

        status = "FAILED" if errors else "PASSED"
        return ValidationResponse(validation_status=status, checks=checks, errors=errors, warnings=warnings)

    def _run(self, root: Path, command: list[str], name: str) -> ValidationCheck:
        if contains_forbidden_terraform_command(command):
            return ValidationCheck(name=name, status="FAILED", command=join(command), stderr="Forbidden Terraform command.")
        try:
            completed = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=self.settings.validation_timeout_seconds,
                check=False,
                shell=False,
            )
            status = "PASSED" if completed.returncode == 0 else "FAILED"
            return ValidationCheck(
                name=name,
                status=status,
                command=join(command),
                stdout=completed.stdout[-20000:],
                stderr=completed.stderr[-20000:],
                return_code=completed.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            return ValidationCheck(name=name, status="FAILED", command=join(command), stdout=str(exc.stdout or ""), stderr="Terraform command timed out.")
        except FileNotFoundError:
            return ValidationCheck(name=name, status="SKIPPED", command=join(command), stderr="Terraform CLI was not found.")

    @staticmethod
    def _check_error(check: ValidationCheck) -> str:
        detail = check.stderr.strip() or check.stdout.strip() or "Terraform returned a non-zero exit code."
        return f"{check.name}: {detail}"
