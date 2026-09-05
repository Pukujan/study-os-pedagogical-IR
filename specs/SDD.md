# SDD — Pedagogical IR v0.1

## Architecture

```text
raw bytes
   ↓
EvidenceArtifact
   ↓
EvidenceSpan
   ↓
Turn
   ↓
ContextFrame
   ↓
RepresentationState + PedagogicalState
   ↓
Operation / Probe / LearnerOutcome
   ↓
Transition / CorrectionBranch
   ↓
Trajectory
```

The implementation must preserve the evidence/derived boundary throughout this pipeline.

## Trust layers

### L0 — source bytes

Canonical evidence identity is SHA-256 over original bytes. L0 has no text normalization semantics.

### L1 — evidence addressing

`EvidenceArtifact`, `EvidenceSpan`, and `Turn` refer to exact source bytes. Byte ranges are half-open: `[start, end)`.

### L2 — context frames

`ContextFrame` is an ordered reference set describing the exact visible/evidentiary context relevant to a turn or derived state. It stores refs and a canonical digest rather than duplicating source text.

### L3 — derived state

`RepresentationState` and `PedagogicalState` are interpretations. They MUST declare evidence status and provenance refs.

### L4/L5 — executable pedagogy

Operations, probes, outcomes, transitions, correction branches and trajectories are deterministic IR objects. They are source-backed constraints, not generated prose.

## Identity

Stable IDs must be independent from persistence row IDs and process randomness.

v0.1 uses explicit caller-provided stable IDs plus canonical SHA-256 digests for integrity/reproducibility. Content-derived IDs may be introduced only after their canonicalization semantics are frozen.

## Evidence status

Initial values:

- `verbatim`
- `reconstructed`
- `derived`

Rules:

- `verbatim` claims require exact resolvable source bytes.
- a reconstructed source cannot be promoted to verbatim by confidence or later annotation;
- derived objects retain provenance to source/derived inputs;
- provenance status and semantic confidence are separate concerns.

## Turn disposition

Every source turn must receive exactly one primary extraction disposition for a given extraction revision:

- `golden`
- `failure`
- `learner_correction`
- `repair`
- `exercise`
- `validation`
- `meta`
- `duplicate`
- `unresolved`

Multiple secondary annotations may reference the same turn. Primary disposition is a coverage/accounting mechanism, not a complete semantic classification.

## RepresentationState

Representation state is structured and must support at least:

- representation family;
- visible components;
- hidden components;
- symbol/label bindings;
- immutable components;
- allowed mutations;
- forbidden mutations;
- answer-visibility policy.

The schema should not hardcode sliding-window fields such as `box_start`; domain-specific values belong in typed/keyed state fields until a repeated cross-domain primitive is demonstrated.

## PedagogicalState

A pedagogical state captures:

- known/established relations;
- current target relation or skill;
- active representation reference;
- learner evidence known at that point;
- forbidden future concepts/information;
- assistance/realization constraints where evidenced;
- provenance.

It must not contain a free-form model-generated summary as its sole semantics.

## Operations

Initial operation enum:

- `explain`
- `bridge`
- `introduce`
- `probe`
- `validate`
- `correct`
- `retry`
- `verify`
- `generalize`
- `assemble`
- `change_representation`

Operation types may grow only with evidence/invariant justification.

## Probe contract

A probe/question contract declares:

- target operation/learner production;
- realization mode: `frozen`, `parameterized`, `generative`;
- immutable prompt semantics;
- mutable parameters and their constraints;
- answer-reveal policy;
- required representation state;
- forbidden concepts/information;
- success evidence rule.

The exact target answer must not be exposed to a runtime renderer when the contract forbids answer reveal.

## Learner outcomes

Initial bounded enum:

- `correct`
- `partial`
- `incorrect`
- `meta`
- `hint_request`
- `unresolved`

Outcomes are observations/classifications tied to actual learner evidence. A tutor message cannot create a learner outcome.

## Transition

A transition declares:

- source state;
- destination state;
- operation;
- authorized semantic delta;
- fields/relations that must be preserved;
- forbidden deltas;
- probe contract if applicable;
- required evidence refs;
- allowed outcome-dependent next branches;
- transition status (`accepted` or `unresolved` in v0.1).

A source-backed required intermediate transition cannot be bypassed by a direct edge unless an independently accepted alternate path is explicitly represented.

## CorrectionBranch

Correction behavior is first-class:

```text
probe
 ├─ correct   → validate/advance
 ├─ partial   → preserve-correct + targeted repair
 ├─ incorrect → correction → retry → verify
 └─ meta/hint → non-mastery branch
```

The exact branch sequence is represented as trajectory structure, not prose notes.

## Trajectory

A trajectory is an ordered/branching set of state and transition refs with explicit entry states and path requirements.

v0.1 does not use generic graph reachability to authorize runtime shortcuts. Required path order is explicit.

## Canonical serialization

Canonical JSON is defined in `specs/CANONICALIZATION.md`. Semantic digests must be deterministic across operating systems and process runs.

## Persistence

The core library must not require a database. Persistence adapters may use SQLite/FOSSIL later. In-memory validated objects and JSON fixtures are sufficient for v0.1 correctness testing.

## Validation layers

1. JSON Schema Draft 2020-12 contracts;
2. strict Python boundary models where implemented;
3. semantic validators that schemas cannot express;
4. fixture tests;
5. property/metamorphic tests;
6. mutation testing of critical validators/compiler;
7. independent `study-os-benchmarker` evaluation.

## Failure behavior

Fail closed on:

- unknown schema version;
- malformed/negative/out-of-range byte span;
- artifact digest mismatch;
- verbatim claim without exact resolvable evidence;
- missing required provenance;
- duplicate primary disposition for same turn/extraction revision;
- incomplete coverage when extraction claims completion;
- unsupported direct transition bypassing required state;
- unresolved edge compiled as accepted;
- non-deterministic canonical output.

No automatic repair is performed in the trust kernel.

## Compatibility

- Historical schema files are immutable after release.
- Breaking semantics require a new versioned schema ID/file.
- Readers support explicit versions; unknown versions fail.
- Writers emit one declared current version per object family.
- Migration produces new derived objects; it does not rewrite original evidence or historical compiled artifacts.
