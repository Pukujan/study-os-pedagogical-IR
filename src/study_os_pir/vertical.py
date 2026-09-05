from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .models import StrictFrozenModel


class VerticalStepKind(StrEnum):
    EXPLAIN = "explain"
    PROBE = "probe"
    VALIDATE = "validate"
    BRIDGE = "bridge"
    COMPARE = "compare"


class VerticalLearnerOutcomeKind(StrEnum):
    CORRECT = "correct"
    META = "meta"


class VerticalViolationCode(StrEnum):
    DUPLICATE_STEP_ID = "DUPLICATE_STEP_ID"
    DUPLICATE_REPRESENTATION_ID = "DUPLICATE_REPRESENTATION_ID"
    DUPLICATE_LEARNER_OUTCOME_ID = "DUPLICATE_LEARNER_OUTCOME_ID"
    UNKNOWN_REPRESENTATION = "UNKNOWN_REPRESENTATION"
    MISSING_PRESERVED_REPRESENTATION = "MISSING_PRESERVED_REPRESENTATION"
    FORBIDDEN_REPRESENTATION_PRESENT = "FORBIDDEN_REPRESENTATION_PRESENT"
    FORBIDDEN_CONCEPT_DISCLOSED = "FORBIDDEN_CONCEPT_DISCLOSED"
    ANSWER_LITERAL_LEAKED = "ANSWER_LITERAL_LEAKED"
    UNKNOWN_LEARNER_OUTCOME_ANCHOR = "UNKNOWN_LEARNER_OUTCOME_ANCHOR"
    UNKNOWN_LEARNER_OUTCOME_NEXT_STEP = "UNKNOWN_LEARNER_OUTCOME_NEXT_STEP"
    INVALID_LEARNER_OUTCOME_ROUTE = "INVALID_LEARNER_OUTCOME_ROUTE"
    UNKNOWN_REJECTED_MOVE_ANCHOR = "UNKNOWN_REJECTED_MOVE_ANCHOR"
    UNKNOWN_REJECTED_MOVE_REPAIR = "UNKNOWN_REJECTED_MOVE_REPAIR"
    INVALID_REJECTED_MOVE_REPAIR_ROUTE = "INVALID_REJECTED_MOVE_REPAIR_ROUTE"
    EXECUTION_MISSING_STEP = "EXECUTION_MISSING_STEP"
    EXECUTION_UNEXPECTED_STEP = "EXECUTION_UNEXPECTED_STEP"
    EXECUTION_ORDER_MISMATCH = "EXECUTION_ORDER_MISMATCH"


class VerticalRow(StrictFrozenModel):
    row_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    values: tuple[str, ...] = Field(min_length=1)


class VerticalWindowBox(StrictFrozenModel):
    start_index: int = Field(ge=0)
    width: int = Field(gt=0)


class VerticalRepresentation(StrictFrozenModel):
    representation_id: str = Field(min_length=1)
    rows: tuple[VerticalRow, ...] = Field(min_length=1)
    box: VerticalWindowBox | None = None
    annotations: tuple[str, ...] = ()
    visible_components: tuple[str, ...] = Field(min_length=1)


class VerticalProbe(StrictFrozenModel):
    target: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    answer_reveal_allowed: bool = False
    forbidden_answer_literals: tuple[str, ...] = ()


class VerticalStep(StrictFrozenModel):
    step_id: str = Field(min_length=1)
    kind: VerticalStepKind
    goal: str = Field(min_length=1)
    representation_id: str = Field(min_length=1)
    preserve_components: tuple[str, ...] = ()
    forbidden_components: tuple[str, ...] = ()
    active_delta: str = Field(min_length=1)
    disclosed_concepts: tuple[str, ...] = ()
    forbidden_concepts: tuple[str, ...] = ()
    probe: VerticalProbe | None = None
    evidence_note: str = Field(min_length=1)


class VerticalLearnerOutcome(StrictFrozenModel):
    outcome_id: str = Field(min_length=1)
    after_step_id: str = Field(min_length=1)
    kind: VerticalLearnerOutcomeKind
    summary: str = Field(min_length=1)
    next_step_id: str | None = Field(default=None, min_length=1)
    exit_target: str | None = Field(default=None, min_length=1)
    evidence_note: str = Field(min_length=1)


class ObservedRejectedMove(StrictFrozenModel):
    move_id: str = Field(min_length=1)
    after_step_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    repaired_by_step_id: str | None = Field(default=None, min_length=1)
    repair_exit_target: str | None = Field(default=None, min_length=1)
    evidence_note: str = Field(min_length=1)


