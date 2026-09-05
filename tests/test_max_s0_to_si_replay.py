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
FIXTURE_DIR = ROOT / "fixtures" / "public" / "max-sum-s0-to-si"


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(
        (FIXTURE_DIR / "trajectory.replay.v0.json").read_text()
    )


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(
        (FIXTURE_DIR / "assessments.replay.v0.json").read_text()
    )


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(
        (FIXTURE_DIR / "context.replay.v0.json").read_text()
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


def test_max_s0_to_si_replay_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()


def test_value_must_be_validated_before_s0_code() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    assert cursor.current_step_id == "probe_first_window_value"

    outcome, cursor = answer_and_render(cursor, "11")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert "validate_first_window_value" in cursor.visited_step_ids
    assert cursor.current_step_id == "probe_s0_assignment"


def test_si_probe_uses_hint_without_leaking_target_assignment() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id="probe_si_assignment",
    )
    contract = build_renderer_contract(trajectory, cursor, load_context())
    rendered = render_turn_text(contract)

    assert "S[0] and S[i] refer to the same entry" in rendered
    assert "max_sum = S[i]" not in rendered
    assert contract.representation.box is not None
    assert contract.representation.box.start_index == 0


def test_source_backed_path_reaches_first_comparison_before_code() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))

    outcome, cursor = answer_and_render(cursor, "11")
    assert outcome == TrajectoryOutcomeKind.CORRECT

    outcome, cursor = answer_and_render(cursor, "max_sum = s[0]")
    assert outcome == TrajectoryOutcomeKind.CORRECT

    outcome, cursor = answer_and_render(cursor, "max_sum = s[i]")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "probe_first_comparison"

    outcome, cursor = answer_and_render(cursor, "yes")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "max_sum_fixed_index_condition"


def test_comparison_code_remains_forbidden_until_exit() -> None:
    trajectory = load_trajectory()
    assert all("comparison_code" in step.forbidden_concepts for step in trajectory.steps)


def test_unobserved_wrong_si_assignment_fails_closed() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="probe_si_assignment",
    )
    with pytest.raises(ValueError, match="no unique route for outcome incorrect"):
        submit_response(trajectory, load_registry(), cursor, "max_sum = S[0]")
