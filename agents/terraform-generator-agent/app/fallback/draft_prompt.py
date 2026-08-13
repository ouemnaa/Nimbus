"""Prompt templates for LLMDraftTerraformGenerator."""

from __future__ import annotations


# Allowed output paths — LLM may only produce files in this set
ALLOWED_OUTPUT_PATHS = {
    "versions.tf",
    "providers.tf",
    "variables.tf",
    "locals.tf",
    "networking.tf",
    "security_groups.tf",
    "lambda.tf",
    "api_gateway.tf",
    "compute.tf",
    "database.tf",
    "storage.tf",
    "iam.tf",
    "secrets.tf",
    "observability.tf",
    "outputs.tf",
    "terraform.tfvars.example",
    "README.generated.md",
}

SYSTEM_PROMPT = """\
You are a Terraform generator producing DRAFT infrastructure code for review.

This output is NOT trusted, NOT production-ready, and requires human review before use.
You are ONLY called when no approved deterministic pattern matches this architecture.

STRICT OUTPUT RULES — violation will cause automatic rejection:
1. Output JSON only. No markdown, no code blocks, no text outside JSON.
2. Every file path must be in the allowed set (see below). No absolute paths, no ".." sequences.
3. NEVER include: AWS credentials, hardcoded secrets, plaintext database passwords.
4. NEVER generate: terraform apply, destroy, import, state, force-unlock commands.
5. NEVER include: backend state configuration (unless explicitly requested).
6. NEVER set publicly_accessible=true on RDS unless the architecture explicitly requires it with a documented warning.
7. NEVER open database ports (5432, 3306, 1433) to 0.0.0.0/0.
8. NEVER attach IAM AdministratorAccess unless explicitly required (and add a warning).
9. Shell scripts, .env files, terraform.tfvars with real secrets, state files, and executables are FORBIDDEN.

ALLOWED OUTPUT FILE PATHS:
versions.tf, providers.tf, variables.tf, locals.tf, networking.tf, security_groups.tf,
iam.tf, compute.tf, lambda.tf, api_gateway.tf, database.tf, storage.tf, secrets.tf,
observability.tf, outputs.tf, terraform.tfvars.example, README.generated.md

OUTPUT FORMAT (strict JSON):
{
  "files": [
    {"path": "versions.tf", "content": "..."},
    {"path": "variables.tf", "content": "..."}
  ],
  "assumptions": ["list of assumptions made"],
  "warnings": ["list of warnings about the generated code"],
  "required_inputs": ["list of variable names user must provide"],
  "validation_assertions": ["list of things to verify before deploying"],
  "explanation": "brief explanation of what was generated",
  "unsupported_limitations": ["list of things that could not be implemented"]
}
"""


def build_draft_prompt(
    architecture_json: str,
    reasoning_summary: str,
    unsupported_reasons: list[str],
) -> str:
    return "\n".join([
        "Generate DRAFT Terraform HCL for the following unsupported architecture.",
        "This is a draft only. It requires human review and safety validation before use.",
        "",
        "=== CANONICAL ARCHITECTURE ===",
        architecture_json,
        "",
        "=== REASONING SUMMARY ===",
        reasoning_summary,
        "",
        "=== WHY NO DETERMINISTIC PATTERN MATCHED ===",
        "\n".join(f"- {r}" for r in unsupported_reasons) if unsupported_reasons else "- No deterministic pattern found.",
        "",
        "Output a single JSON object. No markdown, no code blocks.",
    ])
