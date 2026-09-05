from __future__ import annotations

import re
from enum import StrEnum

from pydantic import Field

from .models import StrictFrozenModel
from .trajectory import (
    ExperimentalTrajectory,
    TrajectoryOutcomeKind,
    TrajectoryStep,
    validate_trajectory,
)
from .vertical import VerticalRepresentation, VerticalStepKind


class AssessmentKind(StrEnum):
    INTEGER = "integer"
    INTEGER_SEQUENCE = "integer_sequence"
    TEXT = "text"


class AssessmentViolationCode(StrEnum):
    TRAJECTORY_ID_MISMATCH = "TRAJECTORY_ID_MISMATCH"
    DUPLICATE_ASSESSMENT_STEP = "DUPLICATE_ASSESSMENT_STEP"
    UNKNOWN_ASSESSMENT_STEP = "UNKNOWN_ASSESSMENT_STEP"
    ASSESSMENT_FOR_NON_PROBE = "ASSESSMENT_FOR_NON_PROBE"
    MISSING_PROBE_ASSESSMENT = "MISSING_PROBE_ASSESSMENT"
    INVALID_INTEGER_ASSESSMENT = "INVALID_INTEGER_ASSESSMENT"
    INVALID_INTEGER_SEQUENCE_ASSESSMENT = "INVALID_INTEGER_SEQUENCE_ASSESSMENT"
    INVALID_TEXT_ASSESSMENT = "INVALID_TEXT_ASSESSMENT"


class ReplayPhase(StrEnum):
    RENDER = "render"
    AWAIT_RESPONSE = "await_response"
    EXITED = "exited"


class AssessmentSpec(StrictFrozenModel):
    step_id: str = Field(min_length=1)
    kind: AssessmentKind
    expected_values: tuple[int, ...] = ()
    partial_values: tuple[int, ...] = ()
    expected_text: tuple[str, ...] = ()
    partial_text: tuple[str, ...] = ()


