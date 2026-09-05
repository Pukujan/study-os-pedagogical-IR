from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from study_os_pir import (
    ContextKind,
    EvidenceStatus,
    Turn,
    TurnActor,
    artifact_from_bytes,
    build_context_frame,
    span_from_artifact,
)

ROOT = Path(__file__).resolve().parents[1]


def load_schema(filename: str) -> dict[str, object]:
    raw = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    return cast(dict[str, object], raw)


def validate(filename: str, instance: dict[str, object]) -> None:
    Draft202012Validator(load_schema(filename)).validate(instance)


def test_valid_runtime_models_also_validate_against_wire_schemas() -> None:
    data = b"learner turn"
    artifact = artifact_from_bytes(artifact_id="a", data=data, media_type="text/plain")
    span = span_from_artifact(
        span_id="s",
        artifact=artifact,
        data=data,
        byte_start=0,
        byte_end=len(data),
    )
    turn = Turn(
        schema_version="pir.turn.v1",
        turn_id="t",
        sequence=0,
        actor=TurnActor.LEARNER,
        evidence_status=EvidenceStatus.VERBATIM,
        source_span_refs=("s",),
    )
    context = build_context_frame(
        context_frame_id="ctx",
        before_turn_id="next",
        context_kind=ContextKind.VISIBLE_VERBATIM,
        ordered_turn_refs=("t",),
        source_span_refs=("s",),
    )

    validate(
        "evidence-artifact.v1.schema.json",
        artifact.model_dump(mode="json", exclude_none=True),
    )
    validate(
        "evidence-span.v1.schema.json",
        span.model_dump(mode="json", exclude_none=True),
    )
    validate("turn.v1.schema.json", turn.model_dump(mode="json", exclude_none=True))
    validate(
        "context-frame.v1.schema.json",
        context.model_dump(mode="json", exclude_none=True),
    )


@pytest.mark.parametrize(
    ("filename", "bad_instance"),
    [
        (
            "evidence-artifact.v1.schema.json",
            {
                "schema_version": "pir.evidence-artifact.v2",
                "artifact_id": "a",
                "sha256": "0" * 64,
                "byte_length": 0,
                "source_status": "verbatim",
            },
        ),
        (
            "turn.v1.schema.json",
            {
                "schema_version": "pir.turn.v999",
                "turn_id": "t",
                "sequence": 0,
                "actor": "learner",
                "evidence_status": "verbatim",
                "source_span_refs": ["s"],
            },
        ),
    ],
)
def test_wire_schemas_fail_closed_on_unknown_versions(
    filename: str,
    bad_instance: dict[str, object],
) -> None:
    with pytest.raises(JsonSchemaValidationError):
        validate(filename, bad_instance)
