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
FIXTURE_DIR = ROOT / "fixtures" / "public" / "max-sum-loop"


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


def test_max_loop_fixture_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()


def test_fixed_index_then_symbolic_comparison_precedes_loop_construction() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    assert cursor.current_step_id == "fixed_index_probe_i2"

    outcome, cursor = answer_and_render(
        cursor,
        "if s[2] > max_sum:\n max_sum = s[2]",
    )
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert "symbolic_bridge_i2" in cursor.visited_step_ids
    assert cursor.current_step_id == "symbolic_probe_i3"

    outcome, cursor = answer_and_render(
        cursor,
        "if s[i] > max_sum:\nmax_sum=s[i]",
    )
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "max_loop_enumerate_probe"


def test_reversed_condition_routes_through_correction_and_retry() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="max_loop_condition_probe",
    )

    outcome, cursor = answer_and_render(cursor, "if max_sum>s[i]")
    assert outcome == TrajectoryOutcomeKind.INCORRECT
    assert "max_loop_condition_correction" in cursor.visited_step_ids
    assert cursor.current_step_id == "max_loop_condition_retry"

    outcome, cursor = answer_and_render(cursor, "if S[i] > max_sum:")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "max_loop_full_probe"


def test_full_loop_body_without_initialization_is_partial_not_wrong() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="max_loop_full_probe",
    )
    body_only = """for i, num in enumerate(S):
 if S[i] > max_sum:
  max_sum=s[i]"""

    outcome, cursor = answer_and_render(cursor, body_only)
    assert outcome == TrajectoryOutcomeKind.PARTIAL
    assert "max_loop_missing_init_explain" in cursor.visited_step_ids
    assert cursor.current_step_id == "max_loop_init_probe"

    outcome, cursor = answer_and_render(cursor, "max_sum = s[0]")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "combine_window_and_max_loops"
    assert cursor.outcomes[-2:] == (
        TrajectoryOutcomeKind.PARTIAL,
        TrajectoryOutcomeKind.CORRECT,
    )


def test_probe_renderer_contracts_do_not_contain_assessment_oracles() -> None:
    trajectory = load_trajectory()
    for step_id in (
        "fixed_index_probe_i2",
        "symbolic_probe_i3",
        "max_loop_condition_retry",
        "max_loop_full_probe",
        "max_loop_init_probe",
    ):
        cursor = ReplayCursor(
            schema_version="pir.replay-cursor.v0",
            trajectory_id=trajectory.trajectory_id,
            phase=ReplayPhase.RENDER,
            current_step_id=step_id,
        )
        contract = build_renderer_contract(trajectory, cursor, load_context())
        payload = contract.model_dump_json()
        assert "expected_text" not in payload
        assert "partial_text" not in payload

    full_cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id="max_loop_full_probe",
    )
    full_text = render_turn_text(build_renderer_contract(trajectory, full_cursor, load_context()))
    assert "for i, num in enumerate(S):" not in full_text
    assert "if S[i] > max_sum:" not in full_text
    assert "max_sum = S[0]" not in full_text


def test_complete_unobserved_full_loop_response_fails_closed() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="max_loop_full_probe",
    )
    complete = """max_sum = S[0]
for i, num in enumerate(S):
    if S[i] > max_sum:
        max_sum = S[i]"""
    with pytest.raises(ValueError, match="no unique route for outcome correct"):
        submit_response(trajectory, load_registry(), cursor, complete)


def test_combined_loop_is_forbidden_until_standalone_loop_is_complete() -> None:
    trajectory = load_trajectory()
    assert all("combined_loop" in step.forbidden_concepts for step in trajectory.steps)
