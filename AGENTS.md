# AGENTS.md

Non-negotiable rules for humans and coding agents modifying this repository.

## 1. Evidence is not interpretation

- Raw evidence is immutable.
- Derived state, annotations, trajectories and golden nodes are never allowed to overwrite source evidence.
- Verbatim/reconstructed/derived status must remain explicit.
- Reconstructed content must never silently satisfy a verbatim requirement.

## 2. Operate on bytes at the evidence layer

- Hash original bytes.
- Store byte offsets, not character offsets.
- Do not call `.strip()`, normalize Unicode, rewrite line endings, or otherwise mutate evidence before hashing/spanning.
- Text decoding is a presentation/derived concern.

## 3. The path is data

- Do not collapse a source-backed `A -> B -> C` trajectory into `A -> C` because B looks semantically redundant.
- Do not infer missing pedagogical edges. Mark them unresolved.
- Historical failure/correction/repair paths are first-class evidence, not noise to summarize away.

## 4. Negative constraints are first-class

PIR must be able to represent what must **not** happen yet:

- forbidden future concepts;
- answer-reveal restrictions;
- forbidden representation changes;
- immutable notation;
- forbidden transition shortcuts.

Do not replace these with prose-only comments.

## 5. No hidden benchmark contamination

- Do not store sealed hidden-holdout answers here.
- Do not copy benchmark-oracle data from `study-os-benchmarker` into PIR fixtures.
- Public fixtures must be synthetic or explicitly redacted/declassified.

## 6. No private transcript commits

Raw/private learner transcript data must not be committed to this public repository.

Private historical replay is performed through an authorized local/private runner that consumes the public PIR package/contracts.

## 7. Versioning is append-only at the semantic level

- Published schema semantics are immutable.
- Breaking semantic changes require a new schema version.
- Do not silently reinterpret old fixtures under new semantics.
- Readers may support old versions explicitly; writers emit only declared current versions.

## 8. Tests are part of the specification

Every hard invariant must map to:

- at least one positive fixture/property;
- at least one negative/adversarial test when meaningful;
- a documented failure condition.

Do not weaken tests merely to make a change pass. If semantics must change, update the specification/version first.

## 9. Keep PIR independent

PIR must work without:

- FOSSIL;
- Study OS runtime;
- an LLM provider;
- a database server;
- a vector store;
- donor tutoring frameworks.

Adapters may be added later at explicit boundaries.

## 10. Scope control

PIR v0.1 is not a generic education ontology. Add only primitives required by:

1. hard evidence/provenance invariants; or
2. the September-4 calibrated trajectory.

Before adding a new abstraction, identify the concrete historical state/transition or invariant that requires it.

## 11. Fail closed

Unknown schema versions, unresolved evidence refs, impossible byte spans, unsupported provenance claims, and incomplete required fields fail explicitly.

No best-effort coercion at trust boundaries.

## 12. Determinism

Core validation/compiler behavior must not depend on current time, randomness, network access, unordered iteration, generated UUIDs, or environment-specific paths.

Volatile metadata may exist outside semantic identity.

## 13. Continuity, generated docs, and PAM checkpoints

Before substantive mutation:

1. read `assurance/HANDOFF_STATE.json` and `assurance/NEXT_SESSION_HANDOFF.md`;
2. reconcile their observations against live `main`, CI, issues, and referenced component revisions;
3. let live state win when the handoff is stale.

Documentation rules:

- `docs/repository-state.json`, the current PAM handoff, and archived checkpoints drive machine-owned project-status documentation;
- run `make docs-sync` after changing those inputs;
- `make docs-check` is part of `make check` and must remain green;
- do not hand-edit text inside generated README/status blocks;
- PDD/SDD/threat/verification specs are human-reviewed semantic documents and must not be rewritten automatically from status metadata.

Checkpoint rules:

- `assurance/HANDOFF_STATE.json` is the single mutable `current` handoff;
- `assurance/checkpoints/*.json` are immutable `historical_checkpoint` snapshots at material boundaries;
- never overwrite or retroactively clean up a historical checkpoint;
- create a new checkpoint when a later milestone materially changes the resumable state;
- hidden holdout/oracle data is forbidden from current handoffs and historical checkpoints;
- every checkpoint must validate against the pinned PAM handoff schema in CI.
