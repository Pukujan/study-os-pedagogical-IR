from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from study_os_pir import (
    ContextKind,
    EvidenceSpan,
    EvidenceStatus,
    Turn,
    TurnActor,
    artifact_from_bytes,
    build_context_frame,
    reconstruct_turn,
    resolve_span,
    span_from_artifact,
    verify_artifact_bytes,
)

ROOT = Path(__file__).resolve().parents[1]


def test_artifact_preserves_original_byte_identity() -> None:
    data = b"line one\r\nline two  \n"
    artifact = artifact_from_bytes(artifact_id="artifact-1", data=data)

    assert artifact.byte_length == len(data)
    verify_artifact_bytes(artifact, data)

    with pytest.raises(ValueError, match="sha256 mismatch|byte length mismatch"):
        verify_artifact_bytes(artifact, data.replace(b"\r\n", b"\n"))


def test_crlf_and_lf_are_different_artifacts() -> None:
    crlf = artifact_from_bytes(artifact_id="crlf", data=b"a\r\nb\r\n")
    lf = artifact_from_bytes(artifact_id="lf", data=b"a\nb\n")

    assert crlf.sha256 != lf.sha256


def test_span_resolves_exact_bytes_including_unicode_encoding() -> None:
    data = "A🙂B\n".encode()
    artifact = artifact_from_bytes(artifact_id="unicode", data=data)
    start = len(b"A")
    end = start + len("🙂".encode())
    span = span_from_artifact(
        span_id="emoji",
        artifact=artifact,
        data=data,
        byte_start=start,
        byte_end=end,
    )

    assert resolve_span(artifact=artifact, data=data, span=span) == "🙂".encode()


def test_invalid_span_bounds_fail_closed() -> None:
    data = b"abcdef"
    artifact = artifact_from_bytes(artifact_id="a", data=data)

    with pytest.raises(ValueError, match="invalid half-open byte span"):
        span_from_artifact(
            span_id="bad",
            artifact=artifact,
            data=data,
            byte_start=4,
            byte_end=3,
        )

    with pytest.raises(ValueError, match="invalid half-open byte span"):
        span_from_artifact(
            span_id="bad",
            artifact=artifact,
            data=data,
            byte_start=0,
            byte_end=99,
        )


def test_reconstructed_artifact_cannot_create_verbatim_span() -> None:
    data = b"reconstructed"
    artifact = artifact_from_bytes(
        artifact_id="a",
        data=data,
        source_status=EvidenceStatus.RECONSTRUCTED,
    )

    with pytest.raises(ValueError, match="cannot yield verbatim span"):
        span_from_artifact(
            span_id="s",
            artifact=artifact,
            data=data,
            byte_start=0,
            byte_end=len(data),
            evidence_status=EvidenceStatus.VERBATIM,
        )


def test_span_digest_detects_wrong_slice_claim() -> None:
    data = b"abcdef"
    artifact = artifact_from_bytes(artifact_id="a", data=data)
    valid = span_from_artifact(
        span_id="s",
        artifact=artifact,
        data=data,
        byte_start=1,
        byte_end=3,
    )
    tampered = EvidenceSpan(
        schema_version="pir.evidence-span.v1",
        span_id=valid.span_id,
        artifact_id=valid.artifact_id,
        byte_start=2,
        byte_end=4,
        sha256=valid.sha256,
        evidence_status=valid.evidence_status,
    )

    with pytest.raises(ValueError, match="span sha256 mismatch"):
        resolve_span(artifact=artifact, data=data, span=tampered)


def test_turn_reconstruction_preserves_span_order_exactly() -> None:
    data = b"ABCDEF"
    artifact = artifact_from_bytes(artifact_id="a", data=data)
    first = span_from_artifact(
        span_id="first", artifact=artifact, data=data, byte_start=0, byte_end=2
    )
    second = span_from_artifact(
        span_id="second", artifact=artifact, data=data, byte_start=4, byte_end=6
    )
    turn = Turn(
        schema_version="pir.turn.v1",
        turn_id="t",
        sequence=0,
        actor=TurnActor.LEARNER,
        evidence_status=EvidenceStatus.VERBATIM,
        source_span_refs=("first", "second"),
    )

    actual = reconstruct_turn(
        turn=turn,
        artifacts={"a": artifact},
        artifact_bytes={"a": data},
        spans={"first": first, "second": second},
    )
    assert actual == b"ABEF"


def test_verbatim_turn_cannot_reference_reconstructed_span() -> None:
    data = b"abc"
    artifact = artifact_from_bytes(artifact_id="a", data=data)
    span = span_from_artifact(
        span_id="s",
        artifact=artifact,
        data=data,
        byte_start=0,
        byte_end=3,
        evidence_status=EvidenceStatus.RECONSTRUCTED,
    )
    turn = Turn(
        schema_version="pir.turn.v1",
        turn_id="t",
        sequence=0,
        actor=TurnActor.LEARNER,
        evidence_status=EvidenceStatus.VERBATIM,
        source_span_refs=("s",),
    )

    with pytest.raises(ValueError, match="verbatim turn cannot reference reconstructed span"):
        reconstruct_turn(
            turn=turn,
            artifacts={"a": artifact},
            artifact_bytes={"a": data},
            spans={"s": span},
        )


def test_unresolved_turn_evidence_ref_fails_closed() -> None:
    turn = Turn(
        schema_version="pir.turn.v1",
        turn_id="t",
        sequence=0,
        actor=TurnActor.LEARNER,
        evidence_status=EvidenceStatus.VERBATIM,
        source_span_refs=("missing",),
    )

    with pytest.raises(ValueError, match="unresolved evidence ref"):
        reconstruct_turn(turn=turn, artifacts={}, artifact_bytes={}, spans={})


def test_context_frame_digest_is_order_sensitive() -> None:
    first = build_context_frame(
        context_frame_id="ctx",
        before_turn_id="t3",
        context_kind=ContextKind.VISIBLE_VERBATIM,
        ordered_turn_refs=("t1", "t2"),
        source_span_refs=("s1", "s2"),
    )
    second = build_context_frame(
        context_frame_id="ctx",
        before_turn_id="t3",
        context_kind=ContextKind.VISIBLE_VERBATIM,
        ordered_turn_refs=("t2", "t1"),
        source_span_refs=("s1", "s2"),
    )

    assert first.sha256 != second.sha256


def test_unknown_schema_version_fails_strict_model() -> None:
    with pytest.raises(ValidationError):
        Turn(
            schema_version="pir.turn.v999",
            turn_id="t",
            sequence=0,
            actor=TurnActor.LEARNER,
            evidence_status=EvidenceStatus.VERBATIM,
            source_span_refs=("s",),
        )


def test_all_json_schemas_are_valid_draft_2020_12() -> None:
    for schema_path in sorted((ROOT / "schemas").glob("*.schema.json")):
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
