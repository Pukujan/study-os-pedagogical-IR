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

## Learner-evidence invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| L1 | Learner outcome is bounded enum | U/P | A: arbitrary outcome label rejected |
| L2 | Outcome requires learner evidence | U | A: tutor-only evidence cannot establish `correct` |
| L3 | Partial/incorrect cannot silently advance | U/A | MU: invert branch/acceptance test and require killed mutation |
| L4 | Meta/hint request does not imply mastery | U | A: advancement without explicit rule rejected |

## Path/trajectory invariants

| ID | Invariant | Positive verification | Negative/adversarial verification |
|---|---|---|---|
| T1 | Source-backed required intermediate node is non-removable | U/R/B | A: delete each required node independently |
| T2 | Shortcut edge cannot bypass required path | U/R/B | A: `A -> B -> C` mutated to `A -> C` rejected |
| T3 | Correction/retry/verify sequence is first-class | U/R | A: collapse correction directly to advance rejected when branch requires retry/verify |
| T4 | Alternate paths require explicit acceptance | U | A: mathematically plausible unregistered alternate edge rejected |
| T5 | Path order deterministic | U/P | M: reorder required path changes semantics/digest |

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

## Required semantic-compression mutation corpus

The compiler/trajectory validator must reject at least:

1. delete `enumerate` explanation node;
2. delete enumerate exercise validation;
3. skip `S[0] -> S[i]`;
4. compare before learner writes `S[i]`;
5. jump explicit `S[1]/S[2]` examples directly to generalized `S[i]` when historical path marks them required;
6. replace same-chart validation with representation loss;
7. skip `if i != 0` and jump to `else`;
8. introduce arbitrary-k/range before fixed-window limitation is established;
9. replace `S[i]` with unauthorized `window_sum` terminology;
10. reveal target answer in a probe;
11. invent learner outcome;
12. invent exercise/experiment;
13. collapse correction→retry→verify;
14. promote unresolved edge to accepted.

## CI gates by phase

### Gate G0 — documentation/schema

- docs present;
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

### Gate G3 — historical compilation

- G2;
- private September-4 R1–R11 pass;
- deterministic compiled artifact digest recorded;
- independent benchmarker consumes exact PIR revision and rejects required public mutations.

No production controller work is authorized by PIR until G3.

## Proof discipline

Passing tests prove only the specified invariants. They do not prove educational efficacy or generalization. Prospective human/donor benchmarking remains a separate evidence layer.
