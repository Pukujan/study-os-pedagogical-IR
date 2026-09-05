from __future__ import annotations

from study_os_pir.runtime import (
    AssessmentKind,
    AssessmentRegistry,
    AssessmentSpec,
    AssessmentViolationCode,
    classify_response,
    validate_assessment_registry,
)
from study_os_pir.trajectory import (
    ExperimentalTrajectory,
    OutcomeRoute,
    TrajectoryOutcomeKind,
    TrajectoryStep,
)
from study_os_pir.vertical import (
    VerticalProbe,
    VerticalRepresentation,
    VerticalRow,
    VerticalStepKind,
)


def make_trajectory() -> ExperimentalTrajectory:
    representation = VerticalRepresentation(
        representation_id="r",
        rows=(VerticalRow(row_id="code", label="code", values=("blank",)),),
        visible_components=("code",),
    )
    step = TrajectoryStep(
        step_id="probe",
        kind=VerticalStepKind.PROBE,
        goal="test partial text",
        representation_id="r",
        active_delta="classify exact text",
        probe=VerticalProbe(
            target="code",
            prompt="write code",
            answer_reveal_allowed=False,
        ),
        evidence_turn_refs=("synthetic:test",),
    )
    return ExperimentalTrajectory(
        schema_version="pir.experimental-trajectory.v0",
        trajectory_id="synthetic.partial-text.v0",
        source_locator="synthetic:test",
        entry_step_id="probe",
        representations=(representation,),
        steps=(step,),
        outcome_routes=(
            OutcomeRoute(
                route_id="partial",
                after_step_id="probe",
                outcome=TrajectoryOutcomeKind.PARTIAL,
                exit_target="partial",
                evidence_turn_refs=("synthetic:test",),
            ),
        ),
    )


def test_text_assessment_classifies_exact_partial_alternative() -> None:
    spec = AssessmentSpec(
        step_id="probe",
        kind=AssessmentKind.TEXT,
        expected_text=("max_sum = S[0]\nfor i, num in enumerate(S): pass",),
        partial_text=("for i, num in enumerate(S): pass",),
    )
    assert (
        classify_response(spec, "for i, num in enumerate(S):\n    pass")
        == TrajectoryOutcomeKind.PARTIAL
    )
    assert (
        classify_response(spec, "max_sum = S[0]\nfor i, num in enumerate(S): pass")
        == TrajectoryOutcomeKind.CORRECT
    )
    assert classify_response(spec, "something else") == TrajectoryOutcomeKind.INCORRECT


def test_partial_text_is_rejected_for_integer_assessment() -> None:
    trajectory = make_trajectory()
    registry = AssessmentRegistry(
        schema_version="pir.experimental-assessment-registry.v0",
        trajectory_id=trajectory.trajectory_id,
        assessments=(
            AssessmentSpec(
                step_id="probe",
                kind=AssessmentKind.INTEGER,
                expected_values=(1,),
                partial_text=("one",),
            ),
        ),
    )
    codes = tuple(v.code for v in validate_assessment_registry(trajectory, registry))
    assert AssessmentViolationCode.INVALID_INTEGER_ASSESSMENT in codes


def test_partial_text_is_rejected_for_integer_sequence_assessment() -> None:
    trajectory = make_trajectory()
    registry = AssessmentRegistry(
        schema_version="pir.experimental-assessment-registry.v0",
        trajectory_id=trajectory.trajectory_id,
        assessments=(
            AssessmentSpec(
                step_id="probe",
                kind=AssessmentKind.INTEGER_SEQUENCE,
                expected_values=(1, 2),
                partial_text=("one two",),
            ),
        ),
    )
    codes = tuple(v.code for v in validate_assessment_registry(trajectory, registry))
    assert AssessmentViolationCode.INVALID_INTEGER_SEQUENCE_ASSESSMENT in codes


def test_text_assessment_still_rejects_numeric_partial_values() -> None:
    trajectory = make_trajectory()
    registry = AssessmentRegistry(
        schema_version="pir.experimental-assessment-registry.v0",
        trajectory_id=trajectory.trajectory_id,
        assessments=(
            AssessmentSpec(
                step_id="probe",
                kind=AssessmentKind.TEXT,
                expected_text=("one",),
                partial_values=(1,),
            ),
        ),
    )
    codes = tuple(v.code for v in validate_assessment_registry(trajectory, registry))
    assert AssessmentViolationCode.INVALID_TEXT_ASSESSMENT in codes