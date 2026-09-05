from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from study_os_pir import (
    ContextKind,
    artifact_from_bytes,
    build_context_frame,
    canonical_json_bytes,
    resolve_span,
    span_from_artifact,
    verify_artifact_bytes,
)


@given(st.binary(max_size=2048))
def test_arbitrary_artifact_bytes_round_trip_without_normalization(data: bytes) -> None:
    artifact = artifact_from_bytes(artifact_id="property-artifact", data=data)
    verify_artifact_bytes(artifact, data)
    assert artifact.byte_length == len(data)


@given(
    data=st.binary(max_size=512),
    start_seed=st.integers(min_value=0, max_value=10_000),
    end_seed=st.integers(min_value=0, max_value=10_000),
)
def test_arbitrary_valid_half_open_span_resolves_exact_slice(
    data: bytes,
    start_seed: int,
    end_seed: int,
) -> None:
    if not data:
        start = end = 0
    else:
        a = start_seed % (len(data) + 1)
        b = end_seed % (len(data) + 1)
        start, end = sorted((a, b))

    artifact = artifact_from_bytes(artifact_id="a", data=data)
    span = span_from_artifact(
        span_id="s",
        artifact=artifact,
        data=data,
        byte_start=start,
        byte_end=end,
    )

    assert resolve_span(artifact=artifact, data=data, span=span) == data[start:end]


@given(st.binary(min_size=1, max_size=512), st.integers(min_value=0, max_value=10_000))
def test_single_byte_mutation_invalidates_artifact_identity(data: bytes, seed: int) -> None:
    artifact = artifact_from_bytes(artifact_id="a", data=data)
    index = seed % len(data)
    replacement = bytes([(data[index] + 1) % 256])
    mutated = data[:index] + replacement + data[index + 1 :]

    assert mutated != data
    assert artifact.sha256 != artifact_from_bytes(artifact_id="b", data=mutated).sha256


@given(st.dictionaries(st.text(min_size=1, max_size=8), st.integers(), max_size=12))
def test_canonical_json_ignores_dictionary_construction_order(payload: dict[str, int]) -> None:
    reversed_payload = dict(reversed(list(payload.items())))
    assert canonical_json_bytes(payload) == canonical_json_bytes(reversed_payload)


def test_identical_text_at_different_byte_positions_retains_distinct_span_identity() -> None:
    data = b"same|gap|same"
    artifact = artifact_from_bytes(artifact_id="a", data=data)
    first = span_from_artifact(
        span_id="first", artifact=artifact, data=data, byte_start=0, byte_end=4
    )
    second = span_from_artifact(
        span_id="second", artifact=artifact, data=data, byte_start=9, byte_end=13
    )

    assert resolve_span(artifact=artifact, data=data, span=first) == b"same"
    assert resolve_span(artifact=artifact, data=data, span=second) == b"same"
    assert first.span_id != second.span_id
    assert (first.byte_start, first.byte_end) != (second.byte_start, second.byte_end)


def test_context_digest_changes_when_source_span_order_changes() -> None:
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
        ordered_turn_refs=("t1", "t2"),
        source_span_refs=("s2", "s1"),
    )

    assert first.sha256 != second.sha256
