from __future__ import annotations

from pathlib import Path

import pytest

from study_os_pir.console import render_turn_text
from study_os_pir.runtime import (
    AssessmentKind,
    AssessmentRegistry,
    AssessmentSpec,
    ReplayContext,
    ReplayCursor,
    ReplayPhase,
    build_renderer_contract,
    classify_response,
    mark_turn_rendered,
    start_replay,
    submit_response,
    validate_assessment_registry,
)
from study_os_pir.trajectory import ExperimentalTrajectory, TrajectoryOutcomeKind, validate_trajectory

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "sliding-window-foundations"


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(
        (FIXTURE_DIR / "trajectory.i-sum.v0.json").read_text()
    )


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(
        (FIXTURE_DIR / "assessments.i-sum.v0.json").read_text()
    )


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(
        (FIXTURE_DIR / "context.i-sum.v0.json").read_text()
    )


def cursor_at(step_id: str, phase: ReplayPhase) -> ReplayCursor:
    return ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=load_trajectory().trajectory_id,
        phase=phase,
        current_step_id=step_id,
    )


def render_until_blocked(cursor: ReplayCursor) -> ReplayCursor:
    trajectory = load_trajectory()
    current = cursor
    while current.phase == ReplayPhase.RENDER:
        build_renderer_contract(trajectory, current, load_context())
        current = mark_turn_rendered(trajectory, current)
    return current


def answer_and_render(
    cursor: ReplayCursor,
    response: str,
) -> tuple[TrajectoryOutcomeKind, ReplayCursor]:
    result = submit_response(load_trajectory(), load_registry(), cursor, response)
    return result.outcome, render_until_blocked(result.cursor)


def test_i_sum_fixture_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()


def test_persistent_problem_context_is_learner_visible_on_late_sum_turn() -> None:
    trajectory = load_trajectory()
    contract = build_renderer_contract(
        trajectory,
        cursor_at("sum_probe2_k2", ReplayPhase.RENDER),
        load_context(),
    )
    text = render_turn_text(contract)
    assert text.startswith("Find the largest sum of any 3 numbers next to each other in the array.")
    assert "With i = 2 and k = 2, what is sum[i=2]?" in text


def test_renderer_contract_without_context_remains_supported() -> None:
    contract = build_renderer_contract(
        load_trajectory(),
        cursor_at("i_intro0", ReplayPhase.RENDER),
    )
    assert contract.persistent_text == ()
    assert not render_turn_text(contract).startswith("Find the largest sum")


def test_replay_context_must_match_trajectory() -> None:
    context = load_context().model_copy(update={"trajectory_id": "other"})
    with pytest.raises(ValueError, match="replay context trajectory does not match"):
        build_renderer_contract(
            load_trajectory(),
            cursor_at("i_intro0", ReplayPhase.RENDER),
            context,
        )


def test_partial_integer_answer_preserves_correct_box_contents() -> None:
    spec = AssessmentSpec(
        step_id="sum",
        kind=AssessmentKind.INTEGER,
        expected_values=(8,),
        partial_values=(2, 6),
    )
    assert classify_response(spec, "2 6") == TrajectoryOutcomeKind.PARTIAL
    assert classify_response(spec, "2,6") == TrajectoryOutcomeKind.PARTIAL
    assert classify_response(spec, "8") == TrajectoryOutcomeKind.CORRECT
    assert classify_response(spec, "7") == TrajectoryOutcomeKind.INCORRECT


def test_partial_matching_does_not_swallow_unsupported_text() -> None:
    spec = AssessmentSpec(
        step_id="sum",
        kind=AssessmentKind.INTEGER,
        expected_values=(8,),
        partial_values=(2, 6),
    )
    with pytest.raises(ValueError, match="single integer"):
        classify_response(spec, "two six")


def test_partial_values_can_be_checked_after_sequence_parse() -> None:
    spec = AssessmentSpec(
        step_id="sequence",
        kind=AssessmentKind.INTEGER_SEQUENCE,
        expected_values=(2, 6, 1),
        partial_values=(2, 6),
    )
    assert classify_response(spec, "2 6") == TrajectoryOutcomeKind.PARTIAL


def test_renderer_safe_contract_does_not_expose_partial_or_expected_oracle() -> None:
    contract = build_renderer_contract(
        load_trajectory(),
        cursor_at("sum_probe2_k2", ReplayPhase.RENDER),
        load_context(),
    )
    payload = contract.model_dump_json()
    assert "expected_values" not in payload
    assert "partial_values" not in payload
    assert "2 + 6 = 8" not in payload


