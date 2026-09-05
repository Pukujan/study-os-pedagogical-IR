from __future__ import annotations

from pathlib import Path

from study_os_pir.lexical import (
    ExperimentalLexicalPolicy,
    LexicalStepPolicy,
    LexicalViolationCode,
    validate_lexical_policy,
    validate_lexical_text,
    validate_rendered_turn,
)
from study_os_pir.trajectory import ExperimentalTrajectory, validate_trajectory

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "sliding-window-foundations"
TRAJECTORY_PATH = FIXTURE_DIR / "trajectory.i-sum.v0.json"
POLICY_PATH = FIXTURE_DIR / "lexical.i-sum.v0.json"


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(TRAJECTORY_PATH.read_text())


def load_policy() -> ExperimentalLexicalPolicy:
    return ExperimentalLexicalPolicy.model_validate_json(POLICY_PATH.read_text())


def mutate_intro_to_premature_register(
    trajectory: ExperimentalTrajectory,
) -> ExperimentalTrajectory:
    target = next(
        representation
        for representation in trajectory.representations
        if representation.representation_id == "r.i_intro0"
    )
    rows = tuple(
        row.model_copy(update={"label": "elements(a)"})
        if row.row_id == "numbers_row"
        else row
        for row in target.rows
    )
    annotations = tuple(
        annotation.replace("box", "window") for annotation in target.annotations
    )
    mutated_representation = target.model_copy(
        update={"rows": rows, "annotations": annotations}
    )
    representations = tuple(
        mutated_representation
        if representation.representation_id == target.representation_id
        else representation
        for representation in trajectory.representations
    )
    return trajectory.model_copy(update={"representations": representations})


def test_source_backed_lexical_policy_accepts_current_i_sum_trajectory() -> None:
    assert validate_lexical_policy(load_trajectory(), load_policy()) == ()


def test_semantic_validator_still_accepts_pure_register_mutation() -> None:
    mutated = mutate_intro_to_premature_register(load_trajectory())
    assert validate_trajectory(mutated) == ()


def test_lexical_policy_rejects_same_register_mutation() -> None:
    mutated = mutate_intro_to_premature_register(load_trajectory())
    violations = validate_lexical_policy(mutated, load_policy())
    codes = {violation.code for violation in violations}
    assert LexicalViolationCode.MISSING_REQUIRED_TERM in codes
    assert LexicalViolationCode.FORBIDDEN_TERM_PRESENT in codes


def test_rendered_turn_policy_rejects_premature_technical_surface() -> None:
    policy = load_policy()
    violations = validate_rendered_turn(
        policy,
        "i_intro0",
        "elements(a): 4 7 2 6 1 9\nwindow: ^^^^^ ^^^^^",
    )
    codes = {violation.code for violation in violations}
    assert LexicalViolationCode.MISSING_REQUIRED_TERM in codes
    assert LexicalViolationCode.FORBIDDEN_TERM_PRESENT in codes


def test_rendered_turn_policy_is_selective_for_unscoped_steps() -> None:
    assert validate_rendered_turn(load_policy(), "not_scoped", "anything") == ()


def test_policy_reports_trajectory_mismatch_duplicate_unknown_and_conflict() -> None:
    policy = load_policy()
    first = policy.steps[0]
    conflict = first.model_copy(
        update={"required_terms": ("box",), "forbidden_terms": ("BOX",)}
    )
    unknown = LexicalStepPolicy(step_id="missing_step")
    invalid = policy.model_copy(
        update={
            "trajectory_id": "other-trajectory",
            "steps": (conflict, conflict, unknown),
        }
    )
    violations = validate_lexical_policy(load_trajectory(), invalid)
    codes = {violation.code for violation in violations}
    assert LexicalViolationCode.TRAJECTORY_ID_MISMATCH in codes
    assert LexicalViolationCode.DUPLICATE_STEP_POLICY in codes
    assert LexicalViolationCode.UNKNOWN_STEP in codes
    assert LexicalViolationCode.TERM_CONFLICT in codes
    assert LexicalViolationCode.FORBIDDEN_TERM_PRESENT in codes


def test_lexical_text_matching_is_case_insensitive_and_reports_missing_terms() -> None:
    policy = LexicalStepPolicy(
        step_id="example",
        required_terms=("Number", "BOX"),
        forbidden_terms=("Element",),
    )
    assert validate_lexical_text(policy, "NUMBER in the box") == ()

    violations = validate_lexical_text(policy, "element")
    codes = {violation.code for violation in violations}
    assert LexicalViolationCode.MISSING_REQUIRED_TERM in codes
    assert LexicalViolationCode.FORBIDDEN_TERM_PRESENT in codes