class ExperimentalVerticalSlice(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.experimental-vertical-slice\.v0$")
    slice_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    representations: tuple[VerticalRepresentation, ...] = Field(min_length=1)
    steps: tuple[VerticalStep, ...] = Field(min_length=1)
    learner_outcomes: tuple[VerticalLearnerOutcome, ...] = ()
    rejected_moves: tuple[ObservedRejectedMove, ...] = ()


class VerticalViolation(StrictFrozenModel):
    code: VerticalViolationCode
    detail: str = Field(min_length=1)


def _duplicate_values(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def _route_is_exclusive(first: str | None, second: str | None) -> bool:
    return (first is None) != (second is None)


def _representation_features(representation: VerticalRepresentation) -> set[str]:
    features = set(representation.visible_components)
    if representation.box is not None:
        features.add("window_box")
    return features


def _representation_surface_text(representation: VerticalRepresentation) -> str:
    parts = [row.label for row in representation.rows]
    for row in representation.rows:
        parts.extend(row.values)
    parts.extend(representation.annotations)
    return "\n".join(parts)


def validate_vertical_slice(slice_: ExperimentalVerticalSlice) -> tuple[VerticalViolation, ...]:
    violations: list[VerticalViolation] = []
    step_ids = tuple(step.step_id for step in slice_.steps)
    representation_ids = tuple(rep.representation_id for rep in slice_.representations)
    outcome_ids = tuple(outcome.outcome_id for outcome in slice_.learner_outcomes)
    step_id_set = set(step_ids)
    representation_by_id = {rep.representation_id: rep for rep in slice_.representations}

    for duplicate in _duplicate_values(step_ids):
        violations.append(
            VerticalViolation(
                code=VerticalViolationCode.DUPLICATE_STEP_ID,
                detail=f"duplicate step id: {duplicate}",
            )
        )

    for duplicate in _duplicate_values(representation_ids):
        violations.append(
            VerticalViolation(
                code=VerticalViolationCode.DUPLICATE_REPRESENTATION_ID,
                detail=f"duplicate representation id: {duplicate}",
            )
        )

    for duplicate in _duplicate_values(outcome_ids):
        violations.append(
            VerticalViolation(
                code=VerticalViolationCode.DUPLICATE_LEARNER_OUTCOME_ID,
                detail=f"duplicate learner outcome id: {duplicate}",
            )
        )

    for step in slice_.steps:
        representation = representation_by_id.get(step.representation_id)
        if representation is None:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.UNKNOWN_REPRESENTATION,
                    detail=(
                        f"{step.step_id} references unknown representation "
                        f"{step.representation_id}"
                    ),
                )
            )
            continue

        representation_features = _representation_features(representation)
        missing = sorted(set(step.preserve_components) - representation_features)
        if missing:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.MISSING_PRESERVED_REPRESENTATION,
                    detail=f"{step.step_id} missing preserved component(s): {', '.join(missing)}",
                )
            )

        forbidden_present = sorted(
            set(step.forbidden_components).intersection(representation_features)
        )
        if forbidden_present:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.FORBIDDEN_REPRESENTATION_PRESENT,
                    detail=(
                        f"{step.step_id} contains forbidden representation feature(s): "
                        f"{', '.join(forbidden_present)}"
                    ),
                )
            )

        disclosed_forbidden = sorted(
            set(step.disclosed_concepts).intersection(step.forbidden_concepts)
        )
        if disclosed_forbidden:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.FORBIDDEN_CONCEPT_DISCLOSED,
                    detail=(
                        f"{step.step_id} disclosed forbidden concept(s): "
                        f"{', '.join(disclosed_forbidden)}"
                    ),
                )
            )

        if step.probe is not None and not step.probe.answer_reveal_allowed:
            learner_visible_surface = (
                step.probe.prompt + "\n" + _representation_surface_text(representation)
            )
            leaked = sorted(
                literal
                for literal in step.probe.forbidden_answer_literals
                if literal and literal in learner_visible_surface
            )
            if leaked:
                violations.append(
                    VerticalViolation(
                        code=VerticalViolationCode.ANSWER_LITERAL_LEAKED,
                        detail=f"{step.step_id} leaked answer literal(s): {', '.join(leaked)}",
                    )
                )

    for outcome in slice_.learner_outcomes:
        if outcome.after_step_id not in step_id_set:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.UNKNOWN_LEARNER_OUTCOME_ANCHOR,
                    detail=f"{outcome.outcome_id} anchors to unknown step {outcome.after_step_id}",
                )
            )
        if not _route_is_exclusive(outcome.next_step_id, outcome.exit_target):
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.INVALID_LEARNER_OUTCOME_ROUTE,
                    detail=(
                        f"{outcome.outcome_id} must select exactly one of next_step_id "
                        "or exit_target"
                    ),
                )
            )
        elif outcome.next_step_id is not None and outcome.next_step_id not in step_id_set:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.UNKNOWN_LEARNER_OUTCOME_NEXT_STEP,
                    detail=(
                        f"{outcome.outcome_id} routes to unknown step "
                        f"{outcome.next_step_id}"
                    ),
                )
            )

    for move in slice_.rejected_moves:
        if move.after_step_id not in step_id_set:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.UNKNOWN_REJECTED_MOVE_ANCHOR,
                    detail=f"{move.move_id} anchors to unknown step {move.after_step_id}",
                )
            )
        if not _route_is_exclusive(move.repaired_by_step_id, move.repair_exit_target):
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.INVALID_REJECTED_MOVE_REPAIR_ROUTE,
                    detail=(
                        f"{move.move_id} must select exactly one repair step "
                        "or repair exit target"
                    ),
                )
            )
        elif move.repaired_by_step_id is not None and move.repaired_by_step_id not in step_id_set:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.UNKNOWN_REJECTED_MOVE_REPAIR,
                    detail=f"{move.move_id} repairs to unknown step {move.repaired_by_step_id}",
                )
            )

    return tuple(violations)


