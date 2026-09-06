from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from .compiler import CanonicalProblemPIR, CompilerPolicy, ProblemCompilerInput
from .compiler_runs import CandidateParseStatus


def render_compiler_prompt(
    compiler_input: ProblemCompilerInput,
    policy: CompilerPolicy,
) -> str:
    """Render the bounded prompt sent to a model-backed canonical compiler."""

    return "\n\n".join(
        (
            "You are a constrained Study OS canonical problem compiler.",
            (
                "Transport contract:\n"
                "- Compile only the supplied problem into CanonicalProblemPIR.\n"
                "- Canonical decomposition is learner-independent; learner state is not input.\n"
                f"- Preserve case_id exactly as {compiler_input.case_id!r}.\n"
                f"- Preserve policy_ref exactly as {policy.policy_ref!r}.\n"
                "- Return only the final JSON object required by the output schema."
            ),
            f"Compiler policy ({policy.policy_ref}):\n{policy.prompt_template}",
            "ProblemCompilerInput JSON:\n" + compiler_input.model_dump_json(indent=2),
        )
    )


def parse_compiler_candidate(
    candidate_bytes: bytes,
) -> tuple[CandidateParseStatus, CanonicalProblemPIR | None]:
    """Parse exact candidate bytes without repairing or normalizing model output."""

    try:
        json.loads(candidate_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return CandidateParseStatus.INVALID_JSON, None

    try:
        proposal = CanonicalProblemPIR.model_validate_json(candidate_bytes)
    except ValidationError:
        return CandidateParseStatus.INVALID_SCHEMA, None

    return CandidateParseStatus.PARSED, proposal


def build_decomposition_projection(
    proposal: CanonicalProblemPIR,
    *,
    candidate_id: str,
    candidate_version: str,
) -> dict[str, Any]:
    """Project PIR into the benchmarker's intentionally narrow graph contract."""

    concepts = tuple(
        dict.fromkeys(
            [prerequisite.concept_id for prerequisite in proposal.prerequisites]
            + [concept for step in proposal.microsteps for concept in step.introduces]
        )
    )
    return {
        "schema_version": "benchmark.decomposition-projection.v1",
        "case_id": proposal.case_id,
        "candidate_id": candidate_id,
        "candidate_version": candidate_version,
        "concepts": concepts,
        "steps": [
            {
                "step_id": step.step_id,
                "introduces": step.introduces,
                "representation_requirements": step.representation_requirements,
            }
            for step in proposal.microsteps
        ],
        "invariants": proposal.invariants,
    }
