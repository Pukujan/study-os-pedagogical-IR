# Study OS Pedagogical IR

Canonical, versioned Pedagogical Intermediate Representation (PIR) for Study OS.

PIR is the trust boundary between raw learner evidence and deterministic pedagogical control. Its job is to preserve the path-dependent structure that ordinary summarization tends to erase: exact evidence provenance, representation state, question function, learner outcome, negative constraints, correction/retry/verify branches, and source-backed intermediate transitions.

## Core rule

> The pedagogical path itself is data.

An intermediate state may not be deleted merely because its endpoints are semantically equivalent.

## Repository boundary

This repository owns:

- versioned PIR schemas and semantics;
- evidence-reference contracts;
- byte-addressed Artifact/Span/Turn/ContextFrame models;
- RepresentationState and PedagogicalState;
- operations, probes, learner outcomes and transitions;
- correction branches and trajectories;
- deterministic validation/compiler logic;
- canonicalization and compatibility rules;
- synthetic/redacted fixtures for PIR correctness.

This repository does **not** own:

- Study OS session/runtime orchestration;
- private learner transcripts in Git;
- benchmark scoring or donor architecture comparison;
- hidden holdout answers;
- LLM rendering;
- curriculum generation;
- FOSSIL internals.

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
```

Every abstraction above L0 is derived. Every derived object must retain a resolvable path back to exact evidence.

## PIR v0.1 scope

PIR v0.1 is intentionally narrow: it must be strong enough to losslessly compile the September 4 sliding-window pedagogy calibration before expanding horizontally.

Success requires an authorized local/private run to:

1. preserve source bytes exactly;
2. reconstruct every verbatim turn exactly;
3. account for every source turn;
4. source every accepted derived state/edge;
5. recover the complete calibrated path, including `enumerate(a)` and failure→correction→repair sequences;
6. reject semantic-shortcut mutations such as deleting `S[0] -> S[i]`;
7. emit `UNRESOLVED` rather than inventing unsupported transitions;
8. reproduce byte-identical canonical compiled output from identical inputs and compiler revision.

## Companion repositories

- Study OS program tracker: https://github.com/Pukujan/Study-os/issues/65
- PIR tracker: https://github.com/Pukujan/study-os-pedagogical-IR/issues/1
- Independent evaluator: https://github.com/Pukujan/study-os-benchmarker/issues/1

The benchmarker evaluates PIR independently. PIR must not contain benchmark expected answers or scoring logic.

## Development order

```text
specification
↓
verification traceability
↓
versioned schemas
↓
byte-exact evidence kernel
↓
context/state IR
↓
pedagogical transitions
↓
trajectory compiler
↓
September-4 compilation gate
```

No production controller or LLM renderer is built here before the PIR kernel is proven against those gates.
