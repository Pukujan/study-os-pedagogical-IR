# Threat Model — PIR v0.1

## Assets to protect

1. exact learner/tutor source evidence;
2. source ordering and context boundaries;
3. evidence-status truth (`verbatim` vs reconstructed/derived);
4. pedagogically required intermediate states;
5. representation state and negative constraints;
6. learner outcome provenance;
7. deterministic trajectory semantics;
8. schema/version history;
9. separation from benchmark oracles/hidden holdouts.

## Primary adversaries

The threat model includes accidental and model-induced failures, not only malicious actors.

- normal text processing that mutates source bytes;
- parser edge cases;
- lossy semantic summarization;
- LLM hallucination/inference during extraction;
- developer "cleanup" of awkward but calibrated states;
- schema drift;
- nondeterministic serialization;
- benchmark contamination;
- over-broad abstraction/generalization;
- under-specified optional-field schemas;
- incorrect persistence/migration code.

## Threats and required defenses

### T1 — source normalization

Examples: CRLF→LF, Unicode normalization, `.strip()`, trailing newline insertion.

Defense:

- ingest `bytes`;
- hash original bytes before decoding;
- byte offsets only;
- round-trip and metamorphic tests.

### T2 — wrong occurrence of repeated text

Text-search provenance can resolve the wrong duplicate sentence.

Defense:

- evidence ref = artifact identity + exact byte range;
- optional span digest for local integrity;
- never use quoted text as identity.

### T3 — delimiter/parser confusion

A role delimiter appears inside code or quoted transcript content.

Defense:

- purpose-built deterministic transcript-envelope parser when parser work begins;
- adversarial delimiter/code-fence fixtures;
- parser output validated against source byte coverage/order.

### T4 — semantic compression

Extractor turns `A -> B -> C` into `A -> C` because B seems redundant.

Defense:

- intermediate states source-backed and identity-bearing;
- explicit required-path trajectory semantics;
- deletion/shortcut mutation tests.

### T5 — invented bridge

A missing edge is inferred because it is pedagogically plausible.

Defense:

- accepted transitions require provenance;
- unresolved transition status;
- compiler rejects unresolved-as-accepted.

### T6 — representation drift

Tutor/extractor preserves the concept but drops chart/index/box/notation state.

Defense:

- structured `RepresentationState`;
- preserve/forbid mutation contracts;
- representation deletion mutations.

### T7 — answer/future information leakage

A hint/explanation reveals the target answer or future concept.

Defense:

- explicit negative constraints;
- probe answer-reveal policy;
- deterministic literal/structural checks where possible;
- independent benchmarker for semantic leakage dimensions.

### T8 — false learner outcome

Tutor intent or model confidence creates `correct` without learner evidence.

Defense:

- outcomes require learner turn/evidence refs;
- outcome cannot be authored by a tutor-only source;
- meta/partial/incorrect branches cannot advance without explicit rules.

### T9 — version reinterpretation

An old object is loaded under new semantics without changing its version.

Defense:

- immutable historical schemas;
- explicit version readers;
- unknown versions fail closed;
- migration creates new objects.

### T10 — canonicalization drift

Same object hashes differently across OS/runtime versions.

Defense:

- explicit canonical JSON spec;
- UTF-8, sorted keys, no insignificant whitespace;
- no floats/timestamps/random IDs in semantic digest inputs unless canonically specified;
- golden digest fixtures.

### T11 — schema/Python divergence

Python accepts data JSON Schema rejects or vice versa.

Defense:

- independent parity tests for fixtures and generated cases;
- semantic validators kept outside either serialization layer.

### T12 — fake completeness

Extractor reports 100% coverage while assigning everything irrelevant/meta or duplicating entries.

Defense:

- exactly one primary disposition per source turn/extraction revision;
- coverage computed from source turn IDs, not reported counters;
- duplicate/missing detection;
- distribution/concept audits in private historical replay.

### T13 — false immutability

Frozen top-level objects contain mutable child dictionaries/lists.

Defense:

- immutable tuples/frozensets or defensive serialization boundaries;
- mutation-after-construction tests.

### T14 — hidden holdout contamination

Expected hidden answers leak into PIR repo, prompts or candidate-visible fixtures.

Defense:

- no hidden oracles in this public repo;
- private holdout boundary outside PIR/benchmarker candidate inputs;
- contaminated cases permanently retired to public regression.

### T15 — FOSSIL coupling failure

PIR cannot run/audit without FOSSIL or FOSSIL semantics redefine PIR.

Defense:

- core has no FOSSIL dependency;
- later adapter maps evidence/provenance only;
- Study OS/PIR remain pedagogical semantic authority.

### T16 — horizontal scope explosion

A generic ontology/framework is built before historical fidelity works.

Defense:

- new primitive requires concrete September-4 evidence or invariant justification;
- v0.1 acceptance gate blocks controller/general-domain work.

## Trust assumptions

PIR assumes that an evidence artifact supplied as authoritative is the intended captured source. SHA-256 verifies identity/integrity, not whether the original capture omitted hidden platform context.

Historical ChatGPT transcripts can therefore be labeled exact **visible** evidence, not retroactively complete hidden model context.

## Security/privacy note

The public repository contains no raw private learner transcript. Private runners are responsible for access control, encryption/storage policy and retention of sensitive evidence.