def test_sum_partial_path_asks_only_missing_arithmetic_then_rejoins() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at("sum_probe2_k2", ReplayPhase.AWAIT_RESPONSE)

    result = submit_response(trajectory, load_registry(), cursor, "2 6")
    assert result.outcome == TrajectoryOutcomeKind.PARTIAL
    assert result.cursor.current_step_id == "sum_partial_contents2_k2"

    cursor = mark_turn_rendered(trajectory, result.cursor)
    assert cursor.current_step_id == "sum_partial_arithmetic2_k2"

    contract = build_renderer_contract(trajectory, cursor, load_context())
    assert contract.probe is not None
    assert contract.probe.prompt == "2 + 6 = ?"
    assert contract.representation.box is not None
    assert contract.representation.box.start_index == 2
    assert contract.representation.box.width == 2

    cursor = mark_turn_rendered(trajectory, cursor)
    result = submit_response(trajectory, load_registry(), cursor, "8")
    assert result.outcome == TrajectoryOutcomeKind.CORRECT
    assert result.cursor.current_step_id == "sum_validate8"


def test_correct_i_and_sum_path_reaches_successive_sums() -> None:
    trajectory = load_trajectory()
    cursor = render_until_blocked(start_replay(trajectory, load_registry()))
    assert cursor.current_step_id == "i_probe1_guided"

    scripted = (
        ("7 2", TrajectoryOutcomeKind.CORRECT, "i_probe3_unassisted"),
        ("6 1", TrajectoryOutcomeKind.CORRECT, "sum_probe2_k3"),
        ("9", TrajectoryOutcomeKind.CORRECT, "sum_probe2_k2"),
        ("8", TrajectoryOutcomeKind.CORRECT, "sum_verify3_k3"),
    )
    for response, expected_outcome, expected_step in scripted:
        outcome, cursor = answer_and_render(cursor, response)
        assert outcome == expected_outcome
        assert cursor.current_step_id == expected_step
        assert cursor.phase == ReplayPhase.AWAIT_RESPONSE

    result = submit_response(trajectory, load_registry(), cursor, "16")
    assert result.outcome == TrajectoryOutcomeKind.CORRECT
    cursor = mark_turn_rendered(trajectory, result.cursor)
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "successive_sums"


def test_wrong_i_path_corrects_retries_confirms_then_rejoins_sum() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at("i_probe3_unassisted", ReplayPhase.AWAIT_RESPONSE)
    result = submit_response(trajectory, load_registry(), cursor, "2 6")
    assert result.outcome == TrajectoryOutcomeKind.INCORRECT
    assert result.cursor.current_step_id == "i_correct3"

    cursor = mark_turn_rendered(trajectory, result.cursor)
    cursor = mark_turn_rendered(trajectory, cursor)
    assert cursor.phase == ReplayPhase.AWAIT_RESPONSE
    assert cursor.current_step_id == "i_retry2_after_error"

    outcome, cursor = answer_and_render(cursor, "2 6")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "i_confirm1_k3"

    outcome, cursor = answer_and_render(cursor, "7 2 6")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "sum_probe2_k3"


def test_wrong_sum_path_requires_changed_retry_and_confirmation() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at("sum_probe2_k2", ReplayPhase.AWAIT_RESPONSE)
    result = submit_response(trajectory, load_registry(), cursor, "7")
    assert result.outcome == TrajectoryOutcomeKind.INCORRECT
    assert result.cursor.current_step_id == "sum_correct8_wrong"

    cursor = mark_turn_rendered(trajectory, result.cursor)
    cursor = mark_turn_rendered(trajectory, cursor)
    assert cursor.current_step_id == "sum_retry3_k3_after_error"
    assert cursor.phase == ReplayPhase.AWAIT_RESPONSE

    outcome, cursor = answer_and_render(cursor, "16")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "sum_confirm1_k2"

    result = submit_response(trajectory, load_registry(), cursor, "9")
    assert result.outcome == TrajectoryOutcomeKind.CORRECT
    cursor = mark_turn_rendered(trajectory, result.cursor)
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "successive_sums"


def test_unmodeled_repeated_error_still_fails_closed() -> None:
    cursor = cursor_at("sum_retry3_k3_after_error", ReplayPhase.AWAIT_RESPONSE)
    with pytest.raises(ValueError, match="no unique route for outcome incorrect"):
        submit_response(load_trajectory(), load_registry(), cursor, "15")
