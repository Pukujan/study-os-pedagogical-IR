from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from study_os_pir.compiler import (
    CanonicalPrerequisite,
    CanonicalProblemPIR,
    CompilerDependency,
    CompilerMicrostep,
    CompilerPolicy,
    CompilerViolationCode,
    LearnerConceptEvidence,
    LearnerEvidenceLevel,
    ProblemCompilerInput,
    TraversalAction,
    TraversalDecision,
    TraversalInput,
    TraversalViolationCode,
    validate_canonical_problem_pir,
    validate_traversal_decision,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "fixtures" / "public" / "compiler-policies"
DEVELOPMENT_DIR = ROOT / "fixtures" / "public" / "compiler-development"


def load_policy(name: str = "compiler-p4.0.1.0.json") -> CompilerPolicy:
    return CompilerPolicy.model_validate_json((POLICY_DIR / name).read_text())


def load_input(name: str = "binary-search.input.v0.json") -> ProblemCompilerInput:
    return ProblemCompilerInput.model_validate_json((DEVELOPMENT_DIR / name).read_text())


def valid_proposal() -> CanonicalProblemPIR:
    compiler_input = load_input()
    return CanonicalProblemPIR(
        schema_version="pir.canonical-problem-pir.v0",
        case_id=compiler_input.case_id,
        policy_ref=compiler_input.policy_ref,
        problem_objects=("array", "target"),
        roles=("current_search_region",),
        prerequisites=(
            CanonicalPrerequisite(
                concept_id="index",
                rationale="the learner must be able to refer to array positions",
            ),
            CanonicalPrerequisite(
                concept_id="array_value_lookup",
                rationale="the learner must connect an index to the value stored there",
            ),
            CanonicalPrerequisite(
                concept_id="search_interval",
                rationale="binary search operates on a changing active region",
            ),
        ),
        state_variables=("left", "right"),
        dependencies=(
            CompilerDependency(
                prerequisite="search_interval",
                dependent="midpoint",
            ),
        ),
        microsteps=(
            CompilerMicrostep(
                step_id="ground_index",
                operation="connect a human position to an array index",
                introduces=("index",),
                preserves=("array",),
                representation_requirements=("array_with_index_row",),
                assessment_target="identify an index",
                exercise_requirements=("changed-index lookup",),
            ),
            CompilerMicrostep(
                step_id="ground_value_lookup",
                operation="retrieve the value stored at a shown index",
                introduces=("array_value_lookup",),
                preserves=("array", "index_row"),
                representation_requirements=("array_with_index_row",),
                assessment_target="retrieve the value at an index",
                exercise_requirements=("changed-value lookup",),
            ),
            CompilerMicrostep(
                step_id="introduce_search_region",
                operation="highlight the region that can still contain the target",
                introduces=("search_interval",),
                preserves=("array", "indexes"),
                representation_requirements=("highlighted_search_region",),
                assessment_target="identify the active region",
                exercise_requirements=("changed search region",),
                optional_expansions=("extra concrete region example",),
            ),
            CompilerMicrostep(
                step_id="introduce_midpoint",
                operation="choose the middle index of the current search region",
                introduces=("midpoint",),
                preserves=("array", "indexes", "search_interval"),
                representation_requirements=("middle_index_marker",),
                assessment_target="identify the middle index",
                exercise_requirements=("changed bounds midpoint",),
            ),
        ),
        invariants=("if the target exists, it remains in the current search region",),
        conditions=("compare target with the value at the middle index",),
        misconception_candidates=("index_position_confusion",),
        generalization_path=("concrete region", "bounds", "midpoint expression", "loop"),
    )


def compiler_codes(
    compiler_input: ProblemCompilerInput,
    policy: CompilerPolicy,
    proposal: CanonicalProblemPIR,
) -> tuple[CompilerViolationCode, ...]:
    return tuple(
        violation.code
        for violation in validate_canonical_problem_pir(compiler_input, policy, proposal)
    )


def traversal_input() -> TraversalInput:
    return TraversalInput(
        schema_version="pir.traversal-input.v0",
        canonical_pir=valid_proposal(),
        learner_evidence=(
            LearnerConceptEvidence(
                concept_id="index",
                level=LearnerEvidenceLevel.UNAIDED_SUCCESS,
                evidence_refs=("attempt.index.1",),
            ),
            LearnerConceptEvidence(
                concept_id="array_value_lookup",
                level=LearnerEvidenceLevel.TRANSFERRED,
                evidence_refs=("attempt.lookup.transfer.1",),
            ),
            LearnerConceptEvidence(
                concept_id="search_interval",
                level=LearnerEvidenceLevel.UNKNOWN,
            ),
        ),
    )


def traversal_decision() -> TraversalDecision:
    return TraversalDecision(
        schema_version="pir.traversal-decision.v0",
        case_id=valid_proposal().case_id,
        action=TraversalAction.SKIP_EVIDENCED,
        selected_step_ids=("introduce_search_region", "introduce_midpoint"),
        skipped_concepts=("index", "array_value_lookup"),
        rationale="skip only concepts with strong evidence and enter at the first uncertain concept",
    )


def traversal_codes(
    input_value: TraversalInput,
    decision: TraversalDecision,
) -> tuple[TraversalViolationCode, ...]:
    return tuple(
        violation.code for violation in validate_traversal_decision(input_value, decision)
    )


def test_all_prompt_policy_versions_and_development_inputs_validate() -> None:
    policies = tuple(
        CompilerPolicy.model_validate_json(path.read_text())
        for path in sorted(POLICY_DIR.glob("*.json"))
    )
    assert tuple(policy.policy_ref for policy in policies) == (
        "compiler-p0@0.1.0",
        "compiler-p1@0.1.0",
        "compiler-p2@0.1.0",
        "compiler-p3@0.1.0",
        "compiler-p4@0.1.0",
    )

    inputs = tuple(
        ProblemCompilerInput.model_validate_json(path.read_text())
        for path in sorted(DEVELOPMENT_DIR.glob("*.json"))
    )
    assert {compiler_input.case_id for compiler_input in inputs} == {
        "dev.dsa.bfs-shortest-path.v0",
        "dev.dsa.binary-search.v0",
        "dev.dsa.two-pointers.v0",
    }
    assert all(compiler_input.policy_ref == "compiler-p4@0.1.0" for compiler_input in inputs)


def test_problem_compiler_input_rejects_learner_state() -> None:
    raw = json.loads((DEVELOPMENT_DIR / "binary-search.input.v0.json").read_text())
    raw["learner_evidence"] = [
        {"concept_id": "index", "level": "retained", "evidence_refs": []}
    ]
    with pytest.raises(ValidationError):
        ProblemCompilerInput.model_validate(raw)


def test_valid_canonical_problem_pir_passes_without_learner_state() -> None:
    assert validate_canonical_problem_pir(load_input(), load_policy(), valid_proposal()) == ()


def test_case_identity_mismatch_is_rejected() -> None:
    proposal = valid_proposal().model_copy(update={"case_id": "wrong-case"})
    assert compiler_codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.CASE_ID_MISMATCH,
    )


