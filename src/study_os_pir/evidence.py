from __future__ import annotations

from collections.abc import Mapping

from .canonical import canonical_sha256, sha256_hex
from .models import ContextFrame, ContextKind, EvidenceArtifact, EvidenceSpan, EvidenceStatus, Turn


def artifact_from_bytes(
    *,
    artifact_id: str,
    data: bytes,
    source_status: EvidenceStatus = EvidenceStatus.VERBATIM,
    media_type: str | None = None,
    source_label: str | None = None,
) -> EvidenceArtifact:
    return EvidenceArtifact(
        schema_version="pir.evidence-artifact.v1",
        artifact_id=artifact_id,
        sha256=sha256_hex(data),
        byte_length=len(data),
        source_status=source_status,
        media_type=media_type,
        source_label=source_label,
    )


def verify_artifact_bytes(artifact: EvidenceArtifact, data: bytes) -> None:
    if len(data) != artifact.byte_length:
        raise ValueError("artifact byte length mismatch")
    if sha256_hex(data) != artifact.sha256:
        raise ValueError("artifact sha256 mismatch")


def span_from_artifact(
    *,
    span_id: str,
    artifact: EvidenceArtifact,
    data: bytes,
    byte_start: int,
    byte_end: int,
    evidence_status: EvidenceStatus | None = None,
) -> EvidenceSpan:
    verify_artifact_bytes(artifact, data)
    if byte_start < 0 or byte_end < byte_start or byte_end > len(data):
        raise ValueError("invalid half-open byte span")

    resolved_status = evidence_status or artifact.source_status
    if (
        resolved_status is EvidenceStatus.VERBATIM
        and artifact.source_status is not EvidenceStatus.VERBATIM
    ):
        raise ValueError("reconstructed artifact cannot yield verbatim span")

    span_bytes = data[byte_start:byte_end]
    return EvidenceSpan(
        schema_version="pir.evidence-span.v1",
        span_id=span_id,
        artifact_id=artifact.artifact_id,
        byte_start=byte_start,
        byte_end=byte_end,
        sha256=sha256_hex(span_bytes),
        evidence_status=resolved_status,
    )


def resolve_span(
    *,
    artifact: EvidenceArtifact,
    data: bytes,
    span: EvidenceSpan,
) -> bytes:
    verify_artifact_bytes(artifact, data)
    if span.artifact_id != artifact.artifact_id:
        raise ValueError("span artifact_id mismatch")
    if span.byte_end > len(data):
        raise ValueError("span byte_end exceeds artifact length")
    if (
        span.evidence_status is EvidenceStatus.VERBATIM
        and artifact.source_status is not EvidenceStatus.VERBATIM
    ):
        raise ValueError("verbatim span cannot resolve from reconstructed artifact")

    value = data[span.byte_start:span.byte_end]
    if span.sha256 is not None and sha256_hex(value) != span.sha256:
        raise ValueError("span sha256 mismatch")
    return value


def reconstruct_turn(
    *,
    turn: Turn,
    artifacts: Mapping[str, EvidenceArtifact],
    artifact_bytes: Mapping[str, bytes],
    spans: Mapping[str, EvidenceSpan],
) -> bytes:
    chunks: list[bytes] = []
    for span_ref in turn.source_span_refs:
        try:
            span = spans[span_ref]
            artifact = artifacts[span.artifact_id]
            data = artifact_bytes[span.artifact_id]
        except KeyError as exc:
            raise ValueError(f"unresolved evidence ref: {exc.args[0]}") from exc

        if (
            turn.evidence_status is EvidenceStatus.VERBATIM
            and span.evidence_status is not EvidenceStatus.VERBATIM
        ):
            raise ValueError("verbatim turn cannot reference reconstructed span")
        chunks.append(resolve_span(artifact=artifact, data=data, span=span))
    return b"".join(chunks)


def context_frame_payload(
    *,
    context_frame_id: str,
    before_turn_id: str,
    context_kind: ContextKind,
    ordered_turn_refs: tuple[str, ...],
    source_span_refs: tuple[str, ...],
) -> dict[str, object]:
    return {
        "schema_version": "pir.context-frame.v1",
        "context_frame_id": context_frame_id,
        "before_turn_id": before_turn_id,
        "context_kind": context_kind.value,
        "ordered_turn_refs": list(ordered_turn_refs),
        "source_span_refs": list(source_span_refs),
    }


def build_context_frame(
    *,
    context_frame_id: str,
    before_turn_id: str,
    context_kind: ContextKind,
    ordered_turn_refs: tuple[str, ...] = (),
    source_span_refs: tuple[str, ...] = (),
) -> ContextFrame:
    payload = context_frame_payload(
        context_frame_id=context_frame_id,
        before_turn_id=before_turn_id,
        context_kind=context_kind,
        ordered_turn_refs=ordered_turn_refs,
        source_span_refs=source_span_refs,
    )
    return ContextFrame(
        schema_version="pir.context-frame.v1",
        context_frame_id=context_frame_id,
        before_turn_id=before_turn_id,
        context_kind=context_kind,
        ordered_turn_refs=ordered_turn_refs,
        source_span_refs=source_span_refs,
        sha256=canonical_sha256(payload),
    )
