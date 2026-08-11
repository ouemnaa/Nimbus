"""
TerraformSafetyPolicyChecker

Scans generated HCL files for dangerous patterns using the policies defined
in safety/policies.py. Runs after rendering, before returning the final result.
"""

from __future__ import annotations

import logging
from typing import Any

from app.schemas.architecture import FileArtifact
from app.schemas.plan import TerraformGenerationPlan

from .findings import SafetyCheckResult, SafetyFinding
from .policies import ALL_POLICIES

logger = logging.getLogger(__name__)

# Files that should NOT be scanned (docs, tfvars examples, etc.)
_SKIP_EXTENSIONS = {".md", ".example", ".txt"}


class TerraformSafetyPolicyChecker:
    """
    Scans HCL text and plan context for dangerous infrastructure patterns.

    Findings are returned as SafetyCheckResult. The caller decides how to
    handle CRITICAL findings (downgrade trusted, set requires_human_review).
    """

    def check(
        self,
        files: list[FileArtifact],
        plan: TerraformGenerationPlan,
    ) -> SafetyCheckResult:
        ctx = self._build_context(plan)
        findings: list[SafetyFinding] = []

        for artifact in files:
            filename = artifact.path
            # Skip non-HCL files for most policies, but always scan README for forbidden commands
            suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
            if suffix in _SKIP_EXTENSIONS and filename != "README.generated.md":
                continue

            content = artifact.content
            for policy_fn in ALL_POLICIES:
                try:
                    for finding in policy_fn(content, filename, ctx):
                        findings.append(finding)
                except Exception as exc:
                    logger.warning("Safety policy %s raised error on %s: %s", policy_fn.__name__, filename, exc)

        has_critical = any(f.severity == "CRITICAL" for f in findings)
        passed = not has_critical and not any(f.severity == "HIGH" for f in findings)

        return SafetyCheckResult(
            passed=passed,
            has_critical=has_critical,
            findings=findings,
        )

    @staticmethod
    def _build_context(plan: TerraformGenerationPlan) -> dict[str, Any]:
        """Build a context dict from plan metadata for policy functions."""
        return {
            "environment": plan.environment,
            "deployment_strategy": plan.deployment_strategy,
            "pattern_id": plan.pattern_id,
            "rds_publicly_accessible": plan.resources.get("rds_publicly_accessible", False),
            "s3_public_access_required": plan.resources.get("s3_public_access_required", False),
            "safety_expectations": plan.safety_expectations,
        }
