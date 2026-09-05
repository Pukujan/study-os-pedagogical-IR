from __future__ import annotations

from pathlib import Path

import pytest

from study_os_pir.runtime import (
    AssessmentKind,
    AssessmentRegistry,
    AssessmentSpec,
    AssessmentViolationCode,
    ReplayCursor,
    ReplayPhase,
    build_renderer_contract,
    classify_response,
    mark_turn_rendered,
    start_replay,
    submit_response,
    validate_assessment_registry,
)
from study_os_pir.trajectory import ExperimentalTrajectory, TrajectoryOutcomeKind

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "sliding-window-foundations"
TRAJECTORY_PATH = FIXTURE_DIR / "trajectory.v0.json"
ASSESSMENT_PATH = FIXTURE_DIR / "assessments.v0.json"


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(TRAJECTORY_PATH.read_text())


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(ASSESSMENT_PATH.read_text())


def violation_codes(
    trajectory: ExperimentalTrajectory,
    registry: AssessmentRegistry,
) -> tuple[AssessmentViolationCode, ...]:
    return tuple(
        violation.code
        for violation in validate_assessment_registry(trajectory, registry)
    )


def cursor_at(
    trajectory: ExperimentalTrajectory,
    step_id: str | None,
    phase: ReplayPhase,
) -> ReplayCursor:
    return ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=phase,
        current_step_id=step_id,
    )


def render_until_blocked(
    trajectory: ExperimentalTrajectory,
    cursor: ReplayCursor,
) -> ReplayCursor:
    current = cursor
    while current.phase == ReplayPhase.RENDER:
        build_renderer_contract(trajectory, current)
        current = mark_turn_rendered(trajectory, current)
    return current


def answer_and_render(
    trajectory: ExperimentalTrajectory,
    registry: AssessmentRegistry,
    cursor: ReplayCursor,
    response: str,
) -> tuple[TrajectoryOutcomeKind, ReplayCursor]:
    result = submit_response(trajectory, registry, cursor, response)
    return result.outcome, render_until_blocked(trajectory, result.cursor)


def test_foundations_assessment_registry_is_valid() -> None:
    assert validate_assessment_registry(load_trajectory(), load_registry()) == ()


def test_registry_trajectory_mismatch_is_rejected() -> None:
    registry = load_registry().model_copy(update={"trajectory_id": "other"})
    assert AssessmentViolationCode.TRAJECTORY_ID_MISMATCH in violation_codes(
        load_trajectory(), registry
    )


def test_duplicate_assessment_step_is_rejected() -> None:
    registry = load_registry()
    duplicate = registry.assessments[0]
    mutated = registry.model_copy(
        update={"assessments": (*registry.assessments, duplicate)}
    )
    assert AssessmentViolationCode.DUPLICATE_ASSESSMENT_STEP in violation_codes(
        load_trajectory(), mutated
    )


def test_unknown_assessment_step_is_rejected() -> None:
    registry = load_registry()
    unknown = registry.assessments[0].model_copy(update={"step_id": "missing"})
    mutated = registry.model_copy(
        update={"assessments": (unknown, *registry.assessments[1:])}
    )
    codes = violation_codes(load_trajectory(), mutated)
    assert AssessmentViolationCode.UNKNOWN_ASSESSMENT_STEP in codes
    assert AssessmentViolationCode.MISSING_PROBE_ASSESSMENT in codes


def test_assessment_for_non_probe_is_rejected() -> None:
    registry = load_registry()
    non_probe = registry.assessments[0].model_copy(update={"step_id": "problem_anchor"})
    mutated = registry.model_copy(
        update={"assessments": (non_probe, *registry.assessments[1:])}
    )
    assert AssessmentViolationCode.ASSESSMENT_FOR_NON_PROBE in violation_codes(
        load_trajectory(), mutated
    )


def test_missing_probe_assessment_is_rejected() -> None:
    registry = load_registry()
    mutated = registry.model_copy(update={"assessments": registry.assessments[1:]})
    assert AssessmentViolationCode.MISSING_PROBE_ASSESSMENT in violation_codes(
        load_trajectory(), mutated
    )


