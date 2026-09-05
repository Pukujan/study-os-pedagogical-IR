# PDD — Pedagogical IR v0.1

## Product problem

Study OS needs to reproduce learner-calibrated pedagogy without relying on an LLM to re-infer the lesson from a large transcript. Existing summaries/goldens can preserve endpoints while losing required intermediate bridges, question behavior, representation state, correction paths, wording constraints, or learner-visible context.

PIR converts raw evidence into a small executable pedagogical representation while keeping every abstraction auditable back to exact source evidence.

## Primary user value

Study OS should be able to answer three different questions reliably:

1. **Historical fidelity:** what exactly was calibrated and accepted?
2. **Controlled execution:** what single pedagogical state/transition is authorized next?
3. **Visible realization fidelity:** did the learner actually see the representation/context that the IR required?

PIR v0.1 remains anchored in historical fidelity, but an experimental deterministic replay harness now exercises the second and third questions so that incorrect abstractions are discovered before the schema is frozen.

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

### P8 — learner-visible output is a falsification surface

A hidden state flag such as `preserve problem_anchor` is insufficient if the runtime can stop visibly showing the problem. Required context/representation must survive into the actual learner-facing turn.

### P9 — grading authority is not renderer authority

Canonical answers and deterministic grading contracts are controller-only. A renderer may receive the authorized pedagogical turn but must not receive hidden answers that violate the probe's reveal policy.

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
- canonical deterministic serialization/versioning;
- renderer-safe turn contracts separated from controller-only assessment data;
- explicit outcome-dependent routes for the bounded source-backed replay paths.

The last two capabilities are currently exercised through experimental v0 runtime/trajectory types. Passing current fixtures does not promote those types to stable G2 semantics.

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

## Active falsification frontier

The current executable replay is intentionally being used to discover what the static IR still fails to express.

Current source/runtime pressure includes:

- prove the original difficult problem remains visibly present where the calibrated lesson requires it;
- extend the executable foundation from `k` through `i` as box start and `sum[i]`;
- support the observed `partial` path where the learner identifies the correct box contents but has not yet computed their sum;
- determine whether language/register abstraction is a separate state dimension from representation abstraction.

The language/register question is explicitly unresolved. Examples such as `number -> element -> a[i]` or `box -> window` suggest that terminology changes may be pedagogical deltas, but no lexical ontology may be added merely because educational theory makes the idea plausible. First demonstrate a concrete source/runtime mutation that current concept/representation constraints cannot express cleanly.

## Non-goals

v0.1 does not attempt:

- production tutoring;
- general automatic curriculum generation;
- general learner modeling;
- LLM training/fine-tuning;
- vector retrieval;
- donor-system integration;
- population-level educational efficacy;
- formal proof of the entire system;
- FOSSIL as a runtime dependency;
- a universal semantic-wave/CRA/linguistic pedagogy ontology.

The experimental local replay harness is a verification instrument, not a claim that production tutoring has been built.

## Success metrics

The first release candidate must satisfy deterministic properties rather than subjective quality claims:

- exact source-byte round trip: 100%;
- exact verbatim-turn reconstruction: 100%;
- source-turn disposition coverage: 100%;
- accepted golden state/edge with resolvable provenance: 100%;
- unsupported inferred edges: 0;
- known semantic-compression mutations rejected: 100% of required mutation corpus;
- deterministic compile reproducibility: byte-identical output for identical inputs/compiler revision;
- hidden grading answers absent from renderer-safe contracts when reveal is forbidden;
- required learner-visible representation/context preserved in replay fixtures.

Human/prospective learning evaluation is owned by the independent benchmarker after historical fidelity is stable.

## Assurance and documentation boundary

PAM supplies pinned methodology contracts and validators; PIR owns project-specific live state.

- `assurance/HANDOFF_STATE.json` is the mutable current handoff.
- `assurance/checkpoints/*.json` are immutable historical snapshots at material boundaries.
- generated README/status sections are synchronized from durable project state and fail CI on drift;
- PDD/SDD/threat/verification specifications remain human-reviewed because semantic design decisions must not be inferred from status metadata.

Historical checkpoints never override live repository or CI truth.

## Release gate

No v0.1 release until the public/synthetic kernel tests pass and an authorized private September-4 replay demonstrates all applicable success metrics above. Experimental replay types must remain explicitly experimental until complete-golden pressure justifies their stable semantics.