def test_input_policy_mismatch_is_rejected() -> None:
    compiler_input = load_input().model_copy(update={"policy_ref": "compiler-p3@0.1.0"})
    assert compiler_codes(compiler_input, load_policy(), valid_proposal()) == (
        CompilerViolationCode.POLICY_REF_MISMATCH,
    )


def test_proposal_policy_mismatch_is_rejected() -> None:
    proposal = valid_proposal().model_copy(update={"policy_ref": "compiler-p3@0.1.0"})
    assert compiler_codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.POLICY_REF_MISMATCH,
    )


def test_policy_concept_budget_rejects_multi_concept_jump() -> None:
    step = valid_proposal().microsteps[0].model_copy(
        update={"introduces": ("index", "position")}
    )
    proposal = valid_proposal().model_copy(update={"microsteps": (step,)})
    assert compiler_codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.TOO_MANY_NEW_CONCEPTS,
    )


def test_duplicate_microstep_ids_are_rejected() -> None:
    first = valid_proposal().microsteps[0]
    second = valid_proposal().microsteps[1].model_copy(update={"step_id": first.step_id})
    proposal = valid_proposal().model_copy(update={"microsteps": (first, second)})
    assert compiler_codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.DUPLICATE_MICROSTEP_ID,
    )


def test_duplicate_prerequisites_are_rejected() -> None:
    prerequisite = valid_proposal().prerequisites[0]
    proposal = valid_proposal().model_copy(
        update={"prerequisites": (prerequisite, prerequisite)}
    )
    assert compiler_codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.DUPLICATE_PREREQUISITE,
    )


def test_traversal_can_skip_only_strongly_evidenced_concepts() -> None:
    assert validate_traversal_decision(traversal_input(), traversal_decision()) == ()


def test_unknown_concept_cannot_be_skipped() -> None:
    decision = traversal_decision().model_copy(
        update={"skipped_concepts": ("search_interval",)}
    )
    assert traversal_codes(traversal_input(), decision) == (
        TraversalViolationCode.UNSUPPORTED_SKIP_EVIDENCE,
    )


def test_supported_success_is_not_enough_to_skip_canonical_step() -> None:
    input_value = traversal_input().model_copy(
        update={
            "learner_evidence": (
                LearnerConceptEvidence(
                    concept_id="index",
                    level=LearnerEvidenceLevel.SUPPORTED_SUCCESS,
                    evidence_refs=("attempt.index.hinted",),
                ),
            )
        }
    )
    decision = traversal_decision().model_copy(update={"skipped_concepts": ("index",)})
    assert traversal_codes(input_value, decision) == (
        TraversalViolationCode.UNSUPPORTED_SKIP_EVIDENCE,
    )


def test_unknown_selected_step_is_rejected() -> None:
    decision = traversal_decision().model_copy(
        update={"selected_step_ids": ("invented_step",)}
    )
    assert traversal_codes(traversal_input(), decision) == (
        TraversalViolationCode.UNKNOWN_SELECTED_STEP,
    )


def test_unknown_skipped_concept_is_rejected() -> None:
    decision = traversal_decision().model_copy(
        update={"skipped_concepts": ("imaginary_concept",)}
    )
    assert traversal_codes(traversal_input(), decision) == (
        TraversalViolationCode.UNKNOWN_SKIPPED_CONCEPT,
    )


def test_duplicate_selected_steps_are_rejected() -> None:
    decision = traversal_decision().model_copy(
        update={"selected_step_ids": ("introduce_search_region", "introduce_search_region")}
    )
    assert traversal_codes(traversal_input(), decision) == (
        TraversalViolationCode.DUPLICATE_SELECTED_STEP,
    )


def test_traversal_case_mismatch_is_rejected() -> None:
    decision = traversal_decision().model_copy(update={"case_id": "wrong-case"})
    assert traversal_codes(traversal_input(), decision) == (
        TraversalViolationCode.CASE_ID_MISMATCH,
    )
