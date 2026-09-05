from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from .models import StrictFrozenModel
from .trajectory import ExperimentalTrajectory


class LexicalViolationCode(StrEnum):
    TRAJECTORY_ID_MISMATCH = "TRAJECTORY_ID_MISMATCH"
    DUPLICATE_STEP_POLICY = "DUPLICATE_STEP_POLICY"
    UNKNOWN_STEP = "UNKNOWN_STEP"
    TERM_CONFLICT = "TERM_CONFLICT"
    MISSING_REQUIRED_TERM = "MISSING_REQUIRED_TERM"
    FORBIDDEN_TERM_PRESENT = "FORBIDDEN_TERM_PRESENT"


class LexicalStepPolicy(StrictFrozenModel):
    step_id: str = Field(min_length=1)
    required_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()


class ExperimentalLexicalPolicy(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.experimental-lexical-policy\.v0$")
    trajectory_id: str = Field(min_length=1)
    steps: tuple[LexicalStepPolicy, ...] = Field(min_length=1)


class LexicalViolation(StrictFrozenModel):
    code: LexicalViolationCode
    detail: str = Field(min_length=1)


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def _normalized_terms(values: tuple[str, ...]) -> set[str]:
    return {value.casefold() for value in values}


def _representation_surface(trajectory: ExperimentalTrajectory, step_id: str) -> str:
    step = next(step for step in trajectory.steps if step.step_id == step_id)
    representation = next(
        representation
        for representation in trajectory.representations
        if representation.representation_id == step.representation_id
    )
    parts: list[str] = []
    for row in representation.rows:
        parts.append(row.label)
        parts.extend(row.values)
    if representation.box is not None:
        parts.append("box")
    parts.extend(representation.annotations)
    if step.probe is not None:
        parts.extend((step.probe.target, step.probe.prompt))
    return "\n".join(parts)


def validate_lexical_text(
    step_policy: LexicalStepPolicy,
    text: str,
) -> tuple[LexicalViolation, ...]:
    surface = text.casefold()
    violations: list[LexicalViolation] = []
    for term in step_policy.required_terms:
        if term.casefold() not in surface:
            violations.append(
                LexicalViolation(
                    code=LexicalViolationCode.MISSING_REQUIRED_TERM,
                    detail=f"{step_policy.step_id} is missing required learner-facing term {term!r}",
                )
            )
    for term in step_policy.forbidden_terms:
        if term.casefold() in surface:
            violations.append(
                LexicalViolation(
                    code=LexicalViolationCode.FORBIDDEN_TERM_PRESENT,
                    detail=f"{step_policy.step_id} contains forbidden learner-facing term {term!r}",
                )
            )
    return tuple(violations)


def validate_lexical_policy(
    trajectory: ExperimentalTrajectory,
    policy: ExperimentalLexicalPolicy,
) -> tuple[LexicalViolation, ...]:
    violations: list[LexicalViolation] = []
    if policy.trajectory_id != trajectory.trajectory_id:
        violations.append(
            LexicalViolation(
                code=LexicalViolationCode.TRAJECTORY_ID_MISMATCH,
                detail=(
                    f"lexical policy trajectory {policy.trajectory_id!r} does not match "
                    f"{trajectory.trajectory_id!r}"
                ),
            )
        )

    policy_step_ids = tuple(step.step_id for step in policy.steps)
    for duplicate in _duplicates(policy_step_ids):
        violations.append(
            LexicalViolation(
                code=LexicalViolationCode.DUPLICATE_STEP_POLICY,
                detail=f"duplicate lexical policy for step: {duplicate}",
            )
        )

    trajectory_step_ids = {step.step_id for step in trajectory.steps}
    for step_policy in policy.steps:
        if step_policy.step_id not in trajectory_step_ids:
            violations.append(
                LexicalViolation(
                    code=LexicalViolationCode.UNKNOWN_STEP,
                    detail=f"lexical policy references unknown step: {step_policy.step_id}",
                )
            )
            continue

        conflicts = sorted(
            _normalized_terms(step_policy.required_terms)
            & _normalized_terms(step_policy.forbidden_terms)
        )
        if conflicts:
            violations.append(
                LexicalViolation(
                    code=LexicalViolationCode.TERM_CONFLICT,
                    detail=(
                        f"{step_policy.step_id} both requires and forbids term(s): "
                        f"{', '.join(conflicts)}"
                    ),
                )
            )

        violations.extend(
            validate_lexical_text(
                step_policy,
                _representation_surface(trajectory, step_policy.step_id),
            )
        )
    return tuple(violations)


def validate_rendered_turn(
    policy: ExperimentalLexicalPolicy,
    step_id: str,
    text: str,
) -> tuple[LexicalViolation, ...]:
    matching = tuple(step_policy for step_policy in policy.steps if step_policy.step_id == step_id)
    if len(matching) != 1:
        return ()
    return validate_lexical_text(matching[0], text)
