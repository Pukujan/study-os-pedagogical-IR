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
   ↓
experimental deterministic replay/controller
   ├─ controller-only assessment oracle
   └─ renderer-safe turn contract
              ↓
       learner-visible output
```

The implementation must preserve the evidence/derived boundary throughout this pipeline. The experimental replay layer exists to falsify the proposed IR semantics before stable G2 promotion; it is not the production Study OS runtime.

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

### Experimental replay layer

The current experimental trajectory/runtime implementation tests whether the proposed L3-L5 contracts are sufficient to produce the learner-visible behavior that was calibrated.

The replay layer must preserve this authority split:

```text
approved pedagogical trajectory
        ↓
deterministic controller
        ├─ assessment registry     (controller only)
        └─ renderer turn contract  (safe to expose)
                  ↓
            renderer / console
                  ↓
               learner
```

The renderer cannot choose an unauthorized next pedagogical node. The renderer-safe contract cannot contain hidden expected answers or other grading-oracle material when answer reveal is forbidden.

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

The full transcript has already falsified a mandatory-window-box assumption: `enumerate(a)` is a valid aligned index/number/pair representation without a window box. Representation contracts therefore must permit non-window visual states and may explicitly forbid irrelevant representation components.

## Persistent learner-visible context

A component marked as preserved in internal state is not necessarily visible to the learner. The replay runtime must distinguish persistent learner-visible context from hidden controller state.

The motivating failure is the full difficult problem anchor: a trajectory can say `preserve problem_anchor` while a console renderer stops showing the problem. That must be treated as a realization failure.

The current frontier is to wire the explicit replay-context artifact into renderer-safe output and test the actual rendered surface.

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

The exact target answer must not be exposed to a runtime renderer when the contract forbids answer reveal. Answer-leak checks must inspect the whole learner-visible structured surface where applicable, not just prompt text.

## Learner outcomes

Initial bounded enum:

- `correct`
- `partial`
- `incorrect`
- `meta`
- `hint_request`
- `unresolved`

Outcomes are observations/classifications tied to actual learner evidence. A tutor message cannot create a learner outcome.

The current runtime deterministically classifies bounded structured integer/integer-sequence probes. Open natural-language classification remains a future bounded adapter problem; it must not silently become controller authority.

`partial` is a real control outcome, not a synonym for incorrect. The next source-backed runtime extension must represent the case where the learner identifies the correct `sum[i]` box contents but has not performed the arithmetic; that path should preserve the correct sub-result and ask only the missing arithmetic step.

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

Historical learner meta-turns may establish runtime policy without becoming literal future runtime gates. For example, a historical learner saying that two exercises are enough can justify a stopping policy without requiring every future learner to reproduce that exact phrase.

## Trajectory

A trajectory is an ordered/branching set of state and transition refs with explicit entry states and path requirements.

v0.1 does not use generic graph reachability to authorize runtime shortcuts. Required path order is explicit.

The experimental trajectory validator currently treats unknown refs, ambiguous control, duplicate outcome routes, unreachable states and cycles as fail-closed errors. Repeated-error behavior is not invented when the source does not establish it.

## Language/register abstraction — unresolved design question

Representation abstraction and learner-facing language abstraction may be distinct pedagogical dimensions.

Examples under investigation include:

```text
number → number at an index → element → a[i]
box → selected group → window
box total → window sum → S[i]
```

A renderer can preserve the correct chart while still prematurely replacing grounded learner language with disciplinary jargon. That would be semantically valid but may be pedagogically invalid.

No first-class lexical/register schema is accepted yet. Before adding one, run a source-backed mutation/falsification test:

1. show that the current contracts permit an unwanted terminology switch;
2. show that existing `disclosed_concepts` / `forbidden_concepts` cannot express the constraint cleanly;
3. add only the smallest experimental lexical state/bridge required;
4. reject premature-term mutations while preserving existing trajectory regressions.

Educational frameworks such as progressive formalization or semantic density may motivate the experiment but are not themselves IR schemas.

## Canonical serialization

Canonical JSON is defined in `specs/CANONICALIZATION.md`. Semantic digests must be deterministic across operating systems and process runs.

## Persistence

The core library must not require a database. Persistence adapters may use SQLite/FOSSIL later. In-memory validated objects and JSON fixtures are sufficient for v0.1 correctness testing.

## Documentation and checkpoint state

PAM is pinned assurance methodology, not project state storage.

- `assurance/HANDOFF_STATE.json` is the one mutable `current` handoff.
- `assurance/checkpoints/*.json` are immutable PAM `historical_checkpoint` snapshots.
- `docs/repository-state.json` contains bounded shared facts for generated status documentation.
- `make docs-sync` rewrites machine-owned README/status content.
- `make docs-check` is part of `make check` and fails on drift.
- design specs remain human-reviewed; generated status cannot silently change architectural semantics.

Every current handoff and archived checkpoint is validated against the pinned PAM revision in assurance CI. Live repository and CI observations supersede stale checkpoint observations.

## Validation layers

1. JSON Schema Draft 2020-12 contracts;
2. strict Python boundary models where implemented;
3. semantic validators that schemas cannot express;
4. fixture tests;
5. property/metamorphic tests;
6. mutation testing of critical validators/compiler;
7. independent `study-os-benchmarker` evaluation;
8. learner-visible deterministic replay used as an intended-use falsification surface;
9. PAM/documentation drift validation for project continuity rather than pedagogy correctness.

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
- non-deterministic canonical output;
- hidden grading answer exposed to a renderer-safe contract;
- required learner-visible context lost in a replay fixture;
- generated project documentation drifting from its durable state sources.

No automatic repair is performed in the trust kernel.

## Compatibility

- Historical schema files are immutable after release.
- Breaking semantics require a new versioned schema ID/file.
- Readers support explicit versions; unknown versions fail.
- Writers emit one declared current version per object family.
- Migration produces new derived objects; it does not rewrite original evidence or historical compiled artifacts.
- Historical PAM checkpoints are never rewritten to match newer project state.
