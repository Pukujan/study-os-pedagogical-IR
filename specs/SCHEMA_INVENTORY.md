# Schema Inventory — PIR v0.1

## Versioning convention

Schema identifiers use explicit object-family versions, for example:

```text
pir.evidence-artifact.v1
pir.evidence-span.v1
pir.turn.v1
pir.context-frame.v1
```

Released schema semantics are immutable. A breaking semantic change creates `v2`; it does not replace `v1`.

## Phase G1 — evidence kernel

Current schemas:

- `schemas/evidence-artifact.v1.schema.json`
- `schemas/evidence-span.v1.schema.json`
- `schemas/turn.v1.schema.json`
- `schemas/context-frame.v1.schema.json`

These are the only v0.1 schemas implemented before the evidence kernel passes G1.

## Deferred until G1 is green

Planned but not yet authorized:

- representation-state;
- pedagogical-state;
- probe-contract;
- learner-outcome;
- transition;
- correction-branch;
- trajectory;
- extraction-ledger/coverage manifest.

The names/shape of deferred schemas are provisional. Do not build consumers against them yet.

## Compatibility policy

- readers identify schema version explicitly;
- unknown versions fail closed;
- writers emit only declared current versions;
- schema validation does not replace semantic validation;
- migrations create new derived objects and preserve original evidence/history.
