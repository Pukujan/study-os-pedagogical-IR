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


class CompilerStrategy(StrEnum):
    WEAK_BASELINE = "weak_baseline"
    PRODUCT_THESIS = "product_thesis"
    EXPLICIT_CONSTRAINTS = "explicit_constraints"
    ONE_TRANSITION = "one_transition"
    PIR_ONLY = "pir_only"


class TraversalAction(StrEnum):
    FOLLOW_CANONICAL = "follow_canonical"
    SKIP_EVIDENCED = "skip_evidenced"
    EXPAND = "expand"
    REPAIR = "repair"


class CompilerViolationCode(StrEnum):
    CASE_ID_MISMATCH = "CASE_ID_MISMATCH"
    POLICY_REF_MISMATCH = "POLICY_REF_MISMATCH"
    TOO_MANY_NEW_CONCEPTS = "TOO_MANY_NEW_CONCEPTS"
    DUPLICATE_MICROSTEP_ID = "DUPLICATE_MICROSTEP_ID"
    DUPLICATE_PREREQUISITE = "DUPLICATE_PREREQUISITE"


class TraversalViolationCode(StrEnum):
    CASE_ID_MISMATCH = "CASE_ID_MISMATCH"
    DUPLICATE_SELECTED_STEP = "DUPLICATE_SELECTED_STEP"
    UNKNOWN_SELECTED_STEP = "UNKNOWN_SELECTED_STEP"
    UNKNOWN_SKIPPED_CONCEPT = "UNKNOWN_SKIPPED_CONCEPT"
    UNSUPPORTED_SKIP_EVIDENCE = "UNSUPPORTED_SKIP_EVIDENCE"


class LearnerConceptEvidence(StrictFrozenModel):
    concept_id: str = Field(min_length=1)
    level: LearnerEvidenceLevel
    evidence_refs: tuple[str, ...] = ()


class ProblemCompilerInput(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.problem-compiler-input\.v0$")
    case_id: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    problem_text: str = Field(min_length=1)
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


class CanonicalPrerequisite(StrictFrozenModel):
    concept_id: str = Field(min_length=1)
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
    exercise_requirements: tuple[str, ...] = ()
    optional_expansions: tuple[str, ...] = ()


class CanonicalProblemPIR(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.canonical-problem-pir\.v0$")
    case_id: str = Field(min_length=1)
    policy_ref: str = Field(min_length=1)
    problem_objects: tuple[str, ...] = Field(min_length=1)
    roles: tuple[str, ...] = ()
    prerequisites: tuple[CanonicalPrerequisite, ...] = ()
    state_variables: tuple[str, ...] = ()
    dependencies: tuple[CompilerDependency, ...] = ()
    microsteps: tuple[CompilerMicrostep, ...] = Field(min_length=1)
    invariants: tuple[str, ...] = ()
    conditions: tuple[str, ...] = ()
    misconception_candidates: tuple[str, ...] = ()
    generalization_path: tuple[str, ...] = ()


class TraversalInput(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.traversal-input\.v0$")
    canonical_pir: CanonicalProblemPIR
    learner_evidence: tuple[LearnerConceptEvidence, ...] = ()
    learner_request: str | None = Field(default=None, min_length=1)
    current_step_id: str | None = Field(default=None, min_length=1)


class TraversalDecision(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.traversal-decision\.v0$")
    case_id: str = Field(min_length=1)
    action: TraversalAction
    selected_step_ids: tuple[str, ...] = Field(min_length=1)
    skipped_concepts: tuple[str, ...] = ()
    requested_expansion: str | None = Field(default=None, min_length=1)
    rationale: str = Field(min_length=1)


class CompilerViolation(StrictFrozenModel):
    code: CompilerViolationCode
    detail: str = Field(min_length=1)


class TraversalViolation(StrictFrozenModel):
    code: TraversalViolationCode
    detail: str = Field(min_length=1)


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def validate_canonical_problem_pir(
    compiler_input: ProblemCompilerInput,
    policy: CompilerPolicy,
    proposal: CanonicalProblemPIR,
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
                detail=f"input/proposal policy refs must both equal {policy.policy_ref!r}",
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

    for duplicate in _duplicates(
        tuple(prerequisite.concept_id for prerequisite in proposal.prerequisites)
    ):
        violations.append(
            CompilerViolation(
                code=CompilerViolationCode.DUPLICATE_PREREQUISITE,
                detail=f"duplicate canonical prerequisite: {duplicate}",
            )
        )

    return tuple(violations)


def validate_traversal_decision(
    traversal_input: TraversalInput,
    decision: TraversalDecision,
) -> tuple[TraversalViolation, ...]:
    violations: list[TraversalViolation] = []
    canonical = traversal_input.canonical_pir

    if decision.case_id != canonical.case_id:
        violations.append(
            TraversalViolation(
                code=TraversalViolationCode.CASE_ID_MISMATCH,
                detail=(
                    f"decision case {decision.case_id!r} does not match "
                    f"canonical case {canonical.case_id!r}"
                ),
            )
        )

    canonical_step_ids = {step.step_id for step in canonical.microsteps}
    for duplicate in _duplicates(decision.selected_step_ids):
        violations.append(
            TraversalViolation(
                code=TraversalViolationCode.DUPLICATE_SELECTED_STEP,
                detail=f"duplicate selected traversal step: {duplicate}",
            )
        )
    for step_id in decision.selected_step_ids:
        if step_id not in canonical_step_ids:
            violations.append(
                TraversalViolation(
                    code=TraversalViolationCode.UNKNOWN_SELECTED_STEP,
                    detail=f"traversal selects unknown canonical step: {step_id}",
                )
            )

    canonical_concepts = {
        prerequisite.concept_id for prerequisite in canonical.prerequisites
    }
    for step in canonical.microsteps:
        canonical_concepts.update(step.introduces)

    evidence_by_concept = {
        evidence.concept_id: evidence.level for evidence in traversal_input.learner_evidence
    }
    skip_supported_levels = {
        LearnerEvidenceLevel.UNAIDED_SUCCESS,
        LearnerEvidenceLevel.TRANSFERRED,
        LearnerEvidenceLevel.RETAINED,
    }
    for concept_id in decision.skipped_concepts:
        if concept_id not in canonical_concepts:
            violations.append(
                TraversalViolation(
                    code=TraversalViolationCode.UNKNOWN_SKIPPED_CONCEPT,
                    detail=f"traversal skips unknown canonical concept: {concept_id}",
                )
            )
            continue
        level = evidence_by_concept.get(concept_id, LearnerEvidenceLevel.UNKNOWN)
        if level not in skip_supported_levels:
            violations.append(
                TraversalViolation(
                    code=TraversalViolationCode.UNSUPPORTED_SKIP_EVIDENCE,
                    detail=(
                        f"{concept_id!r} has evidence level {level.value!r}; "
                        "skipping requires unaided, transferred, or retained evidence"
                    ),
                )
            )

    return tuple(violations)
