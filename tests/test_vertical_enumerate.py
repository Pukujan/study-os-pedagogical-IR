from __future__ import annotations

from pathlib import Path

from study_os_pir.vertical import (
    ExperimentalVerticalSlice,
    VerticalViolationCode,
    VerticalWindowBox,
    render_vertical_slice,
    validate_vertical_execution,
    validate_vertical_slice,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "public" / "enumerate-calibration" / "vertical-slice.v0.json"


def load_slice() -> ExperimentalVerticalSlice:
    return ExperimentalVerticalSlice.model_validate_json(FIXTURE.read_text())


def test_enumerate_slice_is_structurally_valid() -> None:
    assert validate_vertical_slice(load_slice()) == ()


def test_enumerate_rendering_exposes_chart_validation_and_exit() -> None:
    rendered = render_vertical_slice(load_slice())
    assert "Explain enumerate(a) as one current index plus one current number" in rendered
    assert "When the loop reaches a = 6" in rendered
    assert "Show why the learner's (3,6) answer is correct" in rendered
    assert "In this changed array" in rendered
    assert "Learner outcomes:" in rendered
    assert "meta.two_is_enough" in rendered
    assert "Route: exit:append" in rendered
    assert "Repair: exit:append" in rendered
    assert "window    :" not in rendered


def test_exact_enumerate_execution_passes() -> None:
    slice_ = load_slice()
    expected = tuple(step.step_id for step in slice_.steps)
    assert validate_vertical_execution(slice_, expected) == ()


def test_deleting_same_chart_validation_fails_execution() -> None:
    slice_ = load_slice()
    executed = tuple(
        step.step_id
        for step in slice_.steps
        if step.step_id != "validate_pair_36_same_chart"
    )
    violations = validate_vertical_execution(slice_, executed)
    assert tuple(v.code for v in violations) == (VerticalViolationCode.EXECUTION_MISSING_STEP,)
    assert "validate_pair_36_same_chart" in violations[0].detail


def test_window_box_in_enumerate_probe_is_forbidden() -> None:
    slice_ = load_slice()
    representation = slice_.representations[1]
    mutated_representation = representation.model_copy(
        update={"box": VerticalWindowBox(start_index=0, width=1)}
    )
    mutated = slice_.model_copy(
        update={
            "representations": (
                slice_.representations[0],
                mutated_representation,
                *slice_.representations[2:],
            )
        }
    )
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.FORBIDDEN_REPRESENTATION_PRESENT,
    )


def test_answer_leak_in_probe_prompt_is_rejected() -> None:
    slice_ = load_slice()
    step = slice_.steps[1]
    assert step.probe is not None
    bad_probe = step.probe.model_copy(update={"prompt": step.probe.prompt + " (3,6)"})
    bad_step = step.model_copy(update={"probe": bad_probe})
    mutated = slice_.model_copy(update={"steps": (slice_.steps[0], bad_step, *slice_.steps[2:])})
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (VerticalViolationCode.ANSWER_LITERAL_LEAKED,)


def test_answer_leak_in_visible_chart_is_rejected() -> None:
    slice_ = load_slice()
    representation = slice_.representations[1]
    bad_representation = representation.model_copy(
        update={"annotations": (*representation.annotations, "enumerate gives (3,6)")}
    )
    mutated = slice_.model_copy(
        update={
            "representations": (
                slice_.representations[0],
                bad_representation,
                *slice_.representations[2:],
            )
        }
    )
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (VerticalViolationCode.ANSWER_LITERAL_LEAKED,)


def test_duplicate_learner_outcome_id_fails() -> None:
    slice_ = load_slice()
    duplicate = slice_.learner_outcomes[0].model_copy()
    mutated = slice_.model_copy(update={"learner_outcomes": (*slice_.learner_outcomes, duplicate)})
    violations = validate_vertical_slice(mutated)
    assert VerticalViolationCode.DUPLICATE_LEARNER_OUTCOME_ID in tuple(
        violation.code for violation in violations
    )


def test_unknown_learner_outcome_anchor_fails() -> None:
    slice_ = load_slice()
    outcome = slice_.learner_outcomes[0].model_copy(update={"after_step_id": "missing"})
    mutated = slice_.model_copy(
        update={"learner_outcomes": (outcome, *slice_.learner_outcomes[1:])}
    )
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.UNKNOWN_LEARNER_OUTCOME_ANCHOR,
    )


def test_learner_outcome_must_choose_exactly_one_route() -> None:
    slice_ = load_slice()
    outcome = slice_.learner_outcomes[0].model_copy(update={"exit_target": "append"})
    mutated = slice_.model_copy(
        update={"learner_outcomes": (outcome, *slice_.learner_outcomes[1:])}
    )
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.INVALID_LEARNER_OUTCOME_ROUTE,
    )


def test_learner_outcome_unknown_next_step_fails() -> None:
    slice_ = load_slice()
    outcome = slice_.learner_outcomes[0].model_copy(update={"next_step_id": "missing"})
    mutated = slice_.model_copy(
        update={"learner_outcomes": (outcome, *slice_.learner_outcomes[1:])}
    )
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.UNKNOWN_LEARNER_OUTCOME_NEXT_STEP,
    )


def test_rejected_move_must_choose_exactly_one_repair_route() -> None:
    slice_ = load_slice()
    move = slice_.rejected_moves[0].model_copy(update={"repair_exit_target": "append"})
    mutated = slice_.model_copy(update={"rejected_moves": (move, *slice_.rejected_moves[1:])})
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.INVALID_REJECTED_MOVE_REPAIR_ROUTE,
    )


def test_two_successful_probes_can_exit_to_append_without_third_exercise() -> None:
    slice_ = load_slice()
    outcome = next(
        item for item in slice_.learner_outcomes if item.outcome_id == "meta.two_is_enough"
    )
    assert outcome.after_step_id == "validate_pair_47_same_chart"
    assert outcome.next_step_id is None
    assert outcome.exit_target == "append"

    rejected = next(
        item
        for item in slice_.rejected_moves
        if item.move_id == "reject.unnecessary_third_enumerate_exercise"
    )
    assert rejected.repaired_by_step_id is None
    assert rejected.repair_exit_target == "append"
