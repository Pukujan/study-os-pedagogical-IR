from __future__ import annotations

from pathlib import Path

import pytest

from study_os_pir.console import render_turn_text
from study_os_pir.language import LexicalRegister, validate_lexical_register
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
        (FIXTURE_DIR / "trajectory.successive-sums.v0.json").read_text()
    )


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(
        (FIXTURE_DIR / "assessments.successive-sums.v0.json").read_text()
    )


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(
        (FIXTURE_DIR / "context.successive-sums.v0.json").read_text()
    )


def load_lexical_register() -> LexicalRegister:
    return LexicalRegister.model_validate_json(
        (FIXTURE_DIR / "register.beginner-grounded.v0.json").read_text()
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


def test_successive_sums_fixture_is_runtime_and_lexically_valid() -> None:
    trajectory = load_trajectory()
    context = load_context()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()
    assert (
        validate_lexical_register(
            trajectory,
            load_lexical_register(),
            persistent_text=context.persistent_text,
        )
        == ()
    )


def test_first_successive_sum_turn_keeps_problem_array_and_both_boxes_visible() -> None:
    trajectory = load_trajectory()
    contract = build_renderer_contract(
        trajectory,
        start_replay(trajectory, load_registry()),
        load_context(),
    )
    text = render_turn_text(contract)
    assert text.startswith(
        "Given an array of numbers, find the maximum sum of any 3 consecutive numbers."
    )
    assert "numbers(a)" in text
    assert "sum[i]" in text
    assert "sum[i+1]" in text
    assert text.count("^^^^^") == 6
    assert "general recurrence" not in text.lower()


def test_correct_path_replays_successive_sums_then_recurrence_then_exits() -> None:
    trajectory = load_trajectory()
    cursor = render_until_blocked(start_replay(trajectory, load_registry()))
    assert cursor.current_step_id == "successive_probe_i1"

    scripted = (
        ("14", "successive_probe_i2"),
        ("8", "successive_probe_i3"),
        ("14", "successive_i_delta_probe"),
        ("1", "recurrence_three_values_probe"),
    )
    for response, expected_step in scripted:
        outcome, cursor = answer_and_render(cursor, response)
        assert outcome == TrajectoryOutcomeKind.CORRECT
        assert cursor.current_step_id == expected_step
        assert cursor.phase == ReplayPhase.AWAIT_RESPONSE

    result = submit_response(trajectory, load_registry(), cursor, "14 8 14")
    assert result.outcome == TrajectoryOutcomeKind.CORRECT
    cursor = mark_turn_rendered(trajectory, result.cursor)
    cursor = mark_turn_rendered(trajectory, cursor)
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "python_translation"


def test_recurrence_probe_keeps_problem_chart_and_hides_oracle_answers() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id="recurrence_three_values_probe",
    )
    contract = build_renderer_contract(trajectory, cursor, load_context())
    payload = contract.model_dump_json()
    text = render_turn_text(contract)
    assert "numbers(a)" in text
    assert "Formula: S[i] = S[i-1] - a[i-1] + a[i+j]" in text
    assert "What are S[1], S[2], and S[3]?" in text
    assert "expected_values" not in payload
    assert "S[1] = 14" not in text
    assert "S[2] = 8" not in text
    assert "S[3] = 14" not in text


def test_source_backed_bridges_precede_general_recurrence_and_loop_exit() -> None:
    trajectory = load_trajectory()
    step_ids = tuple(step.step_id for step in trajectory.steps)
    recurrence_index = step_ids.index("recurrence_formula_bridge")
    assert step_ids.index("successive_probe_i1") < recurrence_index
    assert step_ids.index("successive_probe_i2") < recurrence_index
    assert step_ids.index("successive_probe_i3") < recurrence_index
    assert step_ids.index("successive_i_delta_validate") < recurrence_index
    assert step_ids.index("recurrence_three_values_validate") < step_ids.index(
        "recurrence_repetition_bridge"
    )


def test_detached_wrong_answer_has_no_invented_retry_policy() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="successive_probe_i2",
    )
    with pytest.raises(ValueError, match="no unique route for outcome incorrect"):
        submit_response(trajectory, load_registry(), cursor, "9")
