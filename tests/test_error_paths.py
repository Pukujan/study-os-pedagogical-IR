from __future__ import annotations

import pytest
from pydantic import ValidationError

from study_os_pir import (
    EvidenceArtifact,
    EvidenceSpan,
    EvidenceStatus,
    artifact_from_bytes,
    canonical_json_bytes,
    resolve_span,
    span_from_artifact,
    verify_artifact_bytes,
)


def test_canonical_json_accepts_runtime_model_directly() -> None:
    artifact = artifact_from_bytes(artifact_id="a", data=b"abc")
    encoded = canonical_json_bytes(artifact)
    assert b'"artifact_id":"a"' in encoded
    assert b'"schema_version":"pir.evidence-artifact.v1"' in encoded


def test_artifact_length_mismatch_fails_before_hash_acceptance() -> None:
    artifact = artifact_from_bytes(artifact_id="a", data=b"abc")
    with pytest.raises(ValueError, match="artifact byte length mismatch"):
        verify_artifact_bytes(artifact, b"abcd")


def test_same_length_artifact_tamper_fails_digest_verification() -> None:
    artifact = artifact_from_bytes(artifact_id="a", data=b"abc")
    with pytest.raises(ValueError, match="artifact sha256 mismatch"):
        verify_artifact_bytes(artifact, b"abd")


def test_negative_span_start_fails_closed() -> None:
    data = b"abc"
    artifact = artifact_from_bytes(artifact_id="a", data=data)
    with pytest.raises(ValueError, match="invalid half-open byte span"):
        span_from_artifact(
            span_id="s",
            artifact=artifact,
            data=data,
            byte_start=-1,
            byte_end=1,
        )


def test_span_model_itself_rejects_reversed_bounds() -> None:
    with pytest.raises(ValidationError, match="byte_end must be >= byte_start"):
        EvidenceSpan(
            schema_version="pir.evidence-span.v1",
            span_id="s",
            artifact_id="a",
            byte_start=2,
            byte_end=1,
            evidence_status=EvidenceStatus.VERBATIM,
        )


def test_resolve_span_rejects_wrong_artifact_identity() -> None:
    data = b"abc"
    artifact = artifact_from_bytes(artifact_id="a", data=data)
    span = EvidenceSpan(
        schema_version="pir.evidence-span.v1",
        span_id="s",
        artifact_id="other",
        byte_start=0,
        byte_end=1,
        evidence_status=EvidenceStatus.VERBATIM,
    )
    with pytest.raises(ValueError, match="span artifact_id mismatch"):
        resolve_span(artifact=artifact, data=data, span=span)


def test_resolve_span_rejects_end_beyond_artifact_length() -> None:
    data = b"abc"
    artifact = artifact_from_bytes(artifact_id="a", data=data)
    span = EvidenceSpan(
        schema_version="pir.evidence-span.v1",
        span_id="s",
        artifact_id="a",
        byte_start=0,
        byte_end=4,
        evidence_status=EvidenceStatus.VERBATIM,
    )
    with pytest.raises(ValueError, match="span byte_end exceeds artifact length"):
        resolve_span(artifact=artifact, data=data, span=span)


def test_direct_verbatim_span_cannot_resolve_from_reconstructed_artifact() -> None:
    data = b"abc"
    artifact = EvidenceArtifact(
        schema_version="pir.evidence-artifact.v1",
        artifact_id="a",
        sha256=artifact_from_bytes(artifact_id="tmp", data=data).sha256,
        byte_length=len(data),
        source_status=EvidenceStatus.RECONSTRUCTED,
    )
    span = EvidenceSpan(
        schema_version="pir.evidence-span.v1",
        span_id="s",
        artifact_id="a",
        byte_start=0,
        byte_end=3,
        evidence_status=EvidenceStatus.VERBATIM,
    )
    with pytest.raises(
        ValueError,
        match="verbatim span cannot resolve from reconstructed artifact",
    ):
        resolve_span(artifact=artifact, data=data, span=span)
