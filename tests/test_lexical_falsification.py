from __future__ import annotations

from pathlib import Path

from study_os_pir.language import (
    LexicalRegister,
    LexicalRule,
    LexicalViolationCode,
    validate_lexical_register,
)
from study_os_pir.trajectory import ExperimentalTrajectory, validate_trajectory

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "sliding-window-foundations"
TRAJECTORY_PATH = FIXTURE_DIR / "trajectory.i-sum.v0.json"
REGISTER_PATH = FIXTURE_DIR / "register.beginner-grounded.v0.json"
PROBLEM_TEXT = "Find the largest sum of any 3 numbers next to each other in the array."


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(TRAJECTORY_PATH.read_text())


def load_register() -> LexicalRegister:
    return LexicalRegister.model_validate_json(REGISTER_PATH.read_text())


def vocabulary_drift_mutation() -> ExperimentalTrajectory:
    trajectory = load_trajectory()
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


def test_source_backed_beginner_register_accepts_current_replay_surface() -> None:
    assert (
        validate_lexical_register(
            load_trajectory(),
            load_register(),
            persistent_text=(PROBLEM_TEXT,),
        )
        == ()
    )


def test_semantic_validator_misses_drift_but_lexical_register_rejects_it() -> None:
    mutated = vocabulary_drift_mutation()

    assert validate_trajectory(mutated) == ()
    violations = validate_lexical_register(
        mutated,
        load_register(),
        persistent_text=(PROBLEM_TEXT,),
    )
    forbidden = [
        violation
        for violation in violations
        if violation.code == LexicalViolationCode.FORBIDDEN_TERM_PRESENT
    ]
    assert {"'elements'", "'window'"}.issubset(
        {fragment for violation in forbidden for fragment in violation.detail.split()}
    )


def test_register_definition_is_itself_deterministically_validated() -> None:
    bad_rule = LexicalRule(
        concept_id="selected_group",
        preferred_term="window",
        allowed_terms=("box", "window"),
        forbidden_terms=("window",),
    )
    register = LexicalRegister(
        schema_version="pir.experimental-lexical-register.v0",
        register_id="bad",
        description="exercise register-definition failures",
        rules=(bad_rule, bad_rule.model_copy(update={"preferred_term": "segment"})),
    )
    violations = validate_lexical_register(load_trajectory(), register)
    codes = {violation.code for violation in violations}
    assert LexicalViolationCode.DUPLICATE_CONCEPT_RULE in codes
    assert LexicalViolationCode.PREFERRED_TERM_NOT_ALLOWED in codes
    assert LexicalViolationCode.ALLOWED_FORBIDDEN_OVERLAP in codes
    assert LexicalViolationCode.FORBIDDEN_TERM_PRESENT not in codes


def test_lexical_validator_skips_missing_representation_already_owned_by_semantic_gate() -> None:
    trajectory = load_trajectory()
    first = trajectory.steps[0].model_copy(update={"representation_id": "missing"})
    mutated = trajectory.model_copy(update={"steps": (first, *trajectory.steps[1:])})

    violations = validate_lexical_register(mutated, load_register())
    assert violations == ()
    assert validate_trajectory(mutated) != ()
