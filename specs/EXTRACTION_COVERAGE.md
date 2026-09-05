# Extraction Coverage — PIR v0.1

## Purpose

This layer exists to prevent a lossy extractor from silently omitting source turns and then declaring a golden complete.

The motivating failure class is concrete: a calibrated section such as `enumerate(a)` can exist in the raw transcript yet disappear from a later compressed reconstruction.

## Critical trust rule

> The extraction ledger does not define the source universe it is graded against.

Coverage is always computed against an authoritative set/order of `Turn` IDs produced by the evidence layer.

Bad design:

```text
ledger says it contains 100 turns
ledger dispositions 100 turns
→ "100% complete"
```

This can hide source turn 101.

Required design:

```text
authoritative Turn IDs from evidence layer
                 +
         ExtractionLedger
                 ↓
      deterministic set accounting
```

## Primary disposition

Each source turn receives exactly one primary disposition for one extraction revision:

- `golden`
- `failure`
- `learner_correction`
- `repair`
- `exercise`
- `validation`
- `meta`
- `duplicate`
- `unresolved`

Primary disposition is an accounting label, not the full semantic annotation model.

A turn may later have multiple secondary annotations, but that does not alter the exactly-one-primary-disposition invariant.

## Extraction revision

Every `TurnDisposition` and its containing `ExtractionLedger` carries the same explicit `extraction_revision`.

A disposition from another extraction revision cannot accidentally satisfy coverage for the current ledger.

## Completion

Coverage is complete if and only if all of these are true:

1. authoritative source turn IDs are unique;
2. every authoritative source turn ID appears exactly once in dispositions;
3. no unknown/non-source turn ID appears;
4. every disposition uses the ledger extraction revision;
5. disposition IDs are unique;
6. the ledger is structurally valid.

A caller may ask the kernel to assert completion. If any condition fails, it raises rather than returning a best-effort complete result.

## Coverage report

The deterministic report contains:

- expected source-turn count;
- disposition record count;
- unique disposed source-turn count;
- missing turn IDs;
- duplicate turn IDs;
- unknown turn IDs;
- duplicate disposition IDs;
- revision-mismatched disposition IDs;
- duplicate authoritative source IDs;
- `complete` boolean.

Diagnostic ID arrays are sorted lexicographically so reports are reproducible independent of input container ordering. Source pedagogical order remains represented by `Turn.sequence`; diagnostics are not trajectory order.

## What coverage does not prove

100% disposition coverage does **not** prove the classifications are correct.

For example, labeling every turn `meta` can still achieve syntactic coverage. Historical replay therefore adds semantic audits and source-backed golden compilation after coverage is complete.

Coverage proves a narrower but critical fact:

> no source turn vanished from the extraction accounting layer.

## Required adversarial tests

- one missing source turn;
- duplicated disposition for one source turn;
- disposition for an unknown turn;
- duplicate disposition ID;
- extraction revision mismatch;
- duplicate authoritative turn ID;
- empty source/empty ledger is complete;
- input order/permutation cannot change diagnostic semantics;
- fake/manual counts cannot influence computed coverage (there are no trusted count fields);
- completion assertion fails closed for every invalid case.
