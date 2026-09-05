from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class EvidenceStatus(StrEnum):
    VERBATIM = "verbatim"
    RECONSTRUCTED = "reconstructed"


class TurnActor(StrEnum):
    LEARNER = "learner"
    TUTOR = "tutor"
    SYSTEM = "system"
    TOOL = "tool"
    OTHER = "other"


class ContextKind(StrEnum):
    VISIBLE_VERBATIM = "visible_verbatim_context"
    COMPLETE_RUNTIME = "complete_runtime_context"
    DERIVED = "derived_context"


class EvidenceArtifact(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.evidence-artifact\.v1$")
    artifact_id: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    byte_length: int = Field(ge=0)
    source_status: EvidenceStatus
    media_type: str | None = Field(default=None, min_length=1)
    source_label: str | None = Field(default=None, min_length=1)


class EvidenceSpan(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.evidence-span\.v1$")
    span_id: str = Field(min_length=1)
    artifact_id: str = Field(min_length=1)
    byte_start: int = Field(ge=0)
    byte_end: int = Field(ge=0)
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_status: EvidenceStatus

    @model_validator(mode="after")
    def validate_half_open_bounds(self) -> EvidenceSpan:
        if self.byte_end < self.byte_start:
            raise ValueError("byte_end must be >= byte_start")
        return self


class Turn(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.turn\.v1$")
    turn_id: str = Field(min_length=1)
    sequence: int = Field(ge=0)
    actor: TurnActor
    evidence_status: EvidenceStatus
    source_span_refs: tuple[str, ...] = Field(min_length=1)
    parent_turn_id: str | None = Field(default=None, min_length=1)


class ContextFrame(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.context-frame\.v1$")
    context_frame_id: str = Field(min_length=1)
    before_turn_id: str = Field(min_length=1)
    context_kind: ContextKind
    ordered_turn_refs: tuple[str, ...] = ()
    source_span_refs: tuple[str, ...] = ()
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
