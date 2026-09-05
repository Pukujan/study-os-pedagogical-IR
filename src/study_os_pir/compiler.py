from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .models import StrictFrozenModel


class LearnerEvidenceLevel(StrEnum):
    UNKNOWN = "unknown"
    SEEN = "seen"
    SUPPORTED_SUCCESS = "supported_success"
    UNAIDED_SUCCESS = "unaided_success"
    TRANSFERRED = "transferred"
    RETAINED = "retained"


class PrerequisiteAction(StrEnum):
    REUSE = "reuse"
    PROBE = "probe"
    TEACH = "teach"


class CompilerStrategy(StrEnum):
    WEAK_BASELINE = "weak_baseline"
    PRODUCT_THESIS = "product_thesis"
    EXPLICIT_CONSTRAINTS = "explicit_constraints"
    ONE_TRANSITION = "one_transition"
    PIR_ONLY = "pir_only"


class CompilerViolationCode(StrEnum):
    CASE_ID_MISMATCH = "CASE_ID_MISMATCH"
    POLICY_REF_MISMATCH = "POLICY_REF_MISMATCH"
    UNSUPPORTED_KNOWLEDGE_ASSUMPTION = "UNSUPPORTED_KNOWLEDGE_ASSUMPTION"
    TOO_MANY_NEW_CONCEPTS = "TOO_MANY_NEW_CONCEPTS"
    DUPLICATE_MICROSTEP_ID = "DUPLICATE_MICROSTEP_ID"


class LearnerConceptEvidence(StrictFrozenModel):
    concept_id: str = Field(min_length=1)
    level: LearnerEvidenceLevel
    evidence_refs: tuple[str, ...] = ()


class CompilerInput(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.compiler-input\.v0$")
    case_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    problem_text: str = Field(min_length=1)
    learner_evidence: tuple[LearnerConceptEvidence, ...] = ()
    current_representation: tuple[str, ...] = ()
    public_constraints: tuple[str, ...] = ()
    policy_ref: str = Field(min_length=1)


class CompilerPolicy(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.compiler-policy\.v0$")
    policy_id: str = Field(min_length=1)
    policy_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    strategy: CompilerStrategy
    prompt_template: str = Field(min_length=1)
    max_new_concepts_per_step: int = Field(ge=1)

    @property
    def policy_ref(self) -> str:
        return f"{self.policy_id}@{self.policy_version}"


class PrerequisitePlan(StrictFrozenModel):
    concept_id: str = Field(min_length=1)
    action: PrerequisiteAction
    rationale: str = Field(min_length=1)


class CompilerDependency(StrictFrozenModel):
    prerequisite: str = Field(min_length=1)
    dependent: str = Field(min_length=1)


class CompilerMicrostep(StrictFrozenModel):
    step_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    introduces: tuple[str, ...] = ()
    preserves: tuple[str, ...] = ()
    representation_requirements: tuple[str, ...] = ()
    assessment_target: str | None = Field(default=None, min_length=1)


class CompilerProposal(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.compiler-proposal\.v0$")
    case_id: str = Field(min_length=1)
    policy_ref: str = Field(min_length=1)
    problem_objects: tuple[str, ...] = Field(min_length=1)
    roles: tuple[str, ...] = ()
    prerequisite_plan: tuple[PrerequisitePlan, ...] = ()
    state_variables: tuple[str, ...] = ()
    dependencies: tuple[CompilerDependency, ...] = ()
    microsteps: tuple[CompilerMicrostep, ...] = Field(min_length=1)
    invariants: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    misconception_candidates: tuple[str, ...] = ()
    generalization_path: tuple[str, ...] = ()


class CompilerViolation(StrictFrozenModel):
    code: CompilerViolationCode
    detail: str = Field(min_length=1)


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def validate_compiler_proposal(
    compiler_input: CompilerInput,
    policy: CompilerPolicy,
    proposal: CompilerProposal,
) -> tuple[CompilerViolation, ...]:
    violations: list[CompilerViolation] = []

    if proposal.case_id != compiler_input.case_id:
        violations.append(
            CompilerViolation(
                code=CompilerViolationCode.CASE_ID_MISMATCH,
                detail=(
                    f"proposal case {proposal.case_id!r} does not match "
                    f"input case {compiler_input.case_id!r}"
                ),
            )
        )

    if compiler_input.policy_ref != policy.policy_ref or proposal.policy_ref != policy.policy_ref:
        violations.append(
            CompilerViolation(
                code=CompilerViolationCode.POLICY_REF_MISMATCH,
                detail=(
                    f"input/proposal policy refs must both equal {policy.policy_ref!r}"
                ),
            )
        )

    evidence_by_concept = {
        evidence.concept_id: evidence.level for evidence in compiler_input.learner_evidence
    }
    for prerequisite in proposal.prerequisite_plan:
        if (
            evidence_by_concept.get(prerequisite.concept_id, LearnerEvidenceLevel.UNKNOWN)
            == LearnerEvidenceLevel.UNKNOWN
            and prerequisite.action == PrerequisiteAction.REUSE
        ):
            violations.append(
                CompilerViolation(
                    code=CompilerViolationCode.UNSUPPORTED_KNOWLEDGE_ASSUMPTION,
                    detail=(
                        f"{prerequisite.concept_id!r} is unknown but proposal marks it reusable"
                    ),
                )
            )

    for step in proposal.microsteps:
        if len(step.introduces) > policy.max_new_concepts_per_step:
            violations.append(
                CompilerViolation(
                    code=CompilerViolationCode.TOO_MANY_NEW_CONCEPTS,
                    detail=(
                        f"{step.step_id} introduces {len(step.introduces)} concepts; "
                        f"policy limit is {policy.max_new_concepts_per_step}"
                    ),
                )
            )

    for duplicate in _duplicates(tuple(step.step_id for step in proposal.microsteps)):
        violations.append(
            CompilerViolation(
                code=CompilerViolationCode.DUPLICATE_MICROSTEP_ID,
                detail=f"duplicate compiler microstep id: {duplicate}",
            )
        )

    return tuple(violations)
