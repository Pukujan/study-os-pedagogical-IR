from __future__ import annotations

import pytest

from study_os_pir.evidence import reconstruct_turn
from study_os_pir.models import TurnActor
from study_os_pir.transcript import parse_chat_visible_transcript


def test_parse_preserves_exact_message_bytes_and_sequence() -> None:
    data = (
        b"# archive\r\n\r\n"
        b"## User\r\n"
        b"hello  \r\n\r\n"
        b"## Assistant\r\n"
        b"world\r\n"
    )
    parsed = parse_chat_visible_transcript(
        artifact_id="part01",
        data=data,
        sequence_start=7,
        source_label="raw/part01.md",
    )

    assert parsed.artifact.byte_length == len(data)
    assert parsed.artifact.source_label == "raw/part01.md"
    assert tuple(turn.actor for turn in parsed.turns) == (TurnActor.LEARNER, TurnActor.TUTOR)
    assert tuple(turn.sequence for turn in parsed.turns) == (7, 8)

    artifacts = {parsed.artifact.artifact_id: parsed.artifact}
    artifact_bytes = {parsed.artifact.artifact_id: data}
    spans = {span.span_id: span for span in parsed.spans}
    bodies = tuple(
        reconstruct_turn(
            turn=turn,
            artifacts=artifacts,
            artifact_bytes=artifact_bytes,
            spans=spans,
        )
        for turn in parsed.turns
    )
    assert bodies == (b"hello  \r\n\r\n", b"world\r\n")


def test_role_headings_inside_fences_are_not_turn_boundaries() -> None:
    data = (
        b"## User\n"
        b"before\n"
        b"```text\n"
        b"## Assistant\n"
        b"~~~ not a closing backtick fence\n"
        b"```\n"
        b"after\n"
        b"## Assistant\n"
        b"reply\n"
        b"~~~text\n"
        b"## User\n"
        b"~~~\n"
    )
    parsed = parse_chat_visible_transcript(artifact_id="fences", data=data)

    assert len(parsed.turns) == 2
    assert parsed.spans[0].byte_end == data.index(b"## Assistant\nreply")
    assert parsed.spans[1].byte_end == len(data)


def test_tilde_fence_closes_before_real_heading() -> None:
    data = b"## User\n~~~\n## Assistant\n~~~\n## Assistant\nok\n"
    parsed = parse_chat_visible_transcript(artifact_id="tilde", data=data)
    assert tuple(turn.actor for turn in parsed.turns) == (TurnActor.LEARNER, TurnActor.TUTOR)


def test_transcript_without_role_headings_fails_closed() -> None:
    with pytest.raises(ValueError, match="no role headings"):
        parse_chat_visible_transcript(artifact_id="empty", data=b"plain text\n")
