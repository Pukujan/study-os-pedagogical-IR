from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .canonical import canonical_sha256, sha256_hex
from .compiler import (
    CanonicalProblemPIR,
    CompilerPolicy,
    CompilerViolationCode,
    ProblemCompilerInput,
    validate_canonical_problem_pir,
)
from .models import StrictFrozenModel


class CandidateParseStatus(StrEnum):
    PARSED = "parsed"
    INVALID_JSON = "invalid_json"
    INVALID_SCHEMA = "invalid_schema"
    EXECUTION_FAILED = "execution_failed"


class GenerationSetting(StrictFrozenModel):
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)


class CompilerRunReceipt(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.compiler-run-receipt\.v0$")
    run_id: str = Field(min_length=1)
    attempt_index: int = Field(ge=0)
    case_id: str = Field(min_length=1)
    policy_ref: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    pir_revision: str = Field(min_length=1)
    benchmarker_revision: str = Field(min_length=1)
    input_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_byte_length: int = Field(ge=0)
    parse_status: CandidateParseStatus
    compiler_violation_codes: tuple[CompilerViolationCode, ...] = ()
    accepted: bool
    generation_settings: tuple[GenerationSetting, ...] = ()


def build_compiler_run_receipt(
    *,
    run_id: str,
    attempt_index: int,
    compiler_input: ProblemCompilerInput,
    policy: CompilerPolicy,
    candidate_bytes: bytes,
    parse_status: CandidateParseStatus,
    proposal: CanonicalProblemPIR | None,
    model_id: str,
    model_revision: str,
    pir_revision: str,
    benchmarker_revision: str,
    generation_settings: tuple[GenerationSetting, ...] = (),
) -> CompilerRunReceipt:
    if parse_status == CandidateParseStatus.PARSED and proposal is None:
        raise ValueError("parsed candidate requires a canonical problem PIR proposal")
    if parse_status != CandidateParseStatus.PARSED and proposal is not None:
        raise ValueError("unparsed candidate cannot include a canonical problem PIR proposal")

    violation_codes: tuple[CompilerViolationCode, ...] = ()
    if proposal is not None:
        violation_codes = tuple(
            violation.code
            for violation in validate_canonical_problem_pir(compiler_input, policy, proposal)
        )

    return CompilerRunReceipt(
        schema_version="pir.compiler-run-receipt.v0",
        run_id=run_id,
        attempt_index=attempt_index,
        case_id=compiler_input.case_id,
        policy_ref=policy.policy_ref,
        model_id=model_id,
        model_revision=model_revision,
        pir_revision=pir_revision,
        benchmarker_revision=benchmarker_revision,
        input_sha256=canonical_sha256(compiler_input),
        policy_sha256=canonical_sha256(policy),
        candidate_sha256=sha256_hex(candidate_bytes),
        candidate_byte_length=len(candidate_bytes),
        parse_status=parse_status,
        compiler_violation_codes=violation_codes,
        accepted=parse_status == CandidateParseStatus.PARSED and not violation_codes,
        generation_settings=generation_settings,
    )
