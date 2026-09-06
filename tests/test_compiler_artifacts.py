from __future__ import annotations

from study_os_pir.canonical import canonical_json_bytes
from study_os_pir.compiler import (
    CanonicalPrerequisite,
    CanonicalProblemPIR,
    CompilerMicrostep,
    CompilerPolicy,
    CompilerStrategy,
    ProblemCompilerInput,
)
from study_os_pir.compiler_artifacts import (
    build_decomposition_projection,
    parse_compiler_candidate,
    render_compiler_prompt,
)
from study_os_pir.compiler_runs import CandidateParseStatus


def compiler_input() -> ProblemCompilerInput:
    return ProblemCompilerInput(
        schema_version="pir.problem-compiler-input.v0",
        case_id="dev.test.v0",
        domain="dsa",
        problem_text="Find a target in a sorted array.",
        public_constraints=("canonical decomposition is learner-independent",),
        policy_ref="compiler-p4@0.1.0",
    )


def policy() -> CompilerPolicy:
    return CompilerPolicy(
        schema_version="pir.compiler-policy.v0",
        policy_id="compiler-p4",
        policy_version="0.1.0",
        strategy=CompilerStrategy.PIR_ONLY,
        prompt_template="Emit the canonical problem graph only.",
        max_new_concepts_per_step=1,
    )


def proposal() -> CanonicalProblemPIR:
    return CanonicalProblemPIR(
        schema_version="pir.canonical-problem-pir.v0",
        case_id="dev.test.v0",
        policy_ref="compiler-p4@0.1.0",
        problem_objects=("array", "target"),
        prerequisites=(
            CanonicalPrerequisite(
                concept_id="index",
                rationale="array positions must be addressable",
            ),
        ),
        microsteps=(
            CompilerMicrostep(
                step_id="ground_index",
                operation="connect a position to an index",
                introduces=("index",),
                representation_requirements=("array_with_index_row",),
            ),
            CompilerMicrostep(
                step_id="ground_search_region",
                operation="show the active region",
                introduces=("search_region",),
                representation_requirements=("highlighted_search_region",),
            ),
        ),
        invariants=("the target remains in the active region if present",),
    )


def test_render_compiler_prompt_preserves_transport_identity() -> None:
    prompt = render_compiler_prompt(compiler_input(), policy())

    assert "dev.test.v0" in prompt
    assert "compiler-p4@0.1.0" in prompt
    assert "learner-independent" in prompt
    assert "Find a target in a sorted array." in prompt
    assert "Emit the canonical problem graph only." in prompt


def test_parse_compiler_candidate_accepts_exact_valid_json() -> None:
    status, parsed = parse_compiler_candidate(canonical_json_bytes(proposal()))

    assert status == CandidateParseStatus.PARSED
    assert parsed == proposal()


def test_parse_compiler_candidate_rejects_invalid_json() -> None:
    status, parsed = parse_compiler_candidate(b"{not-json")

    assert status == CandidateParseStatus.INVALID_JSON
    assert parsed is None


def test_parse_compiler_candidate_rejects_invalid_utf8() -> None:
    status, parsed = parse_compiler_candidate(b"\xff")

    assert status == CandidateParseStatus.INVALID_JSON
    assert parsed is None


def test_parse_compiler_candidate_rejects_schema_invalid_json() -> None:
    status, parsed = parse_compiler_candidate(b'{"schema_version":"wrong"}')

    assert status == CandidateParseStatus.INVALID_SCHEMA
    assert parsed is None


def test_projection_is_narrow_stable_and_deduplicated() -> None:
    projection = build_decomposition_projection(
        proposal(),
        candidate_id="luna",
        candidate_version="local",
    )

    assert projection == {
        "schema_version": "benchmark.decomposition-projection.v1",
        "case_id": "dev.test.v0",
        "candidate_id": "luna",
        "candidate_version": "local",
        "concepts": ("index", "search_region"),
        "steps": [
            {
                "step_id": "ground_index",
                "introduces": ("index",),
                "representation_requirements": ("array_with_index_row",),
            },
            {
                "step_id": "ground_search_region",
                "introduces": ("search_region",),
                "representation_requirements": ("highlighted_search_region",),
            },
        ],
        "invariants": ("the target remains in the active region if present",),
    }
