from __future__ import annotations

from pathlib import Path

import pytest

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
FIXTURE_DIR = ROOT / "fixtures" / "public" / "combined-loop"


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


def test_combined_loop_fixture_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()


def test_first_box_combination_reaches_else_bridge_before_later_box_probe() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    assert cursor.current_step_id == "first_box_combine_probe"

    response = """S.append(a[i] + a[i+1] + a[i+j])
max_sum = s[i]"""
    outcome, cursor = answer_and_render(cursor, response)
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert "else_bridge_explain" in cursor.visited_step_ids
    assert cursor.current_step_id == "later_box_full_probe"


def test_correct_later_box_skips_append_repair() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="later_box_full_probe",
    )
    response = """S.append(S[i-1] - a[i-1] + a[i+j])
if S[i] > max_sum:
    max_sum = S[i]"""

    outcome, cursor = answer_and_render(cursor, response)
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert "append_conversion_correction" not in cursor.visited_step_ids
    assert cursor.current_step_id == "len_probe"


def test_source_shaped_append_error_is_partial_and_repairs_only_append() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="later_box_full_probe",
    )
    source_shorthand = """s.append(si -1 - ai-1 - ai+j
if s i > max sum:
max sum = s i"""

    outcome, cursor = answer_and_render(cursor, source_shorthand)
    assert outcome == TrajectoryOutcomeKind.PARTIAL
    assert "append_conversion_correction" in cursor.visited_step_ids
    assert cursor.current_step_id == "append_retry_probe"

    outcome, cursor = answer_and_render(
        cursor,
        "S.append(S[i-1] - a[i-1] + a[i+j])",
    )
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "full_else_redo_probe"

    full_else = """else:
    S.append(S[i-1] - a[i-1] + a[i+j])
    if S[i] > max_sum:
        max_sum = S[i]"""
    outcome, cursor = answer_and_render(cursor, full_else)
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "len_probe"


def test_len_boundary_and_break_path_exits_to_arbitrary_k_slice() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="len_probe",
    )

    outcome, cursor = answer_and_render(cursor, "5")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "last_valid_probe"

    outcome, cursor = answer_and_render(cursor, "2")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.current_step_id == "past_last_probe"

    outcome, cursor = answer_and_render(cursor, "yes")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert "break_bridge_explain" in cursor.visited_step_ids
    assert cursor.current_step_id == "break_code_probe"

    outcome, cursor = answer_and_render(cursor, "if i > len(a) -k:\n break")
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "arbitrary_k_first_window"


def test_probe_contracts_hide_assessment_oracles() -> None:
    trajectory = load_trajectory()
    for step_id in (
        "first_box_combine_probe",
        "later_box_full_probe",
        "append_retry_probe",
        "full_else_redo_probe",
        "break_code_probe",
    ):
        cursor = ReplayCursor(
            schema_version="pir.replay-cursor.v0",
            trajectory_id=trajectory.trajectory_id,
            phase=ReplayPhase.RENDER,
            current_step_id=step_id,
        )
        payload = build_renderer_contract(
            trajectory,
            cursor,
            load_context(),
        ).model_dump_json()
        assert "expected_text" not in payload
        assert "partial_text" not in payload


def test_arbitrary_k_machinery_is_forbidden_until_boundary_slice_exits() -> None:
    trajectory = load_trajectory()
    for step in trajectory.steps:
        assert "arbitrary_k_first_window" in step.forbidden_concepts
        assert "range_k" in step.forbidden_concepts
        assert "x_loop" in step.forbidden_concepts


def test_unmodeled_later_box_error_fails_closed() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="later_box_full_probe",
    )
    with pytest.raises(ValueError, match="no unique route for outcome incorrect"):
        submit_response(trajectory, load_registry(), cursor, "else: pass")
