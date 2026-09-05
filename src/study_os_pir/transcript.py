from __future__ import annotations

from dataclasses import dataclass

from .evidence import artifact_from_bytes, span_from_artifact
from .models import EvidenceArtifact, EvidenceSpan, EvidenceStatus, Turn, TurnActor


@dataclass(frozen=True)
class ParsedTranscript:
    artifact: EvidenceArtifact
    spans: tuple[EvidenceSpan, ...]
    turns: tuple[Turn, ...]


def _role_from_heading(line: bytes) -> TurnActor | None:
    stripped = line.rstrip(b"\r\n")
    if stripped == b"## User":
        return TurnActor.LEARNER
    if stripped == b"## Assistant":
        return TurnActor.TUTOR
    return None


def _fence_marker(line: bytes) -> bytes | None:
    stripped = line.lstrip()
    if stripped.startswith(b"```"):
        return b"```"
    if stripped.startswith(b"~~~"):
        return b"~~~"
    return None


def parse_chat_visible_transcript(
    *,
    artifact_id: str,
    data: bytes,
    sequence_start: int = 0,
    source_label: str | None = None,
) -> ParsedTranscript:
    """Parse archival `## User` / `## Assistant` headings without changing source bytes.

    Role-looking headings inside fenced code blocks are ignored. Each turn span contains
    the exact message-body bytes after its role heading and before the next role heading.
    """

    artifact = artifact_from_bytes(
        artifact_id=artifact_id,
        data=data,
        source_status=EvidenceStatus.VERBATIM,
        media_type="text/markdown",
        source_label=source_label,
    )

    headings: list[tuple[int, int, TurnActor]] = []
    offset = 0
    active_fence: bytes | None = None

    for line in data.splitlines(keepends=True):
        marker = _fence_marker(line)
        if marker is not None:
            if active_fence is None:
                active_fence = marker
            elif marker == active_fence:
                active_fence = None

        if active_fence is None:
            actor = _role_from_heading(line)
            if actor is not None:
                headings.append((offset, offset + len(line), actor))
        offset += len(line)

    if not headings:
        raise ValueError("transcript contains no role headings")

    spans: list[EvidenceSpan] = []
    turns: list[Turn] = []
    for local_index, (_, body_start, actor) in enumerate(headings, start=1):
        body_end = headings[local_index][0] if local_index < len(headings) else len(data)
        span_id = f"{artifact_id}:span:{local_index:04d}"
        turn_id = f"{artifact_id}:turn:{local_index:04d}"
        span = span_from_artifact(
            span_id=span_id,
            artifact=artifact,
            data=data,
            byte_start=body_start,
            byte_end=body_end,
        )
        turn = Turn(
            schema_version="pir.turn.v1",
            turn_id=turn_id,
            sequence=sequence_start + local_index - 1,
            actor=actor,
            evidence_status=EvidenceStatus.VERBATIM,
            source_span_refs=(span_id,),
        )
        spans.append(span)
        turns.append(turn)

    return ParsedTranscript(artifact=artifact, spans=tuple(spans), turns=tuple(turns))
