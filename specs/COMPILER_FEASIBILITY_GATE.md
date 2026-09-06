# PIR-1 Compiler Feasibility and Generalization Gate

Status: experimental next-phase gate

## Why this gate exists

The September-4 sliding-window calibration is now a rich source-backed public regression corpus. It has been used to discover and exercise pedagogical contracts including prerequisite bridges, representation persistence, deterministic progression, PARTIAL outcomes, correction/retry/verification, language constraints, answer authorization, and the distinction between solution exposure and mastery evidence.

That work does **not** by itself prove that the PIR generalizes to unseen problems. Continuing to add sliding-window-specific states would increase historical fidelity while also increasing the risk of test overfitting.

The next success criterion is therefore not more sliding-window replay. It is demonstrating that a versioned compiler policy can produce a useful **canonical problem decomposition** for structurally different problems without receiving their expected pedagogical graph.

## Architectural decision: decomposition first, traversal later

The problem compiler does **not** receive learner state.

Its job is to answer:

> For this problem, what is the complete prerequisite-respecting sequence, representation grammar, assessment structure, and optional repair/expansion structure that a novice could require?

Personalization is a separate traversal problem. Learner evidence may later select an entry point, skip strongly evidenced concepts, request an expansion, or enter a repair path, but it must not cause the canonical decomposition itself to omit nodes.

```text
raw problem
        ↓
versioned LLM problem-compiler policy
        ↓
CanonicalProblemPIR
        ↓
schema + semantic + pedagogy + representation + language validators
        ↓
accepted canonical teaching graph

accepted canonical teaching graph + learner evidence + learner request/session state
        ↓
TraversalDecision
        ↓
deterministic controller/runtime/renderer/verifier
```

This separation lets us evaluate two questions independently:

1. **Decomposition accuracy:** did the compiler construct the right complete teaching graph?
2. **Adaptation accuracy:** given evidence, did traversal choose the right path through that graph?

## What is already proven enough to freeze as regression

For this phase, the September-4 sliding-window work is treated as visible/public regression evidence rather than as a source to keep optimizing against.

Existing regressions cover, among other things:

- position/index/value grounding;
- `k` and `i` role preservation;
- moved-box and same-chart validation;
- `sum[i]` with representation continuity;
- PARTIAL routing;
- successive sums and recurrence;
- enumerate and append bridges;
- first-window and later-window loop construction;
- boundary/`break` grounding;
- source-representation restoration after code;
- largest-sum and max tracking;
- arbitrary-`k` construction with `range(k)` / `x` / same-`S[i]` state;
- scoped lexical constraints;
- final solution exposure without unsupported mastery claims.

New sliding-window schema changes require evidence that a compiler/generalization experiment exposes a missing reusable abstraction. Do not extend the ontology merely to encode more historical surface detail.

## Missing pieces now

### 1. Canonical problem-compiler contract

The compiler input contains only legitimate problem-side information:

- raw problem text / structured problem data;
- domain;
- public PIR/compiler constraints;
- compiler policy identity/version.

It must **not** contain learner knowledge/evidence, a personalized current step, or evaluator-only expected bridges/answers.

The canonical proposal should describe structure, not a finished lesson. Initial proposal fields are limited to reusable concepts such as:

- problem objects and roles;
- all prerequisite concepts a novice could require;
- candidate state variables;
- dependencies;
- canonical microsteps/transitions;
- invariants/conditions;
- representation requirements;
- assessment targets;
- exercise requirements;
- optional expansion/repair hooks;
- candidate misconception/failure classes;
- abstraction/generalization path.

A canonical graph should be deliberately fine-grained enough that later traversal can safely compress it. Skipping is a traversal operation, not a compiler omission.

### 2. Separate traversal contract

Traversal receives:

- accepted `CanonicalProblemPIR`;
- learner evidence, with `UNKNOWN` permitted by default;
- learner request/session state when relevant.

Traversal may:

- follow the canonical path;
- skip a concept with sufficiently strong evidence;
- enter an authored repair path;
- enter an authored optional example/explanation branch.

The initial deterministic policy is conservative: `SUPPORTED_SUCCESS` is not enough to skip a canonical concept. Unaided, transferred, or retained evidence may authorize skipping. This policy is experimental and can later be calibrated independently from the problem compiler.

### 3. Prompt-policy versioning

Prompt/model configuration is part of the problem-compiler identity and must be versioned independently from PIR.

Initial experimental policies:

- `compiler-p0@0.1.0`: weak natural-language canonical decomposition baseline;
- `compiler-p1@0.1.0`: product-thesis / expertise-decompression framing;
- `compiler-p2@0.1.0`: explicit decomposition constraints;
- `compiler-p3@0.1.0`: one canonical microstep proposal at a time;
- `compiler-p4@0.1.0`: structured canonical PIR-only compiler output.

P3 is an incremental compiler ablation, not a learner-personalization mode. Repeated P3 calls would construct the same canonical graph one step at a time.

Every run receipt must pin prompt policy, model identity/revision, PIR revision, benchmarker revision, settings, and candidate-visible input hashes.

### 4. Diverse development DSA problems

Use structurally different visible-development problems rather than many array variants.

Initial development set:

1. **Binary search** — interval state, midpoint role, comparison semantics, invariant-driven elimination.
2. **Two pointers** — two simultaneous positional roles, coordinated transitions, crossing/boundary conditions.
3. **BFS shortest path / graph frontier** — queue/frontier state, visited invariant, non-linear representation.

These are development cases: failures may be inspected and may guide compiler/PIR improvements. They cannot later count as sealed generalization evidence.

