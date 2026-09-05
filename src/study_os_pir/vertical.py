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


class VerticalViolationCode(StrEnum):
    DUPLICATE_STEP_ID = "DUPLICATE_STEP_ID"
    DUPLICATE_REPRESENTATION_ID = "DUPLICATE_REPRESENTATION_ID"
    UNKNOWN_REPRESENTATION = "UNKNOWN_REPRESENTATION"
    MISSING_PRESERVED_REPRESENTATION = "MISSING_PRESERVED_REPRESENTATION"
    FORBIDDEN_CONCEPT_DISCLOSED = "FORBIDDEN_CONCEPT_DISCLOSED"
    ANSWER_LITERAL_LEAKED = "ANSWER_LITERAL_LEAKED"
    UNKNOWN_REJECTED_MOVE_ANCHOR = "UNKNOWN_REJECTED_MOVE_ANCHOR"
    UNKNOWN_REJECTED_MOVE_REPAIR = "UNKNOWN_REJECTED_MOVE_REPAIR"
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
    box: VerticalWindowBox
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
    active_delta: str = Field(min_length=1)
    disclosed_concepts: tuple[str, ...] = ()
    forbidden_concepts: tuple[str, ...] = ()
    probe: VerticalProbe | None = None
    evidence_note: str = Field(min_length=1)


class ObservedRejectedMove(StrictFrozenModel):
    move_id: str = Field(min_length=1)
    after_step_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    repaired_by_step_id: str = Field(min_length=1)
    evidence_note: str = Field(min_length=1)


class ExperimentalVerticalSlice(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.experimental-vertical-slice\.v0$")
    slice_id: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    representations: tuple[VerticalRepresentation, ...] = Field(min_length=1)
    steps: tuple[VerticalStep, ...] = Field(min_length=1)
    rejected_moves: tuple[ObservedRejectedMove, ...] = ()


class VerticalViolation(StrictFrozenModel):
    code: VerticalViolationCode
    detail: str = Field(min_length=1)


def validate_vertical_slice(slice_: ExperimentalVerticalSlice) -> tuple[VerticalViolation, ...]:
    violations: list[VerticalViolation] = []
    step_ids = tuple(step.step_id for step in slice_.steps)
    representation_ids = tuple(rep.representation_id for rep in slice_.representations)
    step_id_set = set(step_ids)
    representation_by_id = {rep.representation_id: rep for rep in slice_.representations}

    for duplicate in sorted({value for value in step_ids if step_ids.count(value) > 1}):
        violations.append(
            VerticalViolation(
                code=VerticalViolationCode.DUPLICATE_STEP_ID,
                detail=f"duplicate step id: {duplicate}",
            )
        )

    for duplicate in sorted(
        {value for value in representation_ids if representation_ids.count(value) > 1}
    ):
        violations.append(
            VerticalViolation(
                code=VerticalViolationCode.DUPLICATE_REPRESENTATION_ID,
                detail=f"duplicate representation id: {duplicate}",
            )
        )

    for step in slice_.steps:
        representation = representation_by_id.get(step.representation_id)
        if representation is None:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.UNKNOWN_REPRESENTATION,
                    detail=f"{step.step_id} references unknown representation {step.representation_id}",
                )
            )
            continue

        missing = sorted(set(step.preserve_components) - set(representation.visible_components))
        if missing:
            violations.append(
                VerticalViolation(
                    code=VerticalViolationCode.MISSING_PRESERVED_REPRESENTATION,
                    detail=f"{step.step_id} missing preserved component(s): {', '.join(missing)}",
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
            leaked = sorted(
                literal
                for literal in step.probe.forbidden_answer_literals
                if literal and literal in step.probe.prompt
            )
            if leaked:
                violations.append(
                    VerticalViolation(
                        code=VerticalViolationCode.ANSWER_LITERAL_LEAKED,
                        detail=f"{step.step_id} leaked answer literal(s): {', '.join(leaked)}",
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
        if move.repaired_by_step_id not in step_id_set:
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
    value_count = max(len(row.values) for row in representation.rows)
    lines = [
        f"{row.label:<{label_width}}: " + " ".join(f"{value:>3}" for value in row.values)
        for row in representation.rows
    ]
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

    lines.append("Observed rejected moves:")
    for move in slice_.rejected_moves:
        lines.extend(
            [
                f"- {move.move_id} after {move.after_step_id}",
                f"  Rejected: {move.description}",
                f"  Repair: {move.repaired_by_step_id}",
                f"  Evidence note: {move.evidence_note}",
            ]
        )
    return "\n".join(lines) + "\n"
