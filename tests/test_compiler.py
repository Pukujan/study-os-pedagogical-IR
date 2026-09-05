from __future__ import annotations

from pathlib import Path

from study_os_pir.compiler import (
    CompilerDependency,
    CompilerInput,
    CompilerMicrostep,
    CompilerPolicy,
    CompilerProposal,
    CompilerViolationCode,
    PrerequisiteAction,
    PrerequisitePlan,
    validate_compiler_proposal,
)

ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = ROOT / "fixtures" / "public" / "compiler-policies"
DEVELOPMENT_DIR = ROOT / "fixtures" / "public" / "compiler-development"


def load_policy(name: str = "compiler-p4.0.1.0.json") -> CompilerPolicy:
    return CompilerPolicy.model_validate_json((POLICY_DIR / name).read_text())


def load_input(name: str = "binary-search.input.v0.json") -> CompilerInput:
    return CompilerInput.model_validate_json((DEVELOPMENT_DIR / name).read_text())


def valid_proposal() -> CompilerProposal:
    compiler_input = load_input()
    return CompilerProposal(
        schema_version="pir.compiler-proposal.v0",
        case_id=compiler_input.case_id,
        policy_ref=compiler_input.policy_ref,
        problem_objects=("array", "target"),
        roles=("current_search_region",),
        prerequisite_plan=(
            PrerequisitePlan(
                concept_id="index",
                action=PrerequisiteAction.REUSE,
                rationale="learner has unaided index evidence",
            ),
            PrerequisitePlan(
                concept_id="search_interval",
                action=PrerequisiteAction.TEACH,
                rationale="learner evidence is unknown",
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
                step_id="introduce_search_region",
                operation="highlight the current region that can still contain the target",
                introduces=("search_interval",),
                preserves=("array", "indexes"),
                representation_requirements=("highlighted_search_region",),
                assessment_target="identify the active region",
            ),
            CompilerMicrostep(
                step_id="introduce_midpoint",
                operation="choose the middle index of the current search region",
                introduces=("midpoint",),
                preserves=("array", "indexes", "search_interval"),
                representation_requirements=("middle_index_marker",),
                assessment_target="identify the middle index",
            ),
        ),
        invariants=("if the target exists, it remains in the current search region",),
        conditions=("compare target with the value at the middle index",),
        misconception_candidates=("index_position_confusion",),
        generalization_path=("concrete region", "bounds", "midpoint expression", "loop"),
    )


def codes(
    compiler_input: CompilerInput,
    policy: CompilerPolicy,
    proposal: CompilerProposal,
) -> tuple[CompilerViolationCode, ...]:
    return tuple(
        violation.code
        for violation in validate_compiler_proposal(compiler_input, policy, proposal)
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
        CompilerInput.model_validate_json(path.read_text())
        for path in sorted(DEVELOPMENT_DIR.glob("*.json"))
    )
    assert {compiler_input.case_id for compiler_input in inputs} == {
        "dev.dsa.bfs-shortest-path.v0",
        "dev.dsa.binary-search.v0",
        "dev.dsa.two-pointers.v0",
    }
    assert all(compiler_input.policy_ref == "compiler-p4@0.1.0" for compiler_input in inputs)


def test_valid_compiler_proposal_passes() -> None:
    assert validate_compiler_proposal(load_input(), load_policy(), valid_proposal()) == ()


def test_case_identity_mismatch_is_rejected() -> None:
    proposal = valid_proposal().model_copy(update={"case_id": "wrong-case"})
    assert codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.CASE_ID_MISMATCH,
    )


def test_input_policy_mismatch_is_rejected() -> None:
    compiler_input = load_input().model_copy(update={"policy_ref": "compiler-p3@0.1.0"})
    assert codes(compiler_input, load_policy(), valid_proposal()) == (
        CompilerViolationCode.POLICY_REF_MISMATCH,
    )


def test_proposal_policy_mismatch_is_rejected() -> None:
    proposal = valid_proposal().model_copy(update={"policy_ref": "compiler-p3@0.1.0"})
    assert codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.POLICY_REF_MISMATCH,
    )


def test_unknown_prerequisite_cannot_be_silently_reused() -> None:
    proposal = valid_proposal().model_copy(
        update={
            "prerequisite_plan": (
                PrerequisitePlan(
                    concept_id="midpoint",
                    action=PrerequisiteAction.REUSE,
                    rationale="incorrectly assumes unknown knowledge",
                ),
            )
        }
    )
    assert codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.UNSUPPORTED_KNOWLEDGE_ASSUMPTION,
    )


def test_unknown_prerequisite_may_be_probed() -> None:
    proposal = valid_proposal().model_copy(
        update={
            "prerequisite_plan": (
                PrerequisitePlan(
                    concept_id="midpoint",
                    action=PrerequisiteAction.PROBE,
                    rationale="collect evidence before deciding whether to teach",
                ),
            )
        }
    )
    assert validate_compiler_proposal(load_input(), load_policy(), proposal) == ()


def test_known_prerequisite_may_be_reused() -> None:
    proposal = valid_proposal().model_copy(
        update={
            "prerequisite_plan": (
                PrerequisitePlan(
                    concept_id="index",
                    action=PrerequisiteAction.REUSE,
                    rationale="learner has unaided evidence",
                ),
            )
        }
    )
    assert validate_compiler_proposal(load_input(), load_policy(), proposal) == ()


def test_policy_concept_budget_rejects_multi_concept_jump() -> None:
    step = valid_proposal().microsteps[0].model_copy(
        update={"introduces": ("search_interval", "left_bound")}
    )
    proposal = valid_proposal().model_copy(update={"microsteps": (step,)})
    assert codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.TOO_MANY_NEW_CONCEPTS,
    )


def test_duplicate_microstep_ids_are_rejected() -> None:
    first = valid_proposal().microsteps[0]
    second = valid_proposal().microsteps[1].model_copy(update={"step_id": first.step_id})
    proposal = valid_proposal().model_copy(update={"microsteps": (first, second)})
    assert codes(load_input(), load_policy(), proposal) == (
        CompilerViolationCode.DUPLICATE_MICROSTEP_ID,
    )
