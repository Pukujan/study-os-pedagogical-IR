# Study OS v2 — Next Session Handoff

Status date: 2026-09-05
Owning repo: `Pukujan/study-os-pedagogical-IR`
Active issue: #1
Live PIR head at handoff preparation: `d6514a8d34d2a0d6a48e004d5286f29b8ce44ed5`
Live benchmarker head: `a5751661e19f9d00a2c192dd98780c064a285642`
Pinned Study OS evidence source: `Pukujan/Study-os@bef88216d9052eeb7e135916ea7fb6f8d84e0ccc`
Pinned PAM methodology: `Pukujan/project-assurance-modules@03fc55ae4036a9704cdb929fb3ae6dc520ae2183`

## 1. What Study OS v2 is trying to build

Study OS v2 is a compiler/runtime for human problem-solving knowledge.

The intended architecture is not "ask an LLM to teach a problem." It is:

```text
expert/problem-solving knowledge
        ↓
pedagogy compiler
        ↓
explicit pedagogical IR
        ↓
deterministic validation/controller
        ↓
bounded renderer / language model
        ↓
learner
```

A problem should be decomposed into explicit objects, states, operations, transitions, conditions, dependencies, invariants, representations, probes, learner outcomes, repair paths, and forbidden future information. The LLM may propose decompositions or render an authorized turn, but it must not own path progression.

Core pedagogical target:

```text
human intuition
→ visual state
→ explicit reasoning
→ algebra
→ code
```

The underlying meaning should remain stable while representation and language become progressively more compressed/formal.

The motivating calibrated example is sliding window. The beginner path is intentionally much more granular than the expert abstraction:

```text
problem
→ numbers(a)
→ position(p)
→ index(i)
→ k
→ visible box
→ i as box start
→ S[i]
→ S[i+1]
→ recurrence
→ repeated recurrence as i changes
→ enumerate(a)
→ append
→ Python loop
→ validation against original array/index/box
→ max_sum initialization
→ S[0] → S[i]
→ comparison
→ max loop
→ combine loops
→ if i == 0 / if i != 0
→ else
→ boundary / break
→ arbitrary k
→ range(k)
→ x
→ nested accumulation into the same S[i]
→ final combined loop
```

Do not compress an evidenced bridge merely because its endpoints are semantically equivalent. The central invariant remains:

> semantic equivalence does not imply pedagogical equivalence.

## 2. Repository boundaries

### `Pukujan/Study-os`

Real adopter/runtime and source of authorized learner evidence. Raw/private transcripts do not belong in public PIR or benchmarker repositories.

### `Pukujan/study-os-pedagogical-IR`

Canonical candidate home for byte-backed evidence contracts, experimental pedagogical representation, transition semantics, runtime/controller contracts, and eventually the stable PIR/compiler boundary.

### `Pukujan/study-os-benchmarker`

Independent evaluator. Candidate context and benchmark oracle are separated. The evaluator must independently catch shortcutting, answer leakage, representation loss, forbidden future information, unnecessary repetition, etc.

### PAM

PAM is assurance only. It is not pedagogy and is not a runtime dependency. We currently use the structured-handoff and benchmark-integrity modules as a fail-closed continuity / evaluation-integrity shell.

## 3. What is proven and green

### Evidence kernel / extraction accounting

The source evidence layer is raw-byte authoritative. Source bytes are hashed before any normalization. Derived IR is canonicalized separately.

The full September-4 source at pinned Study OS commit `bef88216...` was parsed into:

- 887 turns
- 443 learner turns
- 444 tutor turns
- 887 exact source spans
- 887 disposition records
- 0 missing turns
- 0 duplicate dispositions
- 0 unknown turns

This proves source accounting only. It does **not** prove all 887 turns are semantically understood.

A source-review ledger separately resolves:

- 36 candidate pedagogical events
- 18 explicit failure → repair regions
- 4 retained unresolved questions

Every candidate range resolves to real source turns. This is still a candidate semantic review, not the final complete canonical golden.

### Experimental max-sum vertical slice

A real calibrated sequence is represented and tested:

```text
concrete S[0] value
→ same-chart validation
→ learner produces max_sum = S[0]
→ same-chart validation
→ bridge: because i = 0, S[0] and S[i] denote the same current entry
→ changed example
→ learner produces max_sum = S[i] without seeing the answer
→ same-chart validation
→ only then comparison
```

