# Study OS Pedagogical IR

Canonical, versioned Pedagogical Intermediate Representation (PIR) for Study OS v2.

PIR is the trust boundary between raw learner evidence and deterministic pedagogical control. Its job is to preserve the path-dependent structure that ordinary summarization tends to erase: exact evidence provenance, representation state, question function, learner outcome, negative constraints, correction/retry/verify branches, and source-backed intermediate transitions.

## Core rule

> The pedagogical path itself is data.

An intermediate state may not be deleted merely because its endpoints are semantically equivalent.

<!-- BEGIN GENERATED PROJECT STATUS -->
## Current project status

> Generated from `docs/repository-state.json`, the PAM current handoff, and historical checkpoints. Run `make docs-sync` after changing those inputs. `make docs-check` fails on drift. Design specs remain human-reviewed.

- Program: **Study OS v2 Pedagogical IR**
- Stability: **experimental evidence-backed runtime/schema falsification**
- Current phase: **PIR-0 executable golden replay and runtime/schema falsification**
- Historical checkpoints: **1**

### Landed and tested capabilities

- byte-exact evidence and extraction accounting
- max-sum S[0] to S[i] vertical proof
- enumerate(a) vertical proof with visual answer-leak constraints
- branching foundations trajectory with correction/retry paths
- controller-only assessment registry separated from renderer-safe turn contracts
- deterministic local grading for current integer and integer-sequence probes
- generic local trajectory replay command
- persistent full-problem replay context artifact

### Current next action

Read assurance/NEXT_SESSION_HANDOFF.md, reconcile live main/CI, then wire persistent full-problem context into learner-visible renderer output. Extend the source-backed executable trajectory through i as box start, moved-box exercises, same-chart validation, and sum[i], including the observed PARTIAL path where correct box contents are given without the arithmetic sum. After replay is faithful through sum[i], run a small lexical/register falsification experiment before deciding whether first-class language state is needed.

### Not yet proven

- persistent full-problem context is visibly rendered on every required learner turn
- executable i-moves-box and sum[i] section with PARTIAL routing
- complete canonical September-4 golden
- automatic raw problem plus learner state to PIR decomposition
- lexical/register state as a required PIR primitive
- Luna masked, sealed, or prospective generalization results
- production tutoring or learning efficacy
<!-- END GENERATED PROJECT STATUS -->

## Repository boundary

This repository owns:

- versioned PIR schemas and semantics;
- evidence-reference contracts;
- byte-addressed Artifact/Span/Turn/ContextFrame models;
- representation and pedagogical-state experiments derived from evidence;
- operations, probes, learner outcomes and transitions;
- correction branches and trajectories;
- deterministic validation/compiler logic;
- canonicalization and compatibility rules;
- synthetic/redacted fixtures for PIR correctness;
- an experimental deterministic replay/controller harness used to falsify PIR semantics;
- renderer-safe turn contracts and controller-only assessment contracts.

This repository does **not** own:

- production Study OS session/persistence orchestration;
- private learner transcripts in Git;
- benchmark scoring or donor architecture comparison;
- hidden holdout answers;
- an unconstrained LLM tutor;
- general automatic curriculum generation;
- FOSSIL internals.

The experimental replay runtime is a test instrument for proving that PIR can produce the intended learner-visible behavior. It is not yet the production tutor.

## Layer model

```text
L0  immutable source bytes
          ↓
L1  EvidenceArtifact / EvidenceSpan / Turn
          ↓
L2  ContextFrame
          ↓
L3  RepresentationState / PedagogicalState
          ↓
L4  Operation / Probe / Outcome / Transition / CorrectionBranch
          ↓
L5  Trajectory
          ↓
experimental deterministic replay/controller
          ↓
renderer-safe learner turn
```

Every abstraction above L0 is derived. Every derived object must retain a resolvable path back to exact evidence.

## PIR v0.1 scope

PIR v0.1 is intentionally narrow: it must be strong enough to losslessly compile and faithfully replay the September 4 sliding-window pedagogy calibration before expanding horizontally.

Success requires an authorized local/private run to:

1. preserve source bytes exactly;
2. reconstruct every verbatim turn exactly;
3. account for every source turn;
4. source every accepted derived state/edge;
5. recover the complete calibrated path, including `enumerate(a)` and failure→correction→repair sequences;
6. reject semantic-shortcut mutations such as deleting `S[0] -> S[i]`;
7. emit `UNRESOLVED` rather than inventing unsupported transitions;
8. reproduce byte-identical canonical compiled output from identical inputs and compiler revision;
9. execute the approved path without exposing controller-only grading answers to the renderer;
10. preserve required learner-visible context, not merely hidden structural flags.

## Current local replay

The current public foundations trajectory can be replayed locally:

```bash
python tools/replay_trajectory.py \
  --trajectory fixtures/public/sliding-window-foundations/trajectory.v0.json \
  --assessments fixtures/public/sliding-window-foundations/assessments.v0.json
```

This currently exercises only the encoded beginning of the calibrated lesson. It is not yet the complete sliding-window tutor and does not perform raw-problem decomposition.

## Documentation and checkpoints

PAM is an assurance methodology, not an adopter runtime. PIR owns its live project state.

- `assurance/HANDOFF_STATE.json` is the mutable PAM `current` handoff.
- `assurance/checkpoints/*.json` contains immutable `historical_checkpoint` snapshots at material milestones.
- `assurance/NEXT_SESSION_HANDOFF.md` is the detailed human continuation document.
- `docs/repository-state.json` contains small shared status facts used for generated documentation.
- `make docs-sync` regenerates machine-owned status sections.
- `make docs-check` fails when generated documentation drifts from current state.
- PDD/SDD/threat/verification specs remain human-reviewed because semantic design changes must not be silently generated from status metadata.

Historical checkpoints never override live repository/CI truth.

## Companion repositories

- Study OS program tracker: https://github.com/Pukujan/Study-os/issues/65
- PIR tracker: https://github.com/Pukujan/study-os-pedagogical-IR/issues/1
- Independent evaluator: https://github.com/Pukujan/study-os-benchmarker/issues/1
- Blind/holdout protocol: https://github.com/Pukujan/study-os-benchmarker/issues/2

The benchmarker evaluates PIR independently. PIR must not contain benchmark expected answers or scoring logic.

## Development order

```text
source evidence
↓
lossless extraction/accounting
↓
source-backed golden reconstruction
↓
small semantic/representation slices
↓
adversarial independent benchmarks
↓
branching executable trajectory
↓
deterministic local replay
↓
full September-4 replay
↓
raw problem + learner state → candidate PIR compiler
↓
masked / sealed / prospective evaluation
```

New abstractions are added only when source evidence or executable replay falsifies the existing representation. Green bookkeeping alone is not permission to expand the ontology.