A reusable PIR should express these primarily through generic constructs such as object, role, state, transition, invariant, dependency, condition, iteration, representation, prerequisite, misconception, assessment, exercise, repair, and evidence. If each problem requires bespoke problem-family-specific control fields, treat that as evidence the abstraction is overfit.

### 5. Repeated-run compiler evaluation

Do not judge a prompt/model from one impressive completion.

For each candidate configuration, run multiple fresh independent generations per development problem and report distributions for at least:

- schema-valid proposal rate;
- legal/accepted proposal rate;
- prerequisite coverage;
- canonical microstep coverage/order;
- required bridge preservation;
- representation continuity;
- exercise/assessment objective coverage;
- answer/future-information leakage;
- concept/variable complexity per step;
- semantic convergence across runs;
- surface terminology variance.

Retain failed runs. Do not cherry-pick the best sample.

Learner-state routing metrics belong to the separate traversal benchmark rather than the decomposition score.

### 6. Smaller-model calibration

Evaluate model size and decomposition granularity separately.

Compare at least:

- stronger model, full canonical PIR proposal;
- smaller model, full canonical PIR proposal;
- smaller model, one canonical microstep proposal at a time.

The goal is to discover the smallest approved model for each bounded compiler operation, not to require one model to do the whole teaching job.

Traversal should remain deterministic wherever evidence and authored graph structure are sufficient. LLM use in traversal is a later fallback question, not part of the PIR-1 compiler proof.

### 7. Anti-overfitting lanes

Use the benchmarker's existing holdout protocol.

- **Lane A — public regression:** September-4 and visible DSA development cases.
- **Lane B — masked regression:** mechanically hide known bridges/corrections/representations and test reconstruction. This is not true generalization evidence.
- **Lane C — sealed withheld calibration:** oracle created and kept outside development-agent/candidate visibility before prompt tuning.
- **Lane D — prospective unseen:** a new problem/session produced after compiler/prompt freeze; strongest evidence.

A sealed case becomes contaminated permanently if its oracle is opened for debugging or the prompt is tuned against it.

The development agent cannot manufacture a clean hidden claim by writing and then forgetting an oracle. A separate evaluator/human/isolated process must create or hold Lane C evidence.

## PIR-1 success gate

PIR-1 compiler feasibility is successful when all of the following are true:

1. September-4 remains green as public regression without new problem-specific hacks.
2. A strict learner-independent problem-compiler input and canonical-PIR proposal contract exists and contains no evaluator oracle.
3. A separate traversal contract exists; learner evidence cannot delete nodes from canonical compilation.
4. Prompt policies are versioned and reproducible.
5. At least three structurally different visible DSA development problems can be compiled into valid canonical PIR proposals.
6. Repeated-run reports are produced; no result is based on one selected completion.
7. At least one configuration demonstrates stable semantic decomposition across all development families while deterministic validators continue to catch illegal compression, representation loss, answer leakage, and structural invalidity.
8. Smaller-model performance is measured separately for full canonical decomposition and incremental canonical-microstep generation.
9. Traversal tests separately demonstrate that weak/unknown learner evidence cannot authorize skipping canonical concepts.
10. Systematic Lane B masked September-4 evaluation exists and is reported honestly as masked regression, not unseen generalization.
11. A clean Lane C or Lane D evaluation boundary is prepared before any claim that the compiler works on unseen problems.
12. At least one clean sealed/prospective evaluation is run before promoting the architecture as generalizing beyond development cases.

There is deliberately no population-level learning-efficacy claim in this gate. This phase tests compiler structure, authority boundaries, generalization behavior, and clean separation from adaptation—not whether the system improves student outcomes at scale.

## Hard failure signals

Stop and revise the abstraction if experiments show any of these patterns:

- every new DSA family requires bespoke top-level PIR primitives;
- prompt success depends on embedding expected golden bridges in the prompt;
- good results occur only in selected runs while variance remains high;
- canonical decomposition omits prerequisites because the model assumes an entry-level learner already knows them;
- semantic correctness is achieved by dropping required representation/pedagogical bridges;
- traversal skips weak/unknown concepts simply to shorten a lesson;
- smaller or stronger models can only succeed when given evaluator-side expected answers;
- sealed cases are repeatedly opened and tuned against, destroying the holdout boundary.

## Explicitly deferred from the critical path

The following ideas are valuable future product work, but they are **not required to pass PIR-1** and should not interrupt compiler/generalization experiments:

- production authentication and authorization routes;
- multi-user account system;
- persistent learner knowledge-profile database;
- curricula/domain enrollment;
- production model-routing/cost policies;
- known-problem compiled teaching library at scale;
- LLM-as-fallback production architecture;
- subscriptions/organizations;
- broad non-DSA domain expansion.

The intended future direction is a deterministic adaptive teaching engine with evidence-backed learner profiles, compiled known-problem/domain assets, and LLMs used as bounded compiler/semantic fallback components. Record that direction, but do not build it before PIR-1 establishes that the compiler abstraction generalizes.

## Immediate implementation order

```text
1. close/freeze September-4 public regression
2. split learner-independent canonical problem compilation from learner traversal
3. keep P0-P4 prompt policies learner-independent
4. define binary-search, two-pointers, BFS canonical development inputs
5. add candidate-run receipt/report format
6. build evaluator-side canonical requirements for the three development families
7. run strong-model and smaller-model prompt-policy matrix repeatedly
8. benchmark traversal separately against learner-evidence mutations
9. add systematic September-4 masked regressions
10. select best policy by repeated-run metrics, not anecdotes
11. prepare isolated sealed/prospective evaluation
12. run clean unseen evaluation
```

The next implementation after this split is the candidate runner/receipt plus independent canonical-decomposition evaluator, not another historical tutoring trajectory or production application feature.