Known bad moves are first-class evidence: premature comparison, skipped validation, redundant S[0] exercise, answer leakage, chart loss.

PIR proof previously passed Ruff, strict mypy, 57 tests, and 100% statement + branch coverage.

Independent benchmarker cases reject the same shortcut mutations.

### Experimental enumerate(a) slice

The full transcript falsified an earlier representation assumption: not every pedagogical representation has a window box.

`enumerate(a)` uses an aligned index / number / pair representation, so the experimental representation model was changed to allow non-window charts.

The source also forced two additional capabilities:

1. learner outcomes can control progression (e.g. after two successful changed examples, "two is enough" authorizes moving to append rather than forcing a third exercise);
2. answer-leak validation must inspect the entire learner-visible surface, including chart rows/annotations, not only the question text.

The enumerate PIR slice is green, and the independent benchmarker at `a5751661e19f9d00a2c192dd98780c064a285642` is green. Its cases reject:

- showing the exact `(3,6)` answer before the probe;
- exposing `pair_row` during a no-answer-reveal probe;
- injecting irrelevant `window_box` state;
- advancing to append too early;
- saying "correct" without same-chart validation;
- leaking the changed-example answer;
- forcing an unnecessary third exercise after calibrated stopping evidence.

Benchmarker CI run `33980151679` succeeded for that exact head.

### Branching foundations trajectory

The beginning of the lesson exposed another important schema pressure: the lesson is not a single line. Wrong answers create explicit repair branches.

An experimental acyclic trajectory graph now represents a source-backed finite path such as:

```text
problem anchor
→ position explanation
→ position probe
       ├─ correct
       │    → same-chart validation
       │    → changed verification
       └─ incorrect
            → same-chart correction
            → changed retry
            → validation
→ index introduction
→ index verification
→ k introduction
→ k/box exercises
```

Repeated-error behavior is deliberately not invented where the source does not establish a policy. An unmodeled repeated error fails rather than silently generating another retry strategy.

The trajectory validator catches duplicate IDs, unknown references, forbidden concepts/representation, answer leakage, invalid/ambiguous control, duplicate outcome routes, unreachable states, and cycles.

At commit `f2883c065fb8f3d60271764e733efa4e79b12634`, CI passed:

- Ruff
- strict mypy
- 110 tests
- 100% statement coverage
- 100% branch coverage

### Deterministic interactive runtime

The first actual runtime exists in `src/study_os_pir/runtime.py`.

A critical boundary emerged: canonical answers/grading oracles must not be bundled into the renderer-visible trajectory.

Current split:

```text
pedagogy graph
   ├─ renderer-safe turn contract
   └─ controller-only assessment registry
               ↓
         deterministic grader
               ↓
         normalized outcome
               ↓
       deterministic next node
```

The renderer-safe turn contract strips expected answers and forbidden-answer literals. Tests explicitly serialize the renderer contract and verify that grading-oracle fields are absent.

The runtime currently supports simple deterministic input assessment for integer and integer-sequence probes. Inputs such as these can be graded locally without an LLM:

```text
4
4 7 2
4,7,2,6,1
[4, 7, 2]
```

A tested wrong-answer session routes to correction and then rejoins the calibrated progression.

At commit `2cf7da6eaa197653b052c4589f5ec5bcec6467b7`, CI passed:

- Ruff
- strict mypy
- 147 tests
- 100% statement coverage
- 100% branch coverage

### Local replay command

A generic console replay command has been added:

```bash
python tools/replay_trajectory.py \
  --trajectory fixtures/public/sliding-window-foundations/trajectory.v0.json \
  --assessments fixtures/public/sliding-window-foundations/assessments.v0.json
```

This is not yet a full sliding-window tutor. It is a deterministic local replay of the currently encoded lesson beginning.

## 4. Current exact live state

PIR `main` currently points at:

`d6514a8d34d2a0d6a48e004d5286f29b8ce44ed5`

Commit message:

`add persistent full-problem replay context`

CI run `33982848595` completed successfully for that exact head.