def validate_vertical_execution(
    slice_: ExperimentalVerticalSlice, executed_step_ids: tuple[str, ...]
) -> tuple[VerticalViolation, ...]:
    expected = tuple(step.step_id for step in slice_.steps)
    expected_set = set(expected)
    executed_set = set(executed_step_ids)
    violations: list[VerticalViolation] = []

    missing = tuple(step_id for step_id in expected if step_id not in executed_set)
    if missing:
        violations.append(
            VerticalViolation(
                code=VerticalViolationCode.EXECUTION_MISSING_STEP,
                detail=f"missing step(s): {', '.join(missing)}",
            )
        )

    unexpected = tuple(step_id for step_id in executed_step_ids if step_id not in expected_set)
    if unexpected:
        violations.append(
            VerticalViolation(
                code=VerticalViolationCode.EXECUTION_UNEXPECTED_STEP,
                detail=f"unexpected step(s): {', '.join(unexpected)}",
            )
        )

    if not missing and not unexpected and executed_step_ids != expected:
        violations.append(
            VerticalViolation(
                code=VerticalViolationCode.EXECUTION_ORDER_MISMATCH,
                detail="execution contains the required steps but not in the calibrated order",
            )
        )

    return tuple(violations)


def _render_representation(representation: VerticalRepresentation) -> str:
    label_width = max(len(row.label) for row in representation.rows)
    lines = [
        f"{row.label:<{label_width}}: " + " ".join(f"{value:>3}" for value in row.values)
        for row in representation.rows
    ]
    if representation.box is not None:
        value_count = max(len(row.values) for row in representation.rows)
        end = representation.box.start_index + representation.box.width
        markers = [
            "^^^" if representation.box.start_index <= index < end else "   "
            for index in range(value_count)
        ]
        lines.append(f"{'window':<{label_width}}: " + " ".join(markers))
    lines.extend(f"{'':<{label_width}}  {annotation}" for annotation in representation.annotations)
    return "\n".join(lines)


def render_vertical_slice(slice_: ExperimentalVerticalSlice) -> str:
    representation_by_id = {rep.representation_id: rep for rep in slice_.representations}
    lines = [
        f"Experimental vertical slice: {slice_.slice_id}",
        f"Source: {slice_.source_locator}",
        "",
    ]

    for index, step in enumerate(slice_.steps, start=1):
        lines.extend(
            [
                f"{index}. {step.step_id} [{step.kind.value}]",
                f"Goal: {step.goal}",
                _render_representation(representation_by_id[step.representation_id]),
                f"Preserve: {', '.join(step.preserve_components)}",
                f"Active delta: {step.active_delta}",
                f"Forbidden now: {', '.join(step.forbidden_concepts)}",
            ]
        )
        if step.probe is not None:
            lines.extend(
                [
                    f"Probe target: {step.probe.target}",
                    f"Question: {step.probe.prompt}",
                    f"Answer reveal allowed: {str(step.probe.answer_reveal_allowed).lower()}",
                ]
            )
        lines.extend([f"Evidence note: {step.evidence_note}", ""])

    if slice_.learner_outcomes:
        lines.append("Learner outcomes:")
        for outcome in slice_.learner_outcomes:
            route = outcome.next_step_id or f"exit:{outcome.exit_target}"
            lines.extend(
                [
                    f"- {outcome.outcome_id} after {outcome.after_step_id}",
                    f"  Kind: {outcome.kind.value}",
                    f"  Summary: {outcome.summary}",
                    f"  Route: {route}",
                    f"  Evidence note: {outcome.evidence_note}",
                ]
            )

    lines.append("Observed rejected moves:")
    for move in slice_.rejected_moves:
        repair = move.repaired_by_step_id or f"exit:{move.repair_exit_target}"
        lines.extend(
            [
                f"- {move.move_id} after {move.after_step_id}",
                f"  Rejected: {move.description}",
                f"  Repair: {repair}",
                f"  Evidence note: {move.evidence_note}",
            ]
        )
    return "\n".join(lines) + "\n"
