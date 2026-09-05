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


class PrimaryDisposition(StrEnum):
    GOLDEN = "golden"
    FAILURE = "failure"
    LEARNER_CORRECTION = "learner_correction"
    REPAIR = "repair"
    EXERCISE = "exercise"
    VALIDATION = "validation"
    META = "meta"
    DUPLICATE = "duplicate"
    UNRESOLVED = "unresolved"


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


class TurnDisposition(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.turn-disposition\.v1$")
    disposition_id: str = Field(min_length=1)
    extraction_revision: str = Field(min_length=1)
    turn_id: str = Field(min_length=1)
    primary_disposition: PrimaryDisposition


class ExtractionLedger(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.extraction-ledger\.v1$")
    ledger_id: str = Field(min_length=1)
    extraction_revision: str = Field(min_length=1)
    dispositions: tuple[TurnDisposition, ...] = ()


class CoverageReport(StrictFrozenModel):
    schema_version: str = Field(pattern=r"^pir\.coverage-report\.v1$")
    ledger_id: str = Field(min_length=1)
    extraction_revision: str = Field(min_length=1)
    expected_source_turn_count: int = Field(ge=0)
    disposition_record_count: int = Field(ge=0)
    unique_disposed_source_turn_count: int = Field(ge=0)
    missing_turn_ids: tuple[str, ...] = ()
    duplicate_turn_ids: tuple[str, ...] = ()
    unknown_turn_ids: tuple[str, ...] = ()
    duplicate_disposition_ids: tuple[str, ...] = ()
    revision_mismatched_disposition_ids: tuple[str, ...] = ()
    duplicate_authoritative_turn_ids: tuple[str, ...] = ()
    complete: bool
