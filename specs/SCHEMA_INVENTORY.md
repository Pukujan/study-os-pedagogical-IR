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

## Phase G1 — evidence kernel — GREEN

Schemas:

- `schemas/evidence-artifact.v1.schema.json`
- `schemas/evidence-span.v1.schema.json`
- `schemas/turn.v1.schema.json`
- `schemas/context-frame.v1.schema.json`

Pinned sealed evidence-kernel revision: `f1f64c76d0eaf316f4f8bb4524040db9d9094740`.

## Phase G1.5 — extraction coverage/accounting

Current schemas:

- `schemas/turn-disposition.v1.schema.json`
- `schemas/extraction-ledger.v1.schema.json`
- `schemas/coverage-report.v1.schema.json`

These schemas exist solely to prove that every authoritative source turn is explicitly accounted for under one extraction revision. The ledger does not define the authoritative source-turn universe.

## Deferred until extraction coverage is green

Planned but not yet authorized:

- representation-state;
- pedagogical-state;
- probe-contract;
- learner-outcome;
- transition;
- correction-branch;
- trajectory.

The names/shape of deferred schemas are provisional. Do not build consumers against them yet.

## Compatibility policy

- readers identify schema version explicitly;
- unknown versions fail closed;
- writers emit only declared current versions;
- schema validation does not replace semantic validation;
- migrations create new derived objects and preserve original evidence/history.