def test_integer_assessment_requires_exactly_one_expected_value() -> None:
    registry = load_registry()
    bad = registry.assessments[0].model_copy(update={"expected_values": (4, 5)})
    mutated = registry.model_copy(
        update={"assessments": (bad, *registry.assessments[1:])}
    )
    assert AssessmentViolationCode.INVALID_INTEGER_ASSESSMENT in violation_codes(
        load_trajectory(), mutated
    )


def test_integer_response_classification_is_deterministic() -> None:
    spec = AssessmentSpec(
        step_id="probe",
        kind=AssessmentKind.INTEGER,
        expected_values=(4,),
    )
    assert classify_response(spec, " 4 ") == TrajectoryOutcomeKind.CORRECT
    assert classify_response(spec, "+4") == TrajectoryOutcomeKind.CORRECT
    assert classify_response(spec, "5") == TrajectoryOutcomeKind.INCORRECT
    with pytest.raises(ValueError, match="single integer"):
        classify_response(spec, "four")


@pytest.mark.parametrize(
    "response",
    ["4 7 2", "4,7,2", "[4, 7, 2]", "(4 7 2)"],
)
def test_integer_sequence_accepts_supported_local_input_forms(response: str) -> None:
    spec = AssessmentSpec(
        step_id="probe",
        kind=AssessmentKind.INTEGER_SEQUENCE,
        expected_values=(4, 7, 2),
    )
    assert classify_response(spec, response) == TrajectoryOutcomeKind.CORRECT


def test_integer_sequence_wrong_value_is_incorrect() -> None:
    spec = AssessmentSpec(
        step_id="probe",
        kind=AssessmentKind.INTEGER_SEQUENCE,
        expected_values=(4, 7, 2),
    )
    assert classify_response(spec, "4 7 3") == TrajectoryOutcomeKind.INCORRECT


def test_integer_sequence_empty_or_text_input_fails_closed() -> None:
    spec = AssessmentSpec(
        step_id="probe",
        kind=AssessmentKind.INTEGER_SEQUENCE,
        expected_values=(4, 7, 2),
    )
    with pytest.raises(ValueError, match="does not contain"):
        classify_response(spec, "[]")
    with pytest.raises(ValueError, match="supported integer sequence"):
        classify_response(spec, "4 seven 2")


def test_start_replay_rejects_invalid_trajectory() -> None:
    trajectory = load_trajectory().model_copy(update={"entry_step_id": "missing"})
    with pytest.raises(ValueError, match="invalid trajectory"):
        start_replay(trajectory, load_registry())


def test_start_replay_rejects_invalid_registry() -> None:
    registry = load_registry().model_copy(update={"trajectory_id": "other"})
    with pytest.raises(ValueError, match="invalid assessment registry"):
        start_replay(load_trajectory(), registry)


def test_start_replay_begins_at_renderer_safe_problem_anchor() -> None:
    trajectory = load_trajectory()
    cursor = start_replay(trajectory, load_registry())
    assert cursor.phase == ReplayPhase.RENDER
    assert cursor.current_step_id == "problem_anchor"
    assert cursor.visited_step_ids == ()
    contract = build_renderer_contract(trajectory, cursor)
    assert contract.step_id == "problem_anchor"
    assert contract.probe is None


def test_renderer_contract_for_probe_excludes_assessment_oracle() -> None:
    trajectory = load_trajectory()
    cursor = render_until_blocked(
        trajectory,
        start_replay(trajectory, load_registry()),
    )
    assert cursor.current_step_id == "position_probe6"
    render_cursor = cursor.model_copy(update={"phase": ReplayPhase.RENDER})
    contract = build_renderer_contract(trajectory, render_cursor)
    payload = contract.model_dump_json()
    assert contract.probe is not None
    assert contract.probe.prompt == "What is position(p) of number(a) 6?"
    assert "expected_values" not in payload
    assert "forbidden_answer_literals" not in payload
    assert "p = 4" not in payload


def test_renderer_contract_requires_render_phase() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "position_probe6", ReplayPhase.AWAIT_RESPONSE)
    with pytest.raises(ValueError, match="only in render phase"):
        build_renderer_contract(trajectory, cursor)


