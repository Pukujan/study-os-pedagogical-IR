from __future__ import annotations

import re
from enum import StrEnum

from pydantic import Field

from .models import StrictFrozenModel
from .trajectory import ExperimentalTrajectory
from .vertical import VerticalRepresentation


class LexicalViolationCode(StrEnum):
    DUPLICATE_CONCEPT_RULE = "DUPLICATE_CONCEPT_RULE"
    PREFERRED_TERM_NOT_ALLOWED = "PREFERRED_TERM_NOT_ALLOWED"
    ALLOWED_FORBIDDEN_OVERLAP = "ALLOWED_FORBIDDEN_OVERLAP"
    FORBIDDEN_TERM_PRESENT = "FORBIDDEN_TERM_PRESENT"


class LexicalRule(StrictFrozenModel):
    concept_id: str = Field(min_length=1)
    preferred_term: str = Field(min_length=1)
    allowed_terms: tuple[str, ...] = Field(min_length=1)
    forbidden_terms: tuple[str, ...] = ()


class LexicalRegister(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.experimental-lexical-register\.v0$")
    register_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rules: tuple[LexicalRule, ...] = Field(min_length=1)


class LexicalViolation(StrictFrozenModel):
    code: LexicalViolationCode
    detail: str = Field(min_length=1)


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def _representation_surface(representation: VerticalRepresentation) -> str:
    values: list[str] = []
    for row in representation.rows:
        values.append(row.label)
        values.extend(row.values)
    values.extend(representation.annotations)
    return "\n".join(values)


def _contains_term(surface: str, term: str) -> bool:
    pattern = rf"(?<!\w){re.escape(term)}(?!\w)"
    return re.search(pattern, surface, flags=re.IGNORECASE) is not None


def validate_lexical_register(
    trajectory: ExperimentalTrajectory,
    register: LexicalRegister,
    *,
    persistent_text: tuple[str, ...] = (),
) -> tuple[LexicalViolation, ...]:
    violations: list[LexicalViolation] = []
    concept_ids = tuple(rule.concept_id for rule in register.rules)
    for duplicate in _duplicates(concept_ids):
        violations.append(
            LexicalViolation(
                code=LexicalViolationCode.DUPLICATE_CONCEPT_RULE,
                detail=f"duplicate lexical rule for concept: {duplicate}",
            )
        )

    for rule in register.rules:
        allowed = {term.casefold() for term in rule.allowed_terms}
        forbidden = {term.casefold() for term in rule.forbidden_terms}
        if rule.preferred_term.casefold() not in allowed:
            violations.append(
                LexicalViolation(
                    code=LexicalViolationCode.PREFERRED_TERM_NOT_ALLOWED,
                    detail=(
                        f"{rule.concept_id} preferred term {rule.preferred_term!r} "
                        "is not in allowed_terms"
                    ),
                )
            )
        overlap = sorted(allowed.intersection(forbidden))
        if overlap:
            violations.append(
                LexicalViolation(
                    code=LexicalViolationCode.ALLOWED_FORBIDDEN_OVERLAP,
                    detail=(
                        f"{rule.concept_id} has term(s) both allowed and forbidden: "
                        f"{', '.join(overlap)}"
                    ),
                )
            )

    representation_by_id = {
        representation.representation_id: representation
        for representation in trajectory.representations
    }
    persistent_surface = "\n".join(persistent_text)
    for step in trajectory.steps:
        representation = representation_by_id.get(step.representation_id)
        if representation is None:
            continue
        parts = [_representation_surface(representation)]
        if step.probe is not None:
            parts.append(step.probe.prompt)
        if persistent_surface:
            parts.append(persistent_surface)
        surface = "\n".join(parts)
        for rule in register.rules:
            for term in rule.forbidden_terms:
                if not _contains_term(surface, term):
                    continue
                violations.append(
                    LexicalViolation(
                        code=LexicalViolationCode.FORBIDDEN_TERM_PRESENT,
                        detail=(
                            f"{step.step_id} uses forbidden {rule.concept_id} term "
                            f"{term!r} under register {register.register_id}"
                        ),
                    )
                )
    return tuple(violations)