This latest commit adds an explicit persistent replay-context artifact for the full difficult problem because live output exposed a mismatch: `preserve_components: problem_anchor` was structurally present in the graph, but the console renderer could still stop visibly printing the full problem on subsequent turns.

This is a real intended-use failure, not merely bookkeeping. The next session must wire persistent context into the learner-visible runtime and test actual output.

## 5. Immediate next build frontier

Do **not** jump to automatic raw-problem decomposition yet.

The next proof-producing sequence should be:

```text
1. Reconcile live repo/CI state.

2. Wire persistent full-problem context into RendererTurnContract / console rendering.
   Requirement: the original difficult question remains visibly available throughout the calibrated micro-lesson where required.
   Test actual learner-visible output, not only a hidden `preserve_components` flag.

3. Extend the executable source-backed trajectory through:

   k stable
   ↓
   i = where the box starts
   ↓
   i = 0 explanation
   ↓
   i = 1 guided box exercise
   ↓
   changed i/k exercise without answer arrows
   ↓
   same-chart validation
   ↓
   introduce sum[i] with the box still visible

4. Add `PARTIAL` routing for sum[i].
   Source-backed example:
   learner gives the correct box contents `2 6` but does not add them.
   This is not simply wrong.
   Route to the smaller arithmetic probe `2 + 6 = ?`, then rejoin sum[i] validation.

5. Make the local terminal replay usable through `sum[i]`.
   Deliberately test correct, wrong, and partial learner answers.

6. Only after this runtime experience is visibly faithful, continue into consecutive sums / recurrence.
```

## 6. New linguistic / semantic-density insight from the latest discussion

A new hypothesis needs to be carried into the next session but **must not yet be promoted into canonical PIR**.

Study OS already controls concept disclosure and representation state, but the intended pedagogy also requires controlled movement in language/register.

Examples:

```text
number
→ number at an index
→ element
→ a[i]
```

```text
box
→ selected group
→ window
```

```text
box total
→ window sum
→ S[i]
```

The relevant established educational ideas include concreteness fading / Concrete-Representational-Abstract progression, progressive formalization, and semantic waves / semantic density. The useful engineering hypothesis is not "implement those theories." It is:

> representation abstraction and language/register abstraction may be separate state dimensions.

A model can currently preserve a visual chart while still prematurely switching beginner language from "number" to "element" or "box" to "window." That change may be semantically valid while pedagogically premature.

Possible future primitive, **only if source/runtime pressure proves it necessary**:

```text
lexical/register state
- concept semantic identity
- currently preferred learner-facing term
- allowed synonyms
- not-yet-introduced disciplinary terms
- explicit lexical bridge from grounded → technical terminology
```

Potential rule:

> A new technical term is a pedagogical delta unless it has already been introduced/bridged; it is not merely renderer style.

Potential controlled repair:

```text
formal / dense language
↓ learner confused
semantic downshift
↓
grounded language + visual representation
↓
rejoin formal representation
```

However, before modifying the schema, the next session should perform a **small source-backed lexical falsification test**. Ask:

- Does the current trajectory/runtime allow a renderer to switch `number` → `element` or `box` → `window` prematurely while still passing all current contracts?
- Is there an actual calibrated source instance where terminology stability mattered?
- Can the behavior be constrained with existing `disclosed_concepts` / `forbidden_concepts`, or is first-class lexical/register state genuinely required?

If existing fields can enforce the needed behavior cleanly, do not add a new language ontology. If they cannot, add the smallest experimental lexical bridge/state needed and attack it with mutations.

## 7. Important design decisions not to reverse