def test_cursor_trajectory_mismatch_fails() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id="other",
        phase=ReplayPhase.RENDER,
        current_step_id="problem_anchor",
    )
    with pytest.raises(ValueError, match="does not match"):
        build_renderer_contract(trajectory, cursor)


def test_cursor_without_current_step_fails() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, None, ReplayPhase.RENDER)
    with pytest.raises(ValueError, match="no current step"):
        build_renderer_contract(trajectory, cursor)


def test_cursor_with_unknown_step_fails() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "missing", ReplayPhase.RENDER)
    with pytest.raises(ValueError, match="unknown step"):
        build_renderer_contract(trajectory, cursor)


def test_marking_non_probe_render_advances_one_step_only() -> None:
    trajectory = load_trajectory()
    cursor = start_replay(trajectory, load_registry())
    cursor = mark_turn_rendered(trajectory, cursor)
    assert cursor.phase == ReplayPhase.RENDER
    assert cursor.current_step_id == "position_intro"
    assert cursor.visited_step_ids == ("problem_anchor",)


def test_marking_probe_render_waits_for_response_without_advancing() -> None:
    trajectory = load_trajectory()
    cursor = render_until_blocked(
        trajectory,
        start_replay(trajectory, load_registry()),
    )
    assert cursor.phase == ReplayPhase.AWAIT_RESPONSE
    assert cursor.current_step_id == "position_probe6"
    assert cursor.visited_step_ids[-1] == "position_probe6"


def test_mark_turn_rendered_rejects_wrong_phase() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "position_probe6", ReplayPhase.AWAIT_RESPONSE)
    with pytest.raises(ValueError, match="only in render phase"):
        mark_turn_rendered(trajectory, cursor)


def test_non_probe_without_unique_auto_transition_fails_at_runtime() -> None:
    trajectory = load_trajectory()
    mutated = trajectory.model_copy(
        update={
            "automatic_transitions": tuple(
                transition
                for transition in trajectory.automatic_transitions
                if transition.from_step_id != "problem_anchor"
            )
        }
    )
    cursor = cursor_at(mutated, "problem_anchor", ReplayPhase.RENDER)
    with pytest.raises(ValueError, match="exactly one automatic transition"):
        mark_turn_rendered(mutated, cursor)


def test_runtime_transition_without_any_target_fails_closed() -> None:
    trajectory = load_trajectory()
    first = trajectory.automatic_transitions[0].model_copy(
        update={"next_step_id": None, "exit_target": None}
    )
    mutated = trajectory.model_copy(
        update={"automatic_transitions": (first, *trajectory.automatic_transitions[1:])}
    )
    cursor = cursor_at(mutated, "problem_anchor", ReplayPhase.RENDER)
    with pytest.raises(ValueError, match="has no target"):
        mark_turn_rendered(mutated, cursor)


def test_final_non_probe_can_exit_to_next_compiled_slice() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "k_validate5", ReplayPhase.RENDER)
    cursor = mark_turn_rendered(trajectory, cursor)
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.current_step_id is None
    assert cursor.exit_target == "i_moves_box"
    assert cursor.visited_step_ids == ("k_validate5",)


def test_submit_response_rejects_wrong_phase() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "position_probe6", ReplayPhase.RENDER)
    with pytest.raises(ValueError, match="only while awaiting"):
        submit_response(trajectory, load_registry(), cursor, "4")


def test_awaiting_cursor_must_point_to_probe() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "problem_anchor", ReplayPhase.AWAIT_RESPONSE)
    with pytest.raises(ValueError, match="does not point to a probe"):
        submit_response(trajectory, load_registry(), cursor, "4")


def test_probe_without_runtime_assessment_fails_closed() -> None:
    trajectory = load_trajectory()
    registry = load_registry()
    registry = registry.model_copy(update={"assessments": registry.assessments[1:]})
    cursor = cursor_at(trajectory, "position_probe6", ReplayPhase.AWAIT_RESPONSE)
    with pytest.raises(ValueError, match="no runtime assessment"):
        submit_response(trajectory, registry, cursor, "4")


