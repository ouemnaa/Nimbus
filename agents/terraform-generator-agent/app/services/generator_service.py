from __future__ import annotations

import logging
from typing import Any

from app.core.config import Settings
from app.llm.factory import create_provider
from app.planning.llm_terraform_planner import LLMTerraformPlanner
from app.planning.plan_builder import TerraformPlanBuilder
from app.planning.terraform_resource_plan_coverage_validator import CoverageFinding
from app.planning.terraform_resource_plan_schema import TerraformResourcePlan
from app.reasoning.terraform_reasoning_agent import TerraformReasoningAgent
from app.rendering.generic_hcl_renderer import GenericHCLRenderer
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
from app.review.terraform_reviewer_agent import TerraformReviewerAgent
from app.safety.policy_checker import TerraformSafetyPolicyChecker
from app.schemas.architecture import CanonicalArchitecture, FileArtifact, GenerateOptions
from app.schemas.plan import TerraformGenerationPlan
from app.schemas.terraform import GenerationMetadata, GenerationResponse
from app.schemas.validation import ValidationResponse
from app.utils.hcl_safety import validate_artifact_path

from .architecture_normalizer import NormalizedArchitecture, normalize_architecture
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
        self.reasoning_agent = TerraformReasoningAgent()
        self.plan_builder = TerraformPlanBuilder()
        self.safety_checker = TerraformSafetyPolicyChecker()
        self.reviewer_agent = TerraformReviewerAgent()
        self.llm_planner = LLMTerraformPlanner()
        self.generic_renderer = GenericHCLRenderer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        architecture: CanonicalArchitecture,
        options: GenerateOptions | None = None,
    ) -> GenerationResponse:
        options = options or GenerateOptions()

        # Resolve per-request feature flags (None means use server default)
        reasoning_enabled = (
            options.enable_reasoning
            if options.enable_reasoning is not None
            else self.settings.terraform_reasoning_enabled
        )
        reviewer_enabled = (
            options.enable_reviewer
            if options.enable_reviewer is not None
            else self.settings.terraform_reviewer_enabled
        )
        draft_fallback_enabled = (
            options.enable_llm_draft_fallback
            if options.enable_llm_draft_fallback is not None
            else self.settings.terraform_llm_draft_fallback_enabled
        )

        # Resolve LLM provider (never raise on missing key — just go deterministic)
        llm = None
        try:
            llm = create_provider(self.settings)
        except Exception as exc:
            logger.warning("LLM provider unavailable (%s) — running in deterministic mode.", type(exc).__name__)

        llm_provider_name = llm.name if llm else "none"

        metadata_base: dict[str, Any] = {
            "generator_version": self.settings.generator_version,
            "generated_file_count": 0,
            "llm_provider": llm_provider_name,
            "architecture_id": "unknown",
            "architecture_version": "unknown",
            "reasoning_enabled": reasoning_enabled,
            "reviewer_enabled": reviewer_enabled,
            "draft_fallback_enabled": draft_fallback_enabled,
        }

        # 1. Normalize + validate architecture
        normalized = normalize_architecture(architecture, self.settings.default_aws_region)
        metadata_base["architecture_id"] = normalized.architecture_id
        metadata_base["architecture_version"] = normalized.architecture_version

        arch_validation = validate_architecture(normalized)

        # 2. Detect pattern
        supported_pattern_ids = [p.definition.pattern_id for p in self.registry.patterns]
        pattern_obj = self._find_pattern(normalized)
        detected_pattern_id = pattern_obj.definition.pattern_id if pattern_obj else None

        # 3. Run reasoning (always runs for deterministic patterns; uses LLM if enabled + available)
        reasoning_llm = llm if reasoning_enabled else None
        reasoning = self.reasoning_agent.reason(
            architecture=normalized,
            detected_pattern_id=detected_pattern_id,
            supported_patterns=supported_pattern_ids,
            current_plan=None,
            options={},
            llm=reasoning_llm,
        )

        # 4. Handle cases where no deterministic pattern matched, or unsupported
        # provider types prevent trusted deterministic rendering.
        if pattern_obj is None or arch_validation.unsupported_resources:
            return self._handle_no_pattern(
                normalized, reasoning, arch_validation, metadata_base,
                options, draft_fallback_enabled, llm, reviewer_enabled,
            )

        # 5. Build enriched plan (reasoning overrides ecs_subnets, assign_public_ip, etc.)
        if arch_validation.errors:
            return GenerationResponse(
                generation_status="NEEDS_INPUT",
                generation_mode="DETERMINISTIC_SUPPORTED",
                trusted=True,
                requires_human_review=False,
                pattern_id=detected_pattern_id,
                supported_resources=sorted(set(arch_validation.supported_resources)),
                warnings=arch_validation.warnings,
                reasoning=reasoning.model_dump(),
                next_steps=["Provide the missing deterministic architecture inputs and retry generation."],
                metadata=GenerationMetadata(**metadata_base),
                error=" ".join(arch_validation.errors),
            )

        try:
            plan = self.plan_builder.build(
                architecture=normalized,
                pattern=pattern_obj,
                reasoning=reasoning,
                options=options,
                settings=self.settings,
            )
        except Exception as exc:
            logger.exception("Plan builder failed")
            return self._failed(
                metadata_base, reasoning, str(exc),
                "Plan building failed — review architecture and reasoning output.",
            )

        # 6. If plan builder returned UNSUPPORTED (e.g. no deterministic fallback exists)
        if plan.generation_mode == "UNSUPPORTED":
            return self._unsupported(
                metadata_base,
                plan.warnings,
                arch_validation.supported_resources,
                [],
                error=plan.warnings[-1] if plan.warnings else "Strategy resolution failed.",
                next_steps=reasoning.required_inputs or ["Review architecture networking configuration."],
                reasoning=reasoning.model_dump(),
                pattern_id=detected_pattern_id,
                deployment_strategy=plan.deployment_strategy,
            )

        # 7. Render deterministic files
        try:
            files = self._render_plan(plan)
            local_output_dir = self.writer.write(
                files,
                project_id=options.project_id,
                architecture_id=normalized.architecture_id,
                architecture_version_id=options.architecture_version_id,
                architecture_version=normalized.architecture_version,
            )
            metadata_base["local_output_dir"] = local_output_dir
        except Exception as exc:
            logger.exception("Terraform template rendering failed")
            return self._failed(
                metadata_base, reasoning, f"Template rendering failed: {type(exc).__name__}: {exc}",
            )

        # 8. Safety policy check
        artifact_list = [FileArtifact(path=f["path"], content=f["content"]) for f in files]
        safety_result = self.safety_checker.check(artifact_list, plan)

        # 9. Build file artifacts for response
        file_artifacts = [FileArtifact(path=f["path"], content=f["content"]) for f in files]

        # 10. Reviewer (optional, LLM-only)
        reviewer_llm = llm if reviewer_enabled else None
        review_result = self.reviewer_agent.review(
            architecture=normalized,
            plan=plan,
            files=file_artifacts,
            validation_result=None,  # No validation at this stage; filled in by generate-and-validate
            safety_findings=safety_result,
            llm=reviewer_llm,
        )

        # 11. Determine final trust and status
        has_critical_safety = safety_result.has_critical
        has_critical_review = bool(review_result.critical_issues)
        has_reasoning_blockers = reasoning.reasoning_status == "NEEDS_INPUT"
        trusted = not has_critical_safety and not has_critical_review and not has_reasoning_blockers
        requires_human_review = has_critical_safety or has_critical_review or has_reasoning_blockers
        generation_status = "NEEDS_REVIEW" if requires_human_review else "SUCCESS"

        metadata_base["generated_file_count"] = len(files)
        next_steps = plan.next_steps
        if reasoning.required_inputs:
            next_steps = _merge_unique_lists(reasoning.required_inputs, next_steps)

        return GenerationResponse(
            generation_status=generation_status,
            generation_mode=plan.generation_mode,
            trusted=trusted,
            requires_human_review=requires_human_review,
            pattern_id=plan.pattern_id,
            deployment_strategy=plan.deployment_strategy,
            supported_resources=plan.supported_resources,
            files=file_artifacts,
            derived_resources=plan.derived_resources,
            repairs=plan.repairs,
            assumptions=[],
            required_inputs=reasoning.required_inputs,
            warnings=[*plan.warnings, *arch_validation.warnings],
            runtime_risks=plan.runtime_risks,
            validation_assertions=plan.validation_assertions,
            validation=self._validate_generated_artifacts(file_artifacts).model_dump(),
            safety_findings=[f.model_dump() for f in safety_result.findings],
            reasoning=reasoning.model_dump(),
            review=review_result.model_dump(),
            next_steps=next_steps,
            metadata=GenerationMetadata(**metadata_base),
            error=(
                "Generated Terraform with warnings. Review runtime risks and apply the recommended networking fixes before deployment."
                if has_reasoning_blockers else None
            ),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_pattern(self, normalized: NormalizedArchitecture):
        for pattern in self.registry.patterns:
            if pattern.matches(normalized):
                return pattern
        return None

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

    def _handle_no_pattern(
        self,
        normalized: NormalizedArchitecture,
        reasoning,
        arch_validation,
        metadata_base: dict,
        options: GenerateOptions,
        draft_fallback_enabled: bool,
        llm,
        reviewer_enabled: bool,
    ) -> GenerationResponse:
        if not draft_fallback_enabled or llm is None:
            mode = "UNSUPPORTED"
            return GenerationResponse(
                generation_status="UNSUPPORTED",
                generation_mode=mode,
                trusted=False,
                requires_human_review=True,
                draft_pattern_guess=_guess_draft_pattern(normalized),
                supported_resources=sorted(set(arch_validation.supported_resources)),
                unsupported_resources=sorted(set(arch_validation.unsupported_resources)),
                assumptions=[],
                required_inputs=reasoning.required_inputs,
                warnings=arch_validation.warnings,
                validation_assertions=[],
                reasoning=reasoning.model_dump(),
                next_steps=[
                    "Create a PatternDefinition with required provider types, repair rules, and renderer templates.",
                    "Or enable TERRAFORM_LLM_DRAFT_FALLBACK_ENABLED=true to generate an untrusted LLM-planned draft.",
                ],
                metadata=GenerationMetadata(**metadata_base),
                error=(
                    "No supported Terraform pattern can render these provider types: "
                    + ", ".join(sorted(set(arch_validation.unsupported_resources)))
                    if arch_validation.unsupported_resources
                    else self.registry.missing_pattern_message(normalized)
                ),
            )

        try:
            resource_plan, coverage_findings = self.llm_planner.create_plan(normalized, reasoning, llm)
        except Exception as exc:
            return GenerationResponse(
                generation_status="UNSUPPORTED",
                generation_mode="UNSUPPORTED",
                trusted=False,
                requires_human_review=True,
                draft_pattern_guess=_guess_draft_pattern(normalized),
                supported_resources=sorted(set(arch_validation.supported_resources)),
                unsupported_resources=sorted(set(arch_validation.unsupported_resources)),
                required_inputs=reasoning.required_inputs,
                warnings=[*arch_validation.warnings, "LLM planner could not produce a valid TerraformResourcePlan JSON."],
                reasoning=reasoning.model_dump(),
                metadata=GenerationMetadata(**metadata_base),
                error=f"LLM planner failed: {type(exc).__name__}: {exc}",
            )

        if not resource_plan.resources:
            logger.error(
                "planner_empty_plan architecture_id=%s planned_resource_count=%s planned_variable_count=%s architecture_resource_mapping_count=%s missing_inputs=%s warnings=%s",
                normalized.architecture_id,
                len(resource_plan.resources),
                len(resource_plan.variables),
                len(resource_plan.architecture_resource_mappings),
                resource_plan.missing_inputs,
                resource_plan.warnings,
            )
            return GenerationResponse(
                generation_status="FAILED",
                generation_mode="FAILED",
                trusted=False,
                requires_human_review=True,
                draft_pattern_name=resource_plan.draft_pattern_name,
                draft_pattern_guess=_guess_draft_pattern(normalized),
                supported_resources=sorted(set(arch_validation.supported_resources)),
                unsupported_resources=sorted(set(arch_validation.unsupported_resources)),
                assumptions=resource_plan.assumptions,
                required_inputs=reasoning.required_inputs,
                missing_inputs=resource_plan.missing_inputs,
                warnings=_merge_unique_lists(resource_plan.warnings, arch_validation.warnings),
                runtime_risks=resource_plan.runtime_risks,
                validation_assertions=resource_plan.validation_assertions,
                terraform_resource_plan=resource_plan.model_dump(mode="json"),
                architecture_resource_mappings=[m.model_dump(mode="json") for m in resource_plan.architecture_resource_mappings],
                external_dependencies=[d.model_dump(mode="json") for d in resource_plan.external_dependencies],
                coverage_findings=_normalize_coverage_findings(coverage_findings),
                reasoning=reasoning.model_dump(),
                metadata=GenerationMetadata(**metadata_base),
                error="LLM planner returned an empty TerraformResourcePlan",
            )

        if any(getattr(item, "code", None) == "PLAN_TOO_ABSTRACT" for item in coverage_findings):
            return GenerationResponse(
                generation_status="FAILED",
                generation_mode="FAILED",
                trusted=False,
                requires_human_review=True,
                draft_pattern_name=resource_plan.draft_pattern_name,
                draft_pattern_guess=_guess_draft_pattern(normalized),
                supported_resources=sorted(set(arch_validation.supported_resources)),
                unsupported_resources=sorted(set(arch_validation.unsupported_resources)),
                assumptions=resource_plan.assumptions,
                required_inputs=reasoning.required_inputs,
                missing_inputs=resource_plan.missing_inputs,
                warnings=_merge_unique_lists(resource_plan.warnings, arch_validation.warnings),
                runtime_risks=resource_plan.runtime_risks,
                validation_assertions=resource_plan.validation_assertions,
                terraform_resource_plan=resource_plan.model_dump(mode="json"),
                architecture_resource_mappings=[m.model_dump(mode="json") for m in resource_plan.architecture_resource_mappings],
                external_dependencies=[d.model_dump(mode="json") for d in resource_plan.external_dependencies],
                coverage_findings=_normalize_coverage_findings(coverage_findings),
                reasoning=reasoning.model_dump(),
                metadata=GenerationMetadata(**metadata_base),
                error="LLM planner produced a TerraformResourcePlan that is still too abstract to render safely.",
            )

        try:
            rendered_files = self.generic_renderer.render(resource_plan)
            sanitized_files = [
                FileArtifact(path=validate_artifact_path(f["path"]), content=f["content"])
                for f in rendered_files
            ]
            metadata_base["local_output_dir"] = self.writer.write(
                rendered_files,
                project_id=options.project_id,
                architecture_id=normalized.architecture_id,
                architecture_version_id=options.architecture_version_id,
                architecture_version=normalized.architecture_version,
            )
        except ValueError as exc:
            return GenerationResponse(
                generation_status="FAILED",
                generation_mode="LLM_PLANNED_GENERIC_RENDER",
                trusted=False,
                requires_human_review=True,
                draft_pattern_name=resource_plan.draft_pattern_name,
                draft_pattern_guess=_guess_draft_pattern(normalized),
                supported_resources=sorted(set(arch_validation.supported_resources)),
                unsupported_resources=sorted(set(arch_validation.unsupported_resources)),
                assumptions=resource_plan.assumptions,
                required_inputs=reasoning.required_inputs,
                missing_inputs=resource_plan.missing_inputs,
                warnings=_merge_unique_lists(resource_plan.warnings, ["Rendered file paths failed sanitization."]),
                validation_assertions=resource_plan.validation_assertions,
                terraform_resource_plan=resource_plan.model_dump(mode="json"),
                architecture_resource_mappings=[m.model_dump(mode="json") for m in resource_plan.architecture_resource_mappings],
                external_dependencies=[d.model_dump(mode="json") for d in resource_plan.external_dependencies],
                reasoning=reasoning.model_dump(),
                coverage_findings=_normalize_coverage_findings(coverage_findings),
                metadata=GenerationMetadata(**metadata_base),
                error=str(exc),
            )

        rendered_file_names = [artifact.path for artifact in sanitized_files]
        logger.info(
            "rendered_file_names=%s rendered_file_count=%s rendered_resource_count=%s",
            rendered_file_names,
            len(sanitized_files),
            len(resource_plan.resources),
        )

        if _is_shell_only_render(sanitized_files):
            logger.error(
                "renderer_shell_only_output architecture_id=%s rendered_file_names=%s",
                normalized.architecture_id,
                rendered_file_names,
            )
            return GenerationResponse(
                generation_status="FAILED",
                generation_mode="FAILED",
                trusted=False,
                requires_human_review=True,
                draft_pattern_name=resource_plan.draft_pattern_name,
                draft_pattern_guess=_guess_draft_pattern(normalized),
                supported_resources=sorted(set(arch_validation.supported_resources)),
                unsupported_resources=sorted(set(arch_validation.unsupported_resources)),
                assumptions=resource_plan.assumptions,
                required_inputs=reasoning.required_inputs,
                missing_inputs=resource_plan.missing_inputs,
                warnings=_merge_unique_lists(resource_plan.warnings, arch_validation.warnings),
                runtime_risks=resource_plan.runtime_risks,
                validation_assertions=resource_plan.validation_assertions,
                terraform_resource_plan=resource_plan.model_dump(mode="json"),
                architecture_resource_mappings=[m.model_dump(mode="json") for m in resource_plan.architecture_resource_mappings],
                external_dependencies=[d.model_dump(mode="json") for d in resource_plan.external_dependencies],
                coverage_findings=_normalize_coverage_findings(coverage_findings),
                reasoning=reasoning.model_dump(),
                metadata=GenerationMetadata(**metadata_base),
                error="Generic renderer produced only shell files; no infrastructure resources were rendered.",
            )

        draft_artifacts = sanitized_files

        dummy_plan = TerraformGenerationPlan(
            pattern_id="llm_planned_generic_render",
            generation_mode="LLM_PLANNED_GENERIC_RENDER",
            project_name=options.project_name or self.settings.default_project_name,
            environment=options.environment or self.settings.default_environment,
            aws_region=options.aws_region or self.settings.default_aws_region,
            architecture_id=normalized.architecture_id,
            architecture_version=normalized.architecture_version,
            warnings=resource_plan.warnings,
            runtime_risks=resource_plan.runtime_risks,
            validation_assertions=resource_plan.validation_assertions,
        )
        safety_result = self.safety_checker.check(draft_artifacts, dummy_plan)
        validation_result = self._validate_generated_artifacts(draft_artifacts)

        reviewer_llm = llm if reviewer_enabled else None
        review_result = self.reviewer_agent.review(
            architecture=normalized,
            plan=dummy_plan,
            files=draft_artifacts,
            validation_result=validation_result,
            safety_findings=safety_result,
            llm=reviewer_llm,
        )

        if safety_result.has_critical:
            return GenerationResponse(
                generation_status="FAILED",
                generation_mode="LLM_PLANNED_GENERIC_RENDER",
                trusted=False,
                requires_human_review=True,
                draft_pattern_name=resource_plan.draft_pattern_name,
                draft_pattern_guess=_guess_draft_pattern(normalized),
                supported_resources=sorted(set(arch_validation.supported_resources)),
                unsupported_resources=sorted(set(arch_validation.unsupported_resources)),
                assumptions=resource_plan.assumptions,
                required_inputs=reasoning.required_inputs,
                missing_inputs=resource_plan.missing_inputs,
                warnings=_merge_unique_lists(resource_plan.warnings, arch_validation.warnings),
                runtime_risks=resource_plan.runtime_risks,
                validation_assertions=resource_plan.validation_assertions,
                terraform_resource_plan=resource_plan.model_dump(mode="json"),
                architecture_resource_mappings=[m.model_dump(mode="json") for m in resource_plan.architecture_resource_mappings],
                external_dependencies=[d.model_dump(mode="json") for d in resource_plan.external_dependencies],
                validation=validation_result.model_dump(),
                coverage_findings=_normalize_coverage_findings(coverage_findings),
                safety_findings=[f.model_dump() for f in safety_result.findings],
                reasoning=reasoning.model_dump(),
                review=review_result.model_dump(),
                next_steps=[
                    "LLM-planned generic render produced forbidden or secret-bearing content and was rejected.",
                    "Add a deterministic pattern or correct the planner prompt/provider configuration.",
                ],
                metadata=GenerationMetadata(**metadata_base),
                error="Safety checker rejected the LLM-planned generic render output.",
            )

        metadata_base["generated_file_count"] = len(draft_artifacts)
        return GenerationResponse(
            generation_status="NEEDS_REVIEW",
            generation_mode="LLM_PLANNED_GENERIC_RENDER",
            trusted=False,
            requires_human_review=True,
            draft_pattern_name=resource_plan.draft_pattern_name,
            draft_pattern_guess=_guess_draft_pattern(normalized),
            supported_resources=sorted(set(arch_validation.supported_resources)),
            unsupported_resources=sorted(set(arch_validation.unsupported_resources)),
            files=draft_artifacts,
            assumptions=resource_plan.assumptions,
            required_inputs=reasoning.required_inputs,
            missing_inputs=resource_plan.missing_inputs,
            warnings=_merge_unique_lists(resource_plan.warnings, arch_validation.warnings),
            runtime_risks=resource_plan.runtime_risks,
            validation_assertions=resource_plan.validation_assertions,
            terraform_resource_plan=resource_plan.model_dump(mode="json"),
            architecture_resource_mappings=[m.model_dump(mode="json") for m in resource_plan.architecture_resource_mappings],
            external_dependencies=[d.model_dump(mode="json") for d in resource_plan.external_dependencies],
            validation=validation_result.model_dump(),
            coverage_findings=_normalize_coverage_findings(coverage_findings),
            safety_findings=[f.model_dump() for f in safety_result.findings],
            reasoning=reasoning.model_dump(),
            review=review_result.model_dump(),
            next_steps=[
                "Draft Terraform generated from an LLM-planned resource plan. This architecture is not yet covered by a trusted Nimbus deterministic pattern. Review carefully before use.",
                "Address validation, safety, and reviewer findings before any deploy or apply workflow.",
            ],
            metadata=GenerationMetadata(**metadata_base),
            error=None,
        )

    def _validate_generated_artifacts(
        self,
        artifacts: list[FileArtifact],
    ) -> ValidationResponse:
        return ValidationResponse.model_validate(
            self._validator().validate(artifacts).model_dump()
        )

    def _validator(self):
        from app.services.validator_service import TerraformValidatorService

        return TerraformValidatorService(self.settings)

    def _unsupported(
        self,
        metadata_base: dict,
        warnings: list,
        supported_resources: list,
        unsupported_resources: list,
        error: str,
        next_steps: list | None = None,
        reasoning=None,
        pattern_id: str | None = None,
        deployment_strategy: str | None = None,
    ) -> GenerationResponse:
        return GenerationResponse(
            generation_status="UNSUPPORTED",
            generation_mode="UNSUPPORTED",
            trusted=False,
            requires_human_review=True,
            pattern_id=pattern_id,
            deployment_strategy=deployment_strategy,
            supported_resources=sorted(set(supported_resources)),
            unsupported_resources=unsupported_resources,
            warnings=warnings,
            reasoning=reasoning.model_dump() if reasoning else None,
            next_steps=next_steps or [],
            metadata=GenerationMetadata(**metadata_base),
            error=error,
        )

    def _failed(
        self,
        metadata_base: dict,
        reasoning,
        error: str,
        next_step: str = "Review the error and architecture, then retry.",
    ) -> GenerationResponse:
        return GenerationResponse(
            generation_status="FAILED",
            generation_mode="FAILED",
            trusted=False,
            requires_human_review=True,
            reasoning=reasoning.model_dump() if reasoning else None,
            next_steps=[next_step],
            metadata=GenerationMetadata(**metadata_base),
            error=error,
        )


def _guess_draft_pattern(normalized: NormalizedArchitecture) -> str | None:
    resource_types = {resource.provider_type for resource in normalized.resources}
    if {"aws_apigatewayv2_api", "aws_lambda_function"} & resource_types:
        if "external_supabase" in resource_types:
            return "serverless_http_api_lambda_external_db"
        return "serverless_http_api_lambda"
    if "aws_eks_cluster" in resource_types:
        return "kubernetes_cluster_workload"
    if "external_supabase" in resource_types:
        return "external_database_application_stack"
    return None


def _merge_unique_lists(*lists: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for items in lists:
        for item in items:
            if item not in seen:
                seen.add(item)
                merged.append(item)
    return merged


def _is_shell_only_render(artifacts: list[FileArtifact]) -> bool:
    names = {artifact.path for artifact in artifacts}
    shell_files = {"versions.tf", "providers.tf", "README.generated.md"}
    return bool(names) and names.issubset(shell_files)


def _normalize_coverage_findings(coverage_findings) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for finding in coverage_findings:
        if isinstance(finding, CoverageFinding):
            normalized.append(finding.model_dump())
            continue
        if hasattr(finding, "model_dump"):
            normalized.append(dict(finding.model_dump()))
            continue
        normalized.append(dict(finding))
    return normalized


# ---------------------------------------------------------------------------
# Static site renderer helpers (unchanged from original)
# ---------------------------------------------------------------------------

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
