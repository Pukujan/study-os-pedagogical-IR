# PDD — Pedagogical IR v0.1

## Product problem

Study OS needs to reproduce learner-calibrated pedagogy without relying on an LLM to re-infer the lesson from a large transcript. Existing summaries/goldens can preserve endpoints while losing required intermediate bridges, question behavior, representation state, correction paths, or wording constraints.

PIR converts raw evidence into a small executable pedagogical representation while keeping every abstraction auditable back to exact source evidence.

## Primary user value

Study OS should be able to answer two different questions reliably:

1. **Historical fidelity:** what exactly was calibrated and accepted?
2. **Controlled execution:** what single pedagogical state/transition is authorized next?

PIR v0.1 focuses on the first question and provides the representation needed for the second.

## Product principles

### P1 — evidence before interpretation

Raw bytes and byte-resolvable spans are authoritative. Derived pedagogical interpretations are versioned projections.

### P2 — path-sensitive pedagogy

Pedagogical equivalence is stricter than semantic/program equivalence. An intermediate bridge may carry learner-critical explanatory information even when endpoints are mathematically equivalent.

### P3 — representation state matters

The visible chart/notation/box/index state is part of the pedagogical state, not presentation decoration.

### P4 — negative information matters

The IR must encode forbidden future concepts, answer-leak restrictions, immutable notation and forbidden representation mutations.

### P5 — learner evidence gates progression

A learner outcome is not inferred from tutor intent. Correct/partial/incorrect/meta/hint-request/unresolved are explicit evidence-backed outcomes.

### P6 — no invented edges

If evidence does not establish a bridge, the IR says unresolved. A compiler cannot repair the historical trajectory by intuition.

### P7 — narrow first, deep first

v0.1 is validated on the complete September-4 sliding-window calibration before attempting general curriculum generation or broad-domain abstractions.

## v0.1 capabilities

PIR v0.1 must represent:

- immutable evidence artifacts and byte spans;
- exact source turns and ordered context frames;
- explicit evidence status;
- turn disposition coverage;
- representation state;
- pedagogical state;
- operations such as explain/bridge/probe/validate/correct/retry/verify/generalize/assemble/representation-change;
- probe/question contracts;
- frozen/parameterized/generative realization policy;
- mutation permissions;
- learner outcomes;
- source-backed transitions;
- correction branches;
- trajectories with required intermediate nodes;
- unresolved edges;
- canonical deterministic serialization/versioning.

## Historical acceptance target

The September-4 calibration is the v0.1 reference workload because it contains:

- repeated learner corrections to tutor control flow;
- explicit representation preservation requirements;
- `enumerate(a)` explanation/exercise/validation calibration;
- `S[0] -> S[i]` bridge calibration;
- concrete-index-before-generalization sequence;
- `if i != 0 -> else` bridge;
- boundary/break progression;
- arbitrary-k/range/x nested-state progression;
- correction/retry/verify paths;
- known examples of answer leakage and premature advancement.

## Non-goals

v0.1 does not attempt:

- production tutoring;
- automatic curriculum generation;
- general learner modeling;
- LLM training/fine-tuning;
- vector retrieval;
- donor-system integration;
- population-level educational efficacy;
- formal proof of the entire system;
- FOSSIL as a runtime dependency.

## Success metrics

The first release candidate must satisfy deterministic properties rather than subjective quality claims:

- exact source-byte round trip: 100%;
- exact verbatim-turn reconstruction: 100%;
- source-turn disposition coverage: 100%;
- accepted golden state/edge with resolvable provenance: 100%;
- unsupported inferred edges: 0;
- known semantic-compression mutations rejected: 100% of required mutation corpus;
- deterministic compile reproducibility: byte-identical output for identical inputs/compiler revision.

Human/prospective learning evaluation is owned by the independent benchmarker after historical fidelity is stable.

## Release gate

No v0.1 release until the public/synthetic kernel tests pass and an authorized private September-4 replay demonstrates all success metrics above.
