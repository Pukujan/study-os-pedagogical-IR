from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from referencing import Registry, Resource

from study_os_pir import (
    ContextKind,
    EvidenceStatus,
    ExtractionLedger,
    PrimaryDisposition,
    Turn,
    TurnActor,
    TurnDisposition,
    artifact_from_bytes,
    build_context_frame,
    evaluate_extraction_coverage,
    span_from_artifact,
)

ROOT = Path(__file__).resolve().parents[1]


def load_schema(filename: str) -> dict[str, Any]:
    raw = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
    return cast(dict[str, Any], raw)


def schema_registry() -> Registry[Any]:
    registry: Registry[Any] = Registry()
    for schema_path in sorted((ROOT / "schemas").glob("*.schema.json")):
        schema = load_schema(schema_path.name)
        schema_id = cast(str, schema["$id"])
        registry = registry.with_resource(schema_id, Resource.from_contents(schema))
    return registry


def validate(filename: str, instance: dict[str, object]) -> None:
    Draft202012Validator(
        load_schema(filename),
        registry=schema_registry(),
    ).validate(instance)


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


def test_extraction_runtime_models_validate_with_cross_schema_refs() -> None:
    item = TurnDisposition(
        schema_version="pir.turn-disposition.v1",
        disposition_id="d1",
        extraction_revision="r1",
        turn_id="t1",
        primary_disposition=PrimaryDisposition.GOLDEN,
    )
    ledger = ExtractionLedger(
        schema_version="pir.extraction-ledger.v1",
        ledger_id="ledger-1",
        extraction_revision="r1",
        dispositions=(item,),
    )
    report = evaluate_extraction_coverage(
        authoritative_turn_ids=("t1",),
        ledger=ledger,
    )

    validate(
        "turn-disposition.v1.schema.json",
        item.model_dump(mode="json"),
    )
    validate(
        "extraction-ledger.v1.schema.json",
        ledger.model_dump(mode="json"),
    )
    validate(
        "coverage-report.v1.schema.json",
        report.model_dump(mode="json"),
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
        (
            "turn-disposition.v1.schema.json",
            {
                "schema_version": "pir.turn-disposition.v999",
                "disposition_id": "d",
                "extraction_revision": "r1",
                "turn_id": "t",
                "primary_disposition": "golden",
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
