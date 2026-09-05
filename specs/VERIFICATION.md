# Verification Plan — PIR v0.1

This document is normative. Every hard PIR invariant must have a concrete verification strategy.

## Test classes

- **U** — deterministic unit/fixture test
- **P** — property-based test (Hypothesis)
- **M** — metamorphic test
- **A** — adversarial negative fixture
- **MU** — implementation mutation test (`mutmut`)
- **R** — historical/private replay
- **B** — independent `study-os-benchmarker` check
- **V** — learner-visible replay/output check
- **C** — continuity/documentation/checkpoint validation
- **X** — optional CrossHair pure-contract check

## Evidence invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| E1 | Artifact digest is SHA-256 of original bytes | U/P: arbitrary bytes digest matches stdlib | M: one-byte change changes digest |
| E2 | Ingestion never normalizes evidence | P: arbitrary bytes round-trip | A: CRLF/LF, trailing spaces, BOM, Unicode/emoji/zero-width cases remain distinct |
| E3 | Span uses valid half-open byte bounds | U/P/X: `0 <= start <= end <= len(bytes)` | A: negative/reversed/out-of-range bounds rejected |
| E4 | Span resolves exact original bytes | P: arbitrary valid slice equals resolver output | M: same text at different offsets retains different refs |
| E5 | Verbatim turn reconstructs exactly | U/P: concat ordered spans equals turn bytes | A: reordered/missing span fails verbatim validation |
| E6 | Reconstructed cannot silently satisfy verbatim | U | A: reconstructed artifact/span referenced by verbatim-only object rejected |
| E7 | Identity independent of DB/time/randomness | U/M | A: volatile metadata variation cannot change semantic digest where excluded |

## Coverage/provenance invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| C1 | Exactly one primary disposition per source turn/extraction revision | U/P | A: missing and duplicate disposition rejected |
| C2 | Completed extraction covers all source turns | U/P | A: reported `100%` with omitted turn fails recomputed coverage |
| C3 | Accepted derived state/edge has resolvable provenance | U | A: missing/broken evidence ref rejected |
| C4 | Unsupported edge remains unresolved | U/R | A: unresolved edge marked accepted/compiled fails |
| C5 | Supersession preserves history | U | A: destructive replacement/missing predecessor ref rejected |

## Canonicalization/determinism invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| D1 | Same object serializes byte-identically | U/P | MU: perturb sorting/separators and require tests kill mutation |
| D2 | Object-key construction order irrelevant | P/M | — |
| D3 | Semantic ordered-array order matters | U/M | A: trajectory node reorder changes digest/validation |
| D4 | Explicit set-like order does not matter | P/M | — |
| D5 | Unknown schema version fails closed | U/P | A: future/typo version rejected |
| D6 | Released schema semantics immutable | fixture/golden schema digest check | A: silent schema replacement detected by review/CI manifest |

## Pedagogical-state invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| S1 | Representation state is structured and referenceable | U | A: required representation encoded only as unstructured prose cannot satisfy transition validator |
| S2 | Preserve/forbid constraints are explicit | U | A/B: drop required array/index/box → reject |
| S3 | Forbidden future information is explicit | U | A/B: disclose max comparison before authorized → reject |
| S4 | Answer-reveal policy is explicit | U | A/B: leaked target answer rejected |
| S5 | Realization mode is frozen/parameterized/generative | U | A: mutate immutable frozen wording/question semantics → reject |
| S6 | Parameter mutation permissions explicit | U/P | A: mutate immutable relation/notation while changing example values → reject |
| S7 | Required learner-visible context is actually rendered | V | A/V: internal preserve flag exists but full problem/chart disappears from learner output → reject |
| S8 | Forbidden visual components are enforceable | U/B | A/B: expose enumerate pair row/window box before authorized → reject |

## Learner-evidence and grading invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| L1 | Learner outcome is bounded enum | U/P | A: arbitrary outcome label rejected |
| L2 | Outcome requires learner evidence | U | A: tutor-only evidence cannot establish `correct` |
| L3 | Partial/incorrect cannot silently advance | U/A | MU: invert branch/acceptance test and require killed mutation |
| L4 | Meta/hint request does not imply mastery | U | A: advancement without explicit rule rejected |
| L5 | Grading oracle is controller-only | U/V | A: serialized renderer-safe turn contains expected answer or forbidden-answer literals → reject |
| L6 | `partial` preserves established sub-result and targets only missing step when source-backed | U/R/V | A: treat known partial as fully wrong or advance as fully correct → reject |

## Path/trajectory invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| T1 | Source-backed required intermediate node is non-removable | U/R/B | A: delete each required node independently |
| T2 | Shortcut edge cannot bypass required path | U/R/B | A: `A -> B -> C` mutated to `A -> C` rejected |
| T3 | Correction/retry/verify sequence is first-class | U/R | A: collapse correction directly to advance rejected when branch requires retry/verify |
| T4 | Alternate paths require explicit acceptance | U | A: mathematically plausible unregistered alternate edge rejected |
| T5 | Path order deterministic | U/P | M: reorder required path changes semantics/digest |
| T6 | Unsupported repeated-error/control paths fail closed | U/V | A: invent a second retry policy not established by source/compiled policy → reject |
| T7 | Historical meta evidence may compile into policy without requiring verbatim reenactment | U/R | A: future learner forced to reproduce historical phrase merely because calibration contained it → reject |

