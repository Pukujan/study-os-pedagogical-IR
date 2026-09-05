from __future__ import annotations

from pathlib import Path

import pytest

from study_os_pir.console import render_turn_text
from study_os_pir.runtime import (
    AssessmentRegistry,
    ReplayContext,
    ReplayCursor,
    ReplayPhase,
    build_renderer_contract,
    mark_turn_rendered,
    start_replay,
    submit_response,
    validate_assessment_registry,
)
from study_os_pir.trajectory import (
    ExperimentalTrajectory,
    TrajectoryOutcomeKind,
    validate_trajectory,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "sliding-window-foundations"


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(
        (FIXTURE_DIR / "trajectory.restore-after-code.v0.json").read_text()
    )


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(
        (FIXTURE_DIR / "assessments.restore-after-code.v0.json").read_text()
    )


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(
        (FIXTURE_DIR / "context.restore-after-code.v0.json").read_text()
    )


def render_until_blocked(cursor: ReplayCursor) -> ReplayCursor:
    trajectory = load_trajectory()
    current = cursor
    while current.phase == ReplayPhase.RENDER:
        build_renderer_contract(trajectory, current, load_context())
        current = mark_turn_rendered(trajectory, current)
    return current


def answer_and_render(cursor: ReplayCursor, response: str) -> tuple[TrajectoryOutcomeKind, ReplayCursor]:
    result = submit_response(load_trajectory(), load_registry(), cursor, response)
    return result.outcome, render_until_blocked(result.cursor)


def test_restore_after_code_fixture_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()


def test_entry_restores_array_indexes_all_boxes_and_s_mapping() -> None:
    trajectory = load_trajectory()
    cursor = start_replay(trajectory, load_registry())
    contract = build_renderer_contract(trajectory, cursor, load_context())
    row_ids = {row.row_id for row in contract.representation.rows}
    text = render_turn_text(contract)

    assert {"index_row", "numbers_row", "s_row"} <= row_ids
    assert contract.representation.box is not None
    assert contract.representation.box.start_index == 0
    assert len(contract.representation.boxes) == 3
    assert [box.start_index for box in contract.representation.boxes] == [1, 2, 3]
    assert "i=0: 3 + 8 + 1 = 12 -> S[0]" in text
    assert "i=3: 8 - 1 + 7 = 14 -> S[3]" in text
    assert "largest_window_sum" not in text
    assert "max_tracking" not in text


def test_historical_error_correction_retry_and_second_verification_gate_exit() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    assert cursor.current_step_id == "restore_probe_s2"

    outcome, cursor = answer_and_render(cursor, "8")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "restore_probe_s3"

    outcome, cursor = answer_and_render(cursor, "12")
    assert outcome == TrajectoryOutcomeKind.INCORRECT
    assert "restore_correct_s3" in cursor.visited_step_ids
    assert cursor.current_step_id == "restore_retry_s3_changed"

    outcome, cursor = answer_and_render(cursor, "9")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "restore_verify_s2_changed"

    outcome, cursor = answer_and_render(cursor, "11")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "largest_window_sum"
    assert "restore_validate_s2_changed" in cursor.visited_step_ids


def test_detached_s_only_validation_is_not_an_allowed_representation() -> None:
    trajectory = load_trajectory()
    for step in trajectory.steps:
        representation = next(
            rep
            for rep in trajectory.representations
            if rep.representation_id == step.representation_id
        )
        if step.step_id.startswith("restore_"):
            visible = set(representation.visible_components)
            assert "index_row" in visible
            assert "numbers_row" in visible
            if step.step_id != "restore_original_representation":
                assert "window_box" in visible


def test_unobserved_correct_s3_branch_fails_closed_in_historical_replay() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="restore_probe_s3",
    )
    with pytest.raises(ValueError, match="no unique route for outcome correct"):
        submit_response(trajectory, load_registry(), cursor, "14")