1. Raw source bytes are authority. Derived summaries/goldens do not replace evidence.
2. Source accounting and pedagogical understanding are different claims.
3. PIR describes/controls pedagogy; benchmarker independently evaluates it; Study OS adopts pinned tested revisions.
4. Deterministic controller owns authorized progression. LLMs propose/render/interpret but do not silently choose the next pedagogical node.
5. Renderer-visible context must not contain hidden grading answers.
6. Historical learner meta-turns are calibration evidence, not necessarily literal future runtime gates. A future learner should not have to reproduce a historic phrase such as "two is enough" word-for-word unless the compiled policy explicitly requires a comparable state/outcome.
7. Representation state is structured. Do not reduce "same chart" to prose.
8. Semantic equivalence never authorizes deletion of an evidenced intermediate pedagogical state.
9. Experimental `vertical.py`, `trajectory.py`, and runtime v0 types are still falsification instruments. Do not freeze them as canonical G2 simply because current slices pass.
10. Do not make a universal pedagogy ontology from one learner/session.
11. Do not call masked September-4 cases true hidden generalization tests. True sealed/prospective holdouts remain separate.
12. Once a hidden oracle is opened for debugging, that case is contaminated and must become regression.
13. PAM is an assurance shell, not pedagogy logic.
14. A green schema/coverage receipt is not proof of learning efficacy or automatic compiler quality.
15. Actual learner-visible replay output is now a first-class falsification surface. Structural preservation that is not visibly rendered is insufficient.
16. The language/register insight is a serious hypothesis, not yet permission to expand the schema.

## 8. Unresolved source / research questions

Keep these unresolved unless evidence or explicit experiments answer them:

- Should the earlier `max(S)` detour be executable golden or superseded exploration?
- Should transcript-faithful `len` ordering remain as the historical trajectory while a later improved prerequisite order is tested separately?
- How should early part-01 attempts be dispositioned relative to the later calibrated trajectory?
- Final combined-loop exposure is not independent mastery; what later evidence should establish mastery?
- What is the correct bounded repeated-error policy when a learner fails the changed retry again? Do not infer unlimited retries from one observed branch.
- Is lexical/register state genuinely required as first-class IR, or can current concept/representation contracts express terminology stability without distortion?
- Should `partial` outcome grading stay deterministic for known structured answers and use a bounded classifier only for open natural-language responses?

## 9. What has not been built yet

Do not confuse the current replay runtime with the final product.

Still not built/proven:

- complete source-inspected canonical September-4 golden;
- executable trajectory covering the entire sliding-window lesson;
- recurrence section in the branching runtime;
- enumerate/append integration into one continuous executable trajectory;
- full max-sum / branch / arbitrary-k integration into one continuous runtime;
- automatic raw problem → PIR pedagogy compiler;
- recursive edge-refinement compiler for deciding whether a proposed A → B transition is pedagogically atomic;
- compiler benchmark track for raw problem + learner state → candidate PIR;
- local model renderer benchmark over the executable trajectory;
- Luna fresh-subagent masked-regression tournament;
- sealed hidden holdout evaluation;
- prospective unseen learner/session evaluation;
- fine-tuning;
- production Study OS persistence/runtime integration;
- learning efficacy claims.

## 10. Intended evaluation strategy after golden replay is sufficiently complete

Two distinct benchmark tracks are required:

### Compiler benchmark

```text
raw problem + learner state
→ candidate pedagogical IR
```

Measure required-node recall, bridge recall, dependency order, semantic-delta size, representation continuity, exercise/validation placement, correction paths, answer leakage, future-information leakage, unnecessary concepts, missing concepts, cycles, and over/under-decomposition.

### Runtime benchmark

```text
approved PIR + current state
→ candidate tutor turn
```

Measure next-edge fidelity, representation preservation, language/terminology constraints if justified, answer leakage, forbidden future information, correction-path fidelity, and unnecessary repetition.

Luna is intended to act as an independent local execution lab: fresh subagents receive only manifest-approved candidate inputs, never the hidden oracle, full calibration transcript, previous scores, or expected bridge names.

## 11. Fresh-session startup checklist

A new agent/session should begin by doing exactly this:

```text
1. Read this file.
2. Read assurance/HANDOFF_STATE.json.
3. Re-fetch PIR main and latest CI; live state wins.
4. Re-fetch benchmarker main and CI.
5. Re-fetch Study OS issue #65 / source golden if needed.
6. Do not assume the handoff head is still current if commits changed.
7. Run/inspect the local replay before adding more architecture.
8. Finish persistent full-problem rendering.
9. Extend through i-moves-box and sum[i] with partial-response routing.
10. Then run the lexical/register falsification experiment before deciding whether PIR needs a language-state primitive.
```

The project focus remains output-driven:

> Build only enough new machinery to produce the next decision-relevant runtime or benchmark result.

Do not optimize for more schemas, more receipts, or more theory unless a real learner-visible or benchmark failure requires them.
