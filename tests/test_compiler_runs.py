from __future__ import annotations

from pathlib import Path

import pytest

from study_os_pir.canonical import canonical_json_bytes, sha256_hex
from study_os_pir.compiler import (
    CanonicalPrerequisite,
    CanonicalProblemPIR,
    CompilerMicrostep,
    CompilerPolicy,
    CompilerViolationCode,
    ProblemCompilerInput,
)
from study_os_pir.compiler_runs import (
    CandidateParseStatus,
    GenerationSetting,
    build_compiler_run_receipt,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "fixtures" / "public" / "compiler-policies" / "compiler-p4.0.1.0.json"
INPUT_PATH = (
    ROOT / "fixtures" / "public" / "compiler-development" / "binary-search.input.v0.json"
)


def load_input() -> ProblemCompilerInput:
    return ProblemCompilerInput.model_validate_json(INPUT_PATH.read_text())


def load_policy() -> CompilerPolicy:
    return CompilerPolicy.model_validate_json(POLICY_PATH.read_text())


def proposal() -> CanonicalProblemPIR:
    compiler_input = load_input()
    return CanonicalProblemPIR(
        schema_version="pir.canonical-problem-pir.v0",
        case_id=compiler_input.case_id,
        policy_ref=compiler_input.policy_ref,
        problem_objects=("array", "target"),
        prerequisites=(
            CanonicalPrerequisite(
                concept_id="index",
                rationale="binary search must refer to positions in the array",
            ),
        ),
        microsteps=(
            CompilerMicrostep(
                step_id="ground_index",
                operation="connect array position to index",
                introduces=("index",),
                representation_requirements=("array_with_index_row",),
                assessment_target="identify an index",
                exercise_requirements=("changed index",),
            ),
        ),
    )


def build(
    *,
    candidate_bytes: bytes,
    parse_status: CandidateParseStatus,
    candidate_proposal: CanonicalProblemPIR | None,
):
    return build_compiler_run_receipt(
        run_id="run-001",
        attempt_index=0,
        compiler_input=load_input(),
        policy=load_policy(),
        candidate_bytes=candidate_bytes,
        parse_status=parse_status,
        proposal=candidate_proposal,
        model_id="test-model",
        model_revision="test-model-rev",
        pir_revision="pir-rev",
        benchmarker_revision="bench-rev",
        generation_settings=(GenerationSetting(name="temperature", value="0"),),
    )


def test_accepted_parsed_run_records_exact_identities() -> None:
    candidate = proposal()
    candidate_bytes = canonical_json_bytes(candidate)
    receipt = build(
        candidate_bytes=candidate_bytes,
        parse_status=CandidateParseStatus.PARSED,
        candidate_proposal=candidate,
    )

    assert receipt.accepted is True
    assert receipt.compiler_violation_codes == ()
    assert receipt.candidate_sha256 == sha256_hex(candidate_bytes)
    assert receipt.candidate_byte_length == len(candidate_bytes)
    assert receipt.case_id == load_input().case_id
    assert receipt.policy_ref == load_policy().policy_ref
    assert receipt.generation_settings == (
        GenerationSetting(name="temperature", value="0"),
    )


def test_parsed_but_invalid_proposal_records_deterministic_violation() -> None:
    candidate = proposal().model_copy(update={"case_id": "wrong-case"})
    candidate_bytes = canonical_json_bytes(candidate)
    receipt = build(
        candidate_bytes=candidate_bytes,
        parse_status=CandidateParseStatus.PARSED,
        candidate_proposal=candidate,
    )

    assert receipt.accepted is False
    assert receipt.compiler_violation_codes == (CompilerViolationCode.CASE_ID_MISMATCH,)


def test_invalid_json_run_is_retained_without_fake_proposal() -> None:
    candidate_bytes = b"{not-json"
    receipt = build(
        candidate_bytes=candidate_bytes,
        parse_status=CandidateParseStatus.INVALID_JSON,
        candidate_proposal=None,
    )

    assert receipt.accepted is False
    assert receipt.parse_status == CandidateParseStatus.INVALID_JSON
    assert receipt.compiler_violation_codes == ()
    assert receipt.candidate_sha256 == sha256_hex(candidate_bytes)


def test_invalid_schema_run_is_retained_without_fake_proposal() -> None:
    candidate_bytes = b'{"schema_version":"wrong"}'
    receipt = build(
        candidate_bytes=candidate_bytes,
        parse_status=CandidateParseStatus.INVALID_SCHEMA,
        candidate_proposal=None,
    )

    assert receipt.accepted is False
    assert receipt.parse_status == CandidateParseStatus.INVALID_SCHEMA


def test_parsed_status_requires_proposal() -> None:
    with pytest.raises(ValueError, match="parsed candidate requires"):
        build(
            candidate_bytes=b"{}",
            parse_status=CandidateParseStatus.PARSED,
            candidate_proposal=None,
        )


def test_unparsed_status_rejects_proposal() -> None:
    with pytest.raises(ValueError, match="unparsed candidate cannot include"):
        build(
            candidate_bytes=canonical_json_bytes(proposal()),
            parse_status=CandidateParseStatus.INVALID_SCHEMA,
            candidate_proposal=proposal(),
        )


def test_candidate_hash_is_exact_byte_identity() -> None:
    candidate = proposal()
    compact = canonical_json_bytes(candidate)
    padded = compact + b"\n"

    compact_receipt = build(
        candidate_bytes=compact,
        parse_status=CandidateParseStatus.PARSED,
        candidate_proposal=candidate,
    )
    padded_receipt = build(
        candidate_bytes=padded,
        parse_status=CandidateParseStatus.PARSED,
        candidate_proposal=candidate,
    )

    assert compact_receipt.candidate_sha256 != padded_receipt.candidate_sha256
