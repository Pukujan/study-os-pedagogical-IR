from __future__ import annotations

from pathlib import Path

from study_os_pir.vertical import (
    ExperimentalVerticalSlice,
    VerticalViolationCode,
    render_vertical_slice,
    validate_vertical_execution,
    validate_vertical_slice,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "public" / "max-sum-s0-to-si" / "vertical-slice.v0.json"


def load_slice() -> ExperimentalVerticalSlice:
    return ExperimentalVerticalSlice.model_validate_json(FIXTURE.read_text())


def test_calibrated_vertical_slice_is_structurally_valid() -> None:
    assert validate_vertical_slice(load_slice()) == ()


def test_human_rendering_exposes_behavior_not_just_ids() -> None:
    rendered = render_vertical_slice(load_slice())
    assert "Show why the learner's value answer was correct using the same chart" in rendered
    assert "without yet giving the target code line" in rendered
    assert "Question: Write the Python line that saves S[0] into max_sum." in rendered
    assert "Question: Hint: i = 0, so S[0] and S[i] name the same current entry." in rendered
    assert "Only after S[i] production and validation" in rendered
    assert "window    : ^^^ ^^^ ^^^" in rendered
    assert "Observed rejected moves:" in rendered
    assert "reject.si_answer_leak" in rendered


def test_exact_calibrated_execution_passes() -> None:
    slice_ = load_slice()
    expected = tuple(step.step_id for step in slice_.steps)
    assert validate_vertical_execution(slice_, expected) == ()


def test_semantic_compression_by_deleting_bridge_fails() -> None:
    slice_ = load_slice()
    executed = tuple(
        step.step_id for step in slice_.steps if step.step_id != "bridge_s0_to_si_when_i0"
    )
    violations = validate_vertical_execution(slice_, executed)
    assert tuple(v.code for v in violations) == (VerticalViolationCode.EXECUTION_MISSING_STEP,)
    assert "bridge_s0_to_si_when_i0" in violations[0].detail


def test_same_steps_in_wrong_order_fail() -> None:
    slice_ = load_slice()
    expected = tuple(step.step_id for step in slice_.steps)
    executed = (expected[1], expected[0], *expected[2:])
    violations = validate_vertical_execution(slice_, executed)
    assert tuple(v.code for v in violations) == (VerticalViolationCode.EXECUTION_ORDER_MISMATCH,)


def test_unexpected_execution_step_fails() -> None:
    slice_ = load_slice()
    expected = tuple(step.step_id for step in slice_.steps)
    violations = validate_vertical_execution(slice_, (*expected, "invented_step"))
    assert tuple(v.code for v in violations) == (VerticalViolationCode.EXECUTION_UNEXPECTED_STEP,)


def test_duplicate_step_id_fails() -> None:
    slice_ = load_slice()
    duplicate = slice_.steps[0].model_copy(update={"goal": "duplicate"})
    mutated = slice_.model_copy(update={"steps": (*slice_.steps, duplicate)})
    violations = validate_vertical_slice(mutated)
    assert VerticalViolationCode.DUPLICATE_STEP_ID in tuple(v.code for v in violations)


def test_duplicate_representation_id_fails() -> None:
    slice_ = load_slice()
    duplicate = slice_.representations[0].model_copy(update={"annotations": ("duplicate",)})
    mutated = slice_.model_copy(update={"representations": (*slice_.representations, duplicate)})
    violations = validate_vertical_slice(mutated)
    assert VerticalViolationCode.DUPLICATE_REPRESENTATION_ID in tuple(v.code for v in violations)


def test_unknown_representation_fails() -> None:
    slice_ = load_slice()
    bad_step = slice_.steps[0].model_copy(update={"representation_id": "missing"})
    mutated = slice_.model_copy(update={"steps": (bad_step, *slice_.steps[1:])})
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (VerticalViolationCode.UNKNOWN_REPRESENTATION,)


def test_missing_preserved_component_fails() -> None:
    slice_ = load_slice()
    step = slice_.steps[0]
    bad_step = step.model_copy(
        update={"preserve_components": (*step.preserve_components, "removed_chart_layer")}
    )
    mutated = slice_.model_copy(update={"steps": (bad_step, *slice_.steps[1:])})
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.MISSING_PRESERVED_REPRESENTATION,
    )


def test_forbidden_concept_disclosure_fails() -> None:
    slice_ = load_slice()
    step = slice_.steps[5]
    bad_step = step.model_copy(update={"disclosed_concepts": ("comparison",)})
    mutated = slice_.model_copy(update={"steps": (*slice_.steps[:5], bad_step, *slice_.steps[6:])})
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.FORBIDDEN_CONCEPT_DISCLOSED,
    )


def test_answer_literal_leak_fails() -> None:
    slice_ = load_slice()
    step = slice_.steps[6]
    assert step.probe is not None
    bad_probe = step.probe.model_copy(update={"prompt": step.probe.prompt + " max_sum = S[i]"})
    bad_step = step.model_copy(update={"probe": bad_probe})
    mutated = slice_.model_copy(update={"steps": (*slice_.steps[:6], bad_step, *slice_.steps[7:])})
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (VerticalViolationCode.ANSWER_LITERAL_LEAKED,)


def test_answer_literal_is_not_policed_when_reveal_is_explicitly_allowed() -> None:
    slice_ = load_slice()
    step = slice_.steps[6]
    assert step.probe is not None
    probe = step.probe.model_copy(
        update={"prompt": step.probe.prompt + " max_sum = S[i]", "answer_reveal_allowed": True}
    )
    allowed_step = step.model_copy(update={"probe": probe})
    mutated = slice_.model_copy(
        update={"steps": (*slice_.steps[:6], allowed_step, *slice_.steps[7:])}
    )
    assert validate_vertical_slice(mutated) == ()


def test_empty_forbidden_literal_is_ignored() -> None:
    slice_ = load_slice()
    step = slice_.steps[6]
    assert step.probe is not None
    probe = step.probe.model_copy(update={"forbidden_answer_literals": ("",)})
    allowed_step = step.model_copy(update={"probe": probe})
    mutated = slice_.model_copy(
        update={"steps": (*slice_.steps[:6], allowed_step, *slice_.steps[7:])}
    )
    assert validate_vertical_slice(mutated) == ()


def test_unknown_rejected_move_anchor_fails() -> None:
    slice_ = load_slice()
    move = slice_.rejected_moves[0].model_copy(update={"after_step_id": "missing"})
    mutated = slice_.model_copy(update={"rejected_moves": (move, *slice_.rejected_moves[1:])})
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.UNKNOWN_REJECTED_MOVE_ANCHOR,
    )


def test_unknown_rejected_move_repair_fails() -> None:
    slice_ = load_slice()
    move = slice_.rejected_moves[0].model_copy(update={"repaired_by_step_id": "missing"})
    mutated = slice_.model_copy(update={"rejected_moves": (move, *slice_.rejected_moves[1:])})
    violations = validate_vertical_slice(mutated)
    assert tuple(v.code for v in violations) == (
        VerticalViolationCode.UNKNOWN_REJECTED_MOVE_REPAIR,
    )
