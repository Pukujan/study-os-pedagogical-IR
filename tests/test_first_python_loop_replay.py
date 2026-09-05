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
        (FIXTURE_DIR / "trajectory.first-python-loop.v0.json").read_text()
    )


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(
        (FIXTURE_DIR / "assessments.first-python-loop.v0.json").read_text()
    )


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(
        (FIXTURE_DIR / "context.first-python-loop.v0.json").read_text()
    )


def render_until_blocked(cursor: ReplayCursor) -> ReplayCursor:
    trajectory = load_trajectory()
    current = cursor
    while current.phase == ReplayPhase.RENDER:
        build_renderer_contract(trajectory, current, load_context())
        current = mark_turn_rendered(trajectory, current)
    return current


def answer_and_render(cursor: ReplayCursor, response: str) -> ReplayCursor:
    result = submit_response(load_trajectory(), load_registry(), cursor, response)
    assert result.outcome == TrajectoryOutcomeKind.CORRECT
    return render_until_blocked(result.cursor)


def test_first_python_loop_fixture_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()


def test_first_window_probe_hides_expression_and_preserves_box() -> None:
    trajectory = load_trajectory()
    cursor = start_replay(trajectory, load_registry())
    contract = build_renderer_contract(trajectory, cursor, load_context())
    payload = contract.model_dump_json()
    rendered = render_turn_text(contract)
    assert contract.representation.box is not None
    assert contract.representation.box.start_index == 0
    assert contract.representation.box.width == 3
    assert "a[i] + a[i+1] + a[i+j]" not in payload
    assert "max_sum" not in rendered
    assert contract.forbidden_concepts == ("max_sum",)


def test_source_backed_loop_path_reaches_representation_restoration() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    assert cursor.current_step_id == "loop_first_window_probe"

    cursor = answer_and_render(cursor, "a[i] + a[i+1] + a[i+j]")
    assert cursor.current_step_id == "loop_boundary_probe"

    cursor = answer_and_render(cursor, "stop")
    assert cursor.current_step_id == "loop_break_probe"

    cursor = answer_and_render(cursor, "break")
    assert cursor.current_step_id == "loop_i3_probe"

    result = submit_response(load_trajectory(), load_registry(), cursor, "calculate s[3]")
    assert result.outcome == TrajectoryOutcomeKind.CORRECT
    cursor = render_until_blocked(result.cursor)
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "restore_representation_for_validation"


def test_later_window_expression_is_bridge_not_fake_assessment() -> None:
    trajectory = load_trajectory()
    registry = load_registry()
    assessed_steps = {spec.step_id for spec in registry.assessments}
    assert "loop_later_case_bridge" not in assessed_steps
    later_step = next(
        step for step in trajectory.steps if step.step_id == "loop_later_case_bridge"
    )
    assert later_step.probe is None
    assert "without claiming a new independent learner completion" in later_step.goal


def test_unobserved_wrong_boundary_response_fails_closed() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="loop_boundary_probe",
    )
    with pytest.raises(ValueError, match="no unique route for outcome incorrect"):
        submit_response(trajectory, load_registry(), cursor, "continue")