def test_correct_response_routes_to_same_chart_validation() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "position_probe6", ReplayPhase.AWAIT_RESPONSE)
    result = submit_response(trajectory, load_registry(), cursor, "4")
    assert result.outcome == TrajectoryOutcomeKind.CORRECT
    assert result.cursor.phase == ReplayPhase.RENDER
    assert result.cursor.current_step_id == "position_validate6_correct"
    assert result.cursor.outcomes == (TrajectoryOutcomeKind.CORRECT,)


def test_wrong_response_routes_to_correction_before_retry() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "position_probe6", ReplayPhase.AWAIT_RESPONSE)
    result = submit_response(trajectory, load_registry(), cursor, "9")
    assert result.outcome == TrajectoryOutcomeKind.INCORRECT
    assert result.cursor.current_step_id == "position_correct6_wrong"


def test_unmodeled_repeated_error_fails_instead_of_inventing_route() -> None:
    trajectory = load_trajectory()
    cursor = cursor_at(trajectory, "position_retry9", ReplayPhase.AWAIT_RESPONSE)
    with pytest.raises(ValueError, match="no unique route for outcome incorrect"):
        submit_response(trajectory, load_registry(), cursor, "5")


def test_probe_outcome_can_exit_when_route_explicitly_says_so() -> None:
    trajectory = load_trajectory()
    routes = tuple(
        route.model_copy(
            update={"next_step_id": None, "exit_target": "done"}
        )
        if (
            route.after_step_id == "position_probe6"
            and route.outcome == TrajectoryOutcomeKind.CORRECT
        )
        else route
        for route in trajectory.outcome_routes
    )
    mutated = trajectory.model_copy(update={"outcome_routes": routes})
    cursor = cursor_at(mutated, "position_probe6", ReplayPhase.AWAIT_RESPONSE)
    result = submit_response(mutated, load_registry(), cursor, "4")
    assert result.cursor.phase == ReplayPhase.EXITED
    assert result.cursor.exit_target == "done"
    assert result.cursor.outcomes == (TrajectoryOutcomeKind.CORRECT,)


def test_real_wrong_then_recovery_path_runs_from_actual_text_inputs() -> None:
    trajectory = load_trajectory()
    registry = load_registry()
    cursor = render_until_blocked(trajectory, start_replay(trajectory, registry))

    expected = (
        ("9", TrajectoryOutcomeKind.INCORRECT, "position_retry9"),
        ("6", TrajectoryOutcomeKind.CORRECT, "position_confirm7"),
        ("2", TrajectoryOutcomeKind.CORRECT, "index_probe6"),
        ("3", TrajectoryOutcomeKind.CORRECT, "index_probe9"),
        ("5", TrajectoryOutcomeKind.CORRECT, "k_probe3_guided"),
        ("4 7 2", TrajectoryOutcomeKind.CORRECT, "k_probe5_unassisted"),
    )
    for response, expected_outcome, expected_probe in expected:
        outcome, cursor = answer_and_render(
            trajectory,
            registry,
            cursor,
            response,
        )
        assert outcome == expected_outcome
        assert cursor.current_step_id == expected_probe
        assert cursor.phase == ReplayPhase.AWAIT_RESPONSE

    outcome, cursor = answer_and_render(
        trajectory,
        registry,
        cursor,
        "4,7,2,6,1",
    )
    assert outcome == TrajectoryOutcomeKind.CORRECT
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "i_moves_box"
    assert "position_correct6_wrong" in cursor.visited_step_ids
    assert "position_retry9" in cursor.visited_step_ids
    assert cursor.outcomes[0] == TrajectoryOutcomeKind.INCORRECT
    assert cursor.outcomes[1:] == (TrajectoryOutcomeKind.CORRECT,) * 6


def test_real_all_correct_path_skips_error_only_steps() -> None:
    trajectory = load_trajectory()
    registry = load_registry()
    cursor = render_until_blocked(trajectory, start_replay(trajectory, registry))
    for response in ("4", "2", "3", "5", "4 7 2", "4 7 2 6 1"):
        _, cursor = answer_and_render(trajectory, registry, cursor, response)
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "i_moves_box"
    assert "position_correct6_wrong" not in cursor.visited_step_ids
    assert "position_retry9" not in cursor.visited_step_ids