class AssessmentRegistry(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.experimental-assessment-registry\.v0$")
    trajectory_id: str = Field(min_length=1)
    assessments: tuple[AssessmentSpec, ...] = ()


class ReplayContext(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.experimental-replay-context\.v0$")
    trajectory_id: str = Field(min_length=1)
    persistent_text: tuple[str, ...] = Field(min_length=1)


class AssessmentViolation(StrictFrozenModel):
    code: AssessmentViolationCode
    detail: str = Field(min_length=1)


class RendererProbeContract(StrictFrozenModel):
    target: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    answer_reveal_allowed: bool


class RendererTurnContract(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.renderer-turn-contract\.v0$")
    trajectory_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    kind: VerticalStepKind
    goal: str = Field(min_length=1)
    representation: VerticalRepresentation
    persistent_text: tuple[str, ...] = ()
    preserve_components: tuple[str, ...]
    forbidden_components: tuple[str, ...]
    active_delta: str = Field(min_length=1)
    disclosed_concepts: tuple[str, ...]
    forbidden_concepts: tuple[str, ...]
    probe: RendererProbeContract | None = None


class ReplayCursor(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.replay-cursor\.v0$")
    trajectory_id: str = Field(min_length=1)
    phase: ReplayPhase
    current_step_id: str | None = Field(default=None, min_length=1)
    exit_target: str | None = Field(default=None, min_length=1)
    visited_step_ids: tuple[str, ...] = ()
    outcomes: tuple[TrajectoryOutcomeKind, ...] = ()


class ResponseResult(StrictFrozenModel):
    outcome: TrajectoryOutcomeKind
    cursor: ReplayCursor


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def validate_assessment_registry(
    trajectory: ExperimentalTrajectory,
    registry: AssessmentRegistry,
) -> tuple[AssessmentViolation, ...]:
    violations: list[AssessmentViolation] = []
    if registry.trajectory_id != trajectory.trajectory_id:
        violations.append(
            AssessmentViolation(
                code=AssessmentViolationCode.TRAJECTORY_ID_MISMATCH,
                detail=(
                    f"registry trajectory {registry.trajectory_id!r} does not match "
                    f"{trajectory.trajectory_id!r}"
                ),
            )
        )

    step_by_id = {step.step_id: step for step in trajectory.steps}
    assessment_step_ids = tuple(spec.step_id for spec in registry.assessments)
    for duplicate in _duplicates(assessment_step_ids):
        violations.append(
            AssessmentViolation(
                code=AssessmentViolationCode.DUPLICATE_ASSESSMENT_STEP,
                detail=f"duplicate assessment for step: {duplicate}",
            )
        )

    for spec in registry.assessments:
        step = step_by_id.get(spec.step_id)
        if step is None:
            violations.append(
                AssessmentViolation(
                    code=AssessmentViolationCode.UNKNOWN_ASSESSMENT_STEP,
                    detail=f"assessment references unknown step: {spec.step_id}",
                )
            )
            continue
        if step.kind != VerticalStepKind.PROBE:
            violations.append(
                AssessmentViolation(
                    code=AssessmentViolationCode.ASSESSMENT_FOR_NON_PROBE,
                    detail=f"assessment targets non-probe step: {spec.step_id}",
                )
            )
        if spec.kind == AssessmentKind.INTEGER:
            if len(spec.expected_values) != 1 or spec.expected_text or spec.partial_text:
                violations.append(
                    AssessmentViolation(
                        code=AssessmentViolationCode.INVALID_INTEGER_ASSESSMENT,
                        detail=f"integer assessment must contain one integer value: {spec.step_id}",
                    )
                )
        elif spec.kind == AssessmentKind.INTEGER_SEQUENCE:
            if not spec.expected_values or spec.expected_text or spec.partial_text:
                violations.append(
                    AssessmentViolation(
                        code=AssessmentViolationCode.INVALID_INTEGER_SEQUENCE_ASSESSMENT,
                        detail=(
                            "integer-sequence assessment must contain integer values: "
                            f"{spec.step_id}"
                        ),
                    )
                )
        elif not spec.expected_text or spec.expected_values or spec.partial_values:
            violations.append(
                AssessmentViolation(
                    code=AssessmentViolationCode.INVALID_TEXT_ASSESSMENT,
                    detail=(
                        "text assessment must contain expected_text and optional partial_text "
                        f"alternatives only: {spec.step_id}"
                    ),
                )
            )

    assessed_steps = set(assessment_step_ids)
    for step in trajectory.steps:
        if step.kind == VerticalStepKind.PROBE and step.step_id not in assessed_steps:
            violations.append(
                AssessmentViolation(
                    code=AssessmentViolationCode.MISSING_PROBE_ASSESSMENT,
                    detail=f"probe has no assessment: {step.step_id}",
                )
            )

    return tuple(violations)


def _parse_integer(response: str) -> tuple[int, ...]:
    text = response.strip()
    if re.fullmatch(r"[+-]?\d+", text) is None:
        raise ValueError("response is not a single integer")
    return (int(text),)


def _parse_integer_sequence(response: str) -> tuple[int, ...]:
    normalized = response.strip()
    for character in "[],(),":
        normalized = normalized.replace(character, " ")
    tokens = normalized.split()
    if not tokens:
        raise ValueError("response does not contain an integer sequence")

    values: list[int] = []
    for token in tokens:
        if re.fullmatch(r"[+-]?\d+", token) is None:
            raise ValueError("response is not a supported integer sequence")
        values.append(int(token))
    return tuple(values)


def _normalize_text(response: str) -> str:
    return re.sub(r"\s+", "", response.strip())


def _matches_partial(spec: AssessmentSpec, response: str) -> bool:
    if not spec.partial_values:
        return False
    try:
        observed = _parse_integer_sequence(response)
    except ValueError:
        return False
    return observed == spec.partial_values


def classify_response(spec: AssessmentSpec, response: str) -> TrajectoryOutcomeKind:
    if spec.kind == AssessmentKind.TEXT:
        observed_text = _normalize_text(response)
        if any(observed_text == _normalize_text(expected) for expected in spec.expected_text):
            return TrajectoryOutcomeKind.CORRECT
        if any(observed_text == _normalize_text(partial) for partial in spec.partial_text):
            return TrajectoryOutcomeKind.PARTIAL
        return TrajectoryOutcomeKind.INCORRECT

    try:
        if spec.kind == AssessmentKind.INTEGER:
            observed = _parse_integer(response)
        else:
            observed = _parse_integer_sequence(response)
    except ValueError:
        if _matches_partial(spec, response):
            return TrajectoryOutcomeKind.PARTIAL
        raise
    if observed == spec.expected_values:
        return TrajectoryOutcomeKind.CORRECT
    if _matches_partial(spec, response):
        return TrajectoryOutcomeKind.PARTIAL
    return TrajectoryOutcomeKind.INCORRECT


def _require_runtime_valid(
    trajectory: ExperimentalTrajectory,
    registry: AssessmentRegistry,
) -> None:
    if validate_trajectory(trajectory):
        raise ValueError("cannot start replay with invalid trajectory")
    if validate_assessment_registry(trajectory, registry):
        raise ValueError("cannot start replay with invalid assessment registry")


def start_replay(
    trajectory: ExperimentalTrajectory,
    registry: AssessmentRegistry,
) -> ReplayCursor:
    _require_runtime_valid(trajectory, registry)
    return ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=trajectory.trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id=trajectory.entry_step_id,
    )


def _current_step(trajectory: ExperimentalTrajectory, cursor: ReplayCursor) -> TrajectoryStep:
    if cursor.trajectory_id != trajectory.trajectory_id:
        raise ValueError("cursor trajectory does not match trajectory")
    if cursor.current_step_id is None:
        raise ValueError("cursor has no current step")
    for step in trajectory.steps:
        if step.step_id == cursor.current_step_id:
            return step
    raise ValueError(f"cursor references unknown step: {cursor.current_step_id}")


def build_renderer_contract(
    trajectory: ExperimentalTrajectory,
    cursor: ReplayCursor,
    context: ReplayContext | None = None,
) -> RendererTurnContract:
    if cursor.phase != ReplayPhase.RENDER:
        raise ValueError("renderer contract is available only in render phase")
    if context is not None and context.trajectory_id != trajectory.trajectory_id:
        raise ValueError("replay context trajectory does not match trajectory")
    step = _current_step(trajectory, cursor)
    representation_by_id = {
        representation.representation_id: representation
        for representation in trajectory.representations
    }
    representation = representation_by_id[step.representation_id]
    safe_probe = None
    if step.probe is not None:
        safe_probe = RendererProbeContract(
            target=step.probe.target,
            prompt=step.probe.prompt,
            answer_reveal_allowed=step.probe.answer_reveal_allowed,
        )
    return RendererTurnContract(
        schema_version="pir.renderer-turn-contract.v0",
        trajectory_id=trajectory.trajectory_id,
        step_id=step.step_id,
        kind=step.kind,
        goal=step.goal,
        representation=representation,
        persistent_text=() if context is None else context.persistent_text,
        preserve_components=step.preserve_components,
        forbidden_components=step.forbidden_components,
        active_delta=step.active_delta,
        disclosed_concepts=step.disclosed_concepts,
        forbidden_concepts=step.forbidden_concepts,
        probe=safe_probe,
    )


def _append_visit(cursor: ReplayCursor, step_id: str) -> tuple[str, ...]:
    return (*cursor.visited_step_ids, step_id)


def _cursor_for_target(
    cursor: ReplayCursor,
    *,
    visited: tuple[str, ...],
    next_step_id: str | None,
    exit_target: str | None,
    outcomes: tuple[TrajectoryOutcomeKind, ...] | None = None,
) -> ReplayCursor:
    if exit_target is not None:
        return ReplayCursor(
            schema_version="pir.replay-cursor.v0",
            trajectory_id=cursor.trajectory_id,
            phase=ReplayPhase.EXITED,
            current_step_id=None,
            exit_target=exit_target,
            visited_step_ids=visited,
            outcomes=cursor.outcomes if outcomes is None else outcomes,
        )
    if next_step_id is None:
        raise ValueError("runtime transition has no target")
    return ReplayCursor(
        schema_version="pir.replay-cursor.v0",
        trajectory_id=cursor.trajectory_id,
        phase=ReplayPhase.RENDER,
        current_step_id=next_step_id,
        visited_step_ids=visited,
        outcomes=cursor.outcomes if outcomes is None else outcomes,
    )


def mark_turn_rendered(
    trajectory: ExperimentalTrajectory,
    cursor: ReplayCursor,
) -> ReplayCursor:
    if cursor.phase != ReplayPhase.RENDER:
        raise ValueError("turn can be marked rendered only in render phase")
    step = _current_step(trajectory, cursor)
    visited = _append_visit(cursor, step.step_id)
    if step.kind == VerticalStepKind.PROBE:
        return ReplayCursor(
            schema_version="pir.replay-cursor.v0",
            trajectory_id=cursor.trajectory_id,
            phase=ReplayPhase.AWAIT_RESPONSE,
            current_step_id=step.step_id,
            visited_step_ids=visited,
            outcomes=cursor.outcomes,
        )

    transitions = tuple(
        transition
        for transition in trajectory.automatic_transitions
        if transition.from_step_id == step.step_id
    )
    if len(transitions) != 1:
        raise ValueError("non-probe step does not have exactly one automatic transition")
    transition = transitions[0]
    return _cursor_for_target(
        cursor,
        visited=visited,
        next_step_id=transition.next_step_id,
        exit_target=transition.exit_target,
    )


def submit_response(
    trajectory: ExperimentalTrajectory,
    registry: AssessmentRegistry,
    cursor: ReplayCursor,
    response: str,
) -> ResponseResult:
    if cursor.phase != ReplayPhase.AWAIT_RESPONSE:
        raise ValueError("response can be submitted only while awaiting a response")
    step = _current_step(trajectory, cursor)
    if step.kind != VerticalStepKind.PROBE:
        raise ValueError("awaiting-response cursor does not point to a probe")

    spec_by_step = {spec.step_id: spec for spec in registry.assessments}
    spec = spec_by_step.get(step.step_id)
    if spec is None:
        raise ValueError(f"probe has no runtime assessment: {step.step_id}")
    outcome = classify_response(spec, response)

    routes = tuple(
        route
        for route in trajectory.outcome_routes
        if route.after_step_id == step.step_id and route.outcome == outcome
    )
    if len(routes) != 1:
        raise ValueError(f"no unique route for outcome {outcome.value} after {step.step_id}")
    route = routes[0]
    outcomes = (*cursor.outcomes, outcome)
    next_cursor = _cursor_for_target(
        cursor,
        visited=cursor.visited_step_ids,
        next_step_id=route.next_step_id,
        exit_target=route.exit_target,
        outcomes=outcomes,
    )
    return ResponseResult(outcome=outcome, cursor=next_cursor)