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
        (FIXTURE_DIR / "trajectory.largest-window-sum.v0.json").read_text()
    )


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(
        (FIXTURE_DIR / "assessments.largest-window-sum.v0.json").read_text()
    )


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(
        (FIXTURE_DIR / "context.largest-window-sum.v0.json").read_text()
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


def test_largest_window_sum_fixture_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()


def test_location_and_value_are_separate_gates() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    assert cursor.current_step_id == "largest_locations_probe"

    outcome, cursor = answer_and_render(cursor, "s1 and s3")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "largest_value_probe"

    outcome, cursor = answer_and_render(cursor, "13")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "changed_location_probe"

    outcome, cursor = answer_and_render(cursor, "s1")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "changed_value_probe"

    outcome, cursor = answer_and_render(cursor, "14")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "max_sum_retry_probe"


def test_repaired_max_sum_probe_does_not_reveal_answer() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id="max_sum_retry_probe",
    )
    contract = build_renderer_contract(trajectory, cursor, load_context())
    rendered = render_turn_text(contract)

    assert "S: 10 7 15 9" in rendered
    assert "max_sum = max(S)" in rendered
    assert "max_sum = 15" not in rendered
    assert "max(S) = 15" not in rendered
    assert "S[2] = 15" not in rendered


def test_changed_retry_and_verification_unlock_incremental_initialization() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="max_sum_retry_probe",
    )

    outcome, cursor = answer_and_render(cursor, "15")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "max_sum_verify_probe"

    outcome, cursor = answer_and_render(cursor, "11")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "max_sum_s0_initialization"


def test_incremental_max_tracking_is_forbidden_before_exit() -> None:
    trajectory = load_trajectory()
    assert all("incremental_max_tracking" in step.forbidden_concepts for step in trajectory.steps)


def test_unobserved_wrong_retry_fails_closed() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="max_sum_retry_probe",
    )
    with pytest.raises(ValueError, match="no unique route for outcome incorrect"):
        submit_response(trajectory, load_registry(), cursor, "9")
