from __future__ import annotations

from pathlib import Path

from study_os_pir.console import render_turn_text
from study_os_pir.runtime import (
    AssessmentKind,
    AssessmentRegistry,
    AssessmentSpec,
    AssessmentViolationCode,
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
from study_os_pir.trajectory import (
    ExperimentalTrajectory,
    TrajectoryOutcomeKind,
    validate_trajectory,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "public" / "sliding-window-foundations"


def load_trajectory() -> ExperimentalTrajectory:
    return ExperimentalTrajectory.model_validate_json(
        (FIXTURE_DIR / "trajectory.enumerate-append.v0.json").read_text()
    )


def load_registry() -> AssessmentRegistry:
    return AssessmentRegistry.model_validate_json(
        (FIXTURE_DIR / "assessments.enumerate-append.v0.json").read_text()
    )


def load_context() -> ReplayContext:
    return ReplayContext.model_validate_json(
        (FIXTURE_DIR / "context.enumerate-append.v0.json").read_text()
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


def test_enumerate_append_fixture_is_runtime_valid() -> None:
    trajectory = load_trajectory()
    assert validate_trajectory(trajectory) == ()
    assert validate_assessment_registry(trajectory, load_registry()) == ()


def test_text_assessment_is_whitespace_tolerant_but_case_sensitive() -> None:
    spec = AssessmentSpec(
        step_id="append",
        kind=AssessmentKind.TEXT,
        expected_text=("S.append(S[i-1] + a[i])",),
    )
    assert (
        classify_response(spec, " S.append( S[i-1] + a[i] ) ")
        == TrajectoryOutcomeKind.CORRECT
    )
    assert classify_response(spec, "s.append(S[i-1] + a[i])") == TrajectoryOutcomeKind.INCORRECT


def test_renderer_contract_never_exposes_expected_text_or_pair_oracle() -> None:
    trajectory = load_trajectory()
    registry_payload = load_registry().model_dump_json()
    assert "S.append(S[i-1] + a[i])" in registry_payload

    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id="append_probe_simple",
    )
    contract = build_renderer_contract(trajectory, cursor, load_context())
    payload = contract.model_dump_json()
    assert "expected_text" not in payload
    assert "expected_values" not in payload
    assert "S.append(S[i-1] + a[i])" not in payload

    pair_cursor = cursor.model_copy(update={"current_step_id": "enumerate_probe6"})
    pair_payload = build_renderer_contract(
        trajectory, pair_cursor, load_context()
    ).model_dump_json()
    assert "(3,6)" not in pair_payload


def test_full_source_backed_path_reaches_first_python_window_loop() -> None:
    cursor = render_until_blocked(start_replay(load_trajectory(), load_registry()))
    assert cursor.current_step_id == "enumerate_probe6"

    cursor = answer_and_render(cursor, "3,6")
    assert cursor.current_step_id == "enumerate_probe7_changed"

    cursor = answer_and_render(cursor, "4 7")
    assert cursor.current_step_id == "append_probe_simple"
    assert "S.append(S[i-1] + a[i])" not in render_turn_text(
        build_renderer_contract(load_trajectory(), cursor, load_context())
    )

    cursor = answer_and_render(cursor, "S.append( S[i-1] + a[i] )")
    assert cursor.current_step_id == "append_probe_changed"

    result = submit_response(
        load_trajectory(),
        load_registry(),
        cursor,
        "S.append(S[i-1] - a[i-1] + a[i+2])",
    )
    assert result.outcome == TrajectoryOutcomeKind.CORRECT
    cursor = render_until_blocked(result.cursor)
    assert cursor.phase == ReplayPhase.EXITED
    assert cursor.exit_target == "first_python_window_loop"


def test_unobserved_wrong_append_answer_fails_closed() -> None:
    trajectory = load_trajectory()
    cursor = ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.AWAIT_RESPONSE,
        current_step_id="append_probe_simple",
    )
    try:
        submit_response(trajectory, load_registry(), cursor, "S[i] = S[i-1] + a[i]")
    except ValueError as error:
        assert "no unique route for outcome incorrect" in str(error)
    else:
        raise AssertionError("unobserved wrong append path must fail closed")


def _registry_with_replacement(replacement: AssessmentSpec) -> AssessmentRegistry:
    registry = load_registry()
    assessments = tuple(
        replacement if spec.step_id == replacement.step_id else spec
        for spec in registry.assessments
    )
    return registry.model_copy(update={"assessments": assessments})


def test_invalid_integer_sequence_assessment_is_rejected() -> None:
    replacement = AssessmentSpec(
        step_id="enumerate_probe6",
        kind=AssessmentKind.INTEGER_SEQUENCE,
    )
    violations = validate_assessment_registry(
        load_trajectory(), _registry_with_replacement(replacement)
    )
    assert AssessmentViolationCode.INVALID_INTEGER_SEQUENCE_ASSESSMENT in {
        violation.code for violation in violations
    }


def test_invalid_text_assessment_payload_is_rejected() -> None:
    replacement = AssessmentSpec(
        step_id="append_probe_simple",
        kind=AssessmentKind.TEXT,
        expected_values=(1,),
    )
    violations = validate_assessment_registry(
        load_trajectory(), _registry_with_replacement(replacement)
    )
    assert AssessmentViolationCode.INVALID_TEXT_ASSESSMENT in {
        violation.code for violation in violations
    }


def test_integer_assessment_cannot_carry_text_oracle() -> None:
    replacement = AssessmentSpec(
        step_id="enumerate_probe6",
        kind=AssessmentKind.INTEGER,
        expected_values=(3,),
        expected_text=("3",),
    )
    violations = validate_assessment_registry(
        load_trajectory(), _registry_with_replacement(replacement)
    )
    assert AssessmentViolationCode.INVALID_INTEGER_ASSESSMENT in {
        violation.code for violation in violations
    }