## September-4 historical regression obligations

These run only in an authorized private/local lane; raw transcript is not committed here.

| ID | Historical requirement | Required result |
|---|---|---|
| R1 | ingest all raw parts | exact source byte digests retained |
| R2 | reconstruct all source turns | 100% exact verbatim reconstruction |
| R3 | extraction ledger | 100% source-turn coverage, zero duplicates |
| R4 | `enumerate(a)` | full explanation→exercise→validation sequence recovered from raw evidence |
| R5 | max progression | `S[0] -> S[i]` bridge and explicit-index-before-generalization recovered |
| R6 | representation validation | array/index/box preservation requirement recovered |
| R7 | else bridge | explicit `if i != 0 -> else` transition recovered |
| R8 | arbitrary k | fixed-k scalability failure→`range(k)`→`x`→same-`S[i]` nested state recovered |
| R9 | correction policies | failure→learner correction→successful repair paths represented |
| R10 | unsupported ambiguity | emitted unresolved, never invented |
| R11 | compile replay | same inputs/compiler revision → byte-identical canonical trajectory |
| R12 | learner-visible replay | required problem/chart context remains visible across authorized runtime transitions |

## Required semantic-compression and realization mutation corpus

The compiler/trajectory/runtime validators must reject at least:

1. delete `enumerate` explanation node;
2. delete enumerate exercise validation;
3. skip `S[0] -> S[i]`;
4. compare before learner writes `S[i]`;
5. jump explicit `S[1]/S[2]` examples directly to generalized `S[i]` when historical path marks them required;
6. replace same-chart validation with representation loss;
7. skip `if i != 0` and jump to `else`;
8. introduce arbitrary-k/range before fixed-window limitation is established;
9. replace `S[i]` with unauthorized `window_sum` terminology;
10. reveal target answer in a probe prompt;
11. reveal target answer through a learner-visible chart/annotation;
12. invent learner outcome;
13. invent exercise/experiment;
14. collapse correction→retry→verify;
15. promote unresolved edge to accepted;
16. preserve `problem_anchor` internally while dropping it from learner-visible output;
17. expose controller-only assessment values to the renderer;
18. invent an unsupported repeated-error branch.

A future lexical/register mutation corpus may add premature `number -> element` or `box -> window` substitutions only after the active falsification experiment demonstrates that language/register needs first-class control.

## Continuity/documentation/checkpoint invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| A1 | `HANDOFF_STATE.json` is PAM-valid `current` state | C: pinned PAM validator | A/C: invalid version/state/reason rejected |
| A2 | archived checkpoint JSON is PAM-valid `historical_checkpoint` state | C: pinned PAM validator over every checkpoint | A/C: malformed checkpoint fails assurance CI |
| A3 | generated README/status matches durable state inputs | C: `make docs-check` | A/C: edit generated block or change state without sync → CI fails |
| A4 | historical checkpoint is not treated as current authority | C/reconciliation review | A: stale checkpoint overrides live repo/CI observation → reject process result |
| A5 | semantic design docs are human-reviewed rather than inferred from status metadata | review | A: status generator silently rewrites PDD/SDD semantics → reject |

## CI gates by phase

### Gate G0 — documentation/schema

- required docs present;
- generated README/status synchronization passes;
- current PAM handoff and historical checkpoints validate in assurance CI;
- JSON Schemas validate their own metaschema;
- schema fixtures/parity tests pass;
- lint/type checks pass.

### Gate G1 — evidence kernel

- G0;
- byte artifact/span/turn unit tests;
- Hypothesis byte/span round-trip properties;
- adversarial Unicode/newline/duplicate-text fixtures;
- branch coverage on evidence kernel.

### Gate G2 — state/transition kernel

- G1;
- representation/pedagogy state validation;
- outcome/probe/transition constraints;
- semantic mutation corpus;
- `mutmut` critical surviving mutants reviewed/zero for designated validators.

### Gate G2.5 — experimental executable replay falsification

This gate is allowed before the complete historical G3 compilation only as a schema/runtime falsification instrument.

- deterministic controller follows only explicit trajectory routes;
- renderer-safe contract excludes grading oracle data;
- correct/incorrect/partial fixtures route as specified by the currently encoded source-backed slice;
- learner-visible representation/context tests pass;
- no claim of production tutoring, automatic decomposition, or mastery follows from this gate.

### Gate G3 — historical compilation

- G2;
- private September-4 R1–R12 pass where applicable;
- deterministic compiled artifact digest recorded;
- independent benchmarker consumes exact PIR revision and rejects required public mutations;
- complete source-inspected canonical golden is frozen or explicitly retains unresolved edges.

Production Study OS controller integration is not authorized by PIR before G3. The experimental replay/controller harness is permitted before G3 only to falsify PIR semantics and validate intended learner-visible behavior.

## Proof discipline

Passing tests prove only the specified invariants. They do not prove educational efficacy, automatic problem decomposition quality, or generalization. Prospective human/donor benchmarking remains a separate evidence layer.
