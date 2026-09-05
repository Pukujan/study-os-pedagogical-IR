from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from study_os_pir.coverage import assert_extraction_complete
from study_os_pir.evidence import reconstruct_turn
from study_os_pir.models import ExtractionLedger, PrimaryDisposition, TurnDisposition
from study_os_pir.transcript import parse_chat_visible_transcript

SESSION_ROOT = Path("sessions/2026-09-04/sliding-window-pedagogy-calibration/raw")
SOURCE_PARTS = tuple(f"chat-visible-transcript-part{part:02d}.md" for part in range(1, 9))
EXTRACTION_REVISION = "sep4-full-accounting.v0.1"


def _json_dump(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _one_line_preview(body: bytes, limit: int = 120) -> str:
    text = body.decode("utf-8").replace("\r", " ").replace("\n", " ")
    compact = " ".join(text.split())
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts = []
    spans = []
    turns = []
    bodies: dict[str, bytes] = {}
    sequence_start = 0

    for part_number, filename in enumerate(SOURCE_PARTS, start=1):
        source_path = args.source_root / SESSION_ROOT / filename
        data = source_path.read_bytes()
        artifact_id = f"sep4-part{part_number:02d}"
        parsed = parse_chat_visible_transcript(
            artifact_id=artifact_id,
            data=data,
            sequence_start=sequence_start,
            source_label=str(SESSION_ROOT / filename),
        )
        artifact_map = {parsed.artifact.artifact_id: parsed.artifact}
        byte_map = {parsed.artifact.artifact_id: data}
        span_map = {span.span_id: span for span in parsed.spans}
        for turn in parsed.turns:
            bodies[turn.turn_id] = reconstruct_turn(
                turn=turn,
                artifacts=artifact_map,
                artifact_bytes=byte_map,
                spans=span_map,
            )
        artifacts.append(parsed.artifact)
        spans.extend(parsed.spans)
        turns.extend(parsed.turns)
        sequence_start += len(parsed.turns)

    dispositions = tuple(
        TurnDisposition(
            schema_version="pir.turn-disposition.v1",
            disposition_id=f"{turn.turn_id}:disposition:{EXTRACTION_REVISION}",
            extraction_revision=EXTRACTION_REVISION,
            turn_id=turn.turn_id,
            primary_disposition=PrimaryDisposition.UNRESOLVED,
        )
        for turn in turns
    )
    ledger = ExtractionLedger(
        schema_version="pir.extraction-ledger.v1",
        ledger_id="sep4-full-accounting-ledger.v0.1",
        extraction_revision=EXTRACTION_REVISION,
        dispositions=dispositions,
    )
    authoritative_turn_ids = tuple(turn.turn_id for turn in turns)
    coverage = assert_extraction_complete(
        authoritative_turn_ids=authoritative_turn_ids,
        ledger=ledger,
    )

    actor_counts = Counter(turn.actor.value for turn in turns)
    disposition_counts = Counter(item.primary_disposition.value for item in dispositions)
    receipt = {
        "schema_version": "pir.sep4-extraction-receipt.v0",
        "source_repository": "Pukujan/Study-os",
        "source_commit": args.source_commit,
        "source_parts": [artifact.model_dump(mode="json") for artifact in artifacts],
        "extraction_revision": EXTRACTION_REVISION,
        "turn_count": len(turns),
        "span_count": len(spans),
        "actor_counts": dict(sorted(actor_counts.items())),
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "coverage": coverage.model_dump(mode="json"),
        "golden_status": "not_compiled",
        "claim_boundary": [
            "This receipt proves byte-addressed turn accounting for the pinned source bundle.",
            "It does not prove pedagogical correctness or a complete golden trajectory.",
            "All turns remain UNRESOLVED until source-inspected semantic promotion occurs.",
        ],
    }

    manifest = {
        "schema_version": "pir.sep4-turn-manifest.v0",
        "source_commit": args.source_commit,
        "turns": [
            {
                **turn.model_dump(mode="json"),
                "span": spans[index].model_dump(mode="json"),
                "body_preview": _one_line_preview(bodies[turn.turn_id]),
            }
            for index, turn in enumerate(turns)
        ],
    }
    full_turns = {
        "schema_version": "pir.sep4-turn-bodies.v0",
        "source_commit": args.source_commit,
        "turns": [
            {
                "turn_id": turn.turn_id,
                "sequence": turn.sequence,
                "actor": turn.actor.value,
                "body": bodies[turn.turn_id].decode("utf-8"),
            }
            for turn in turns
        ],
    }

    audit_lines = [
        "# September-4 full-source accounting audit",
        "",
        f"Source commit: `{args.source_commit}`",
        f"Turns: **{len(turns)}**",
        f"Coverage complete: **{coverage.complete}**",
        f"Unresolved turns: **{disposition_counts[PrimaryDisposition.UNRESOLVED.value]}**",
        "Golden status: **not compiled**",
        "",
        "This is deliberately a source-accounting receipt, not a pedagogy-success claim.",
        "",
        "## Turn manifest",
        "",
    ]
    for turn in turns:
        body = bodies[turn.turn_id]
        audit_lines.append(
            f"- `{turn.turn_id}` seq={turn.sequence} actor={turn.actor.value} — "
            f"{_one_line_preview(body)}"
        )

    _json_dump(output_dir / "receipt.json", receipt)
    _json_dump(output_dir / "turn-manifest.json", manifest)
    _json_dump(output_dir / "turn-bodies.json", full_turns)
    (output_dir / "audit.md").write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
