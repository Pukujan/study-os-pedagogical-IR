# PIR-1 Compiler Feasibility and Generalization Gate

Status: experimental next-phase gate

## Why this gate exists

The September-4 sliding-window calibration is now a rich source-backed public regression corpus. It has been used to discover and exercise pedagogical contracts including prerequisite bridges, representation persistence, deterministic progression, PARTIAL outcomes, correction/retry/verification, language constraints, answer authorization, and the distinction between solution exposure and mastery evidence.

That work does **not** by itself prove that the PIR generalizes to unseen problems. Continuing to add sliding-window-specific states would increase historical fidelity while also increasing the risk of test overfitting.

The next success criterion is therefore not more sliding-window replay. It is demonstrating that a versioned compiler policy can propose useful PIR structure for structurally different problems without receiving their expected pedagogical graph.

## Immediate product question

> Given a raw problem plus an evidence-bounded learner state, can an LLM compiler produce a candidate pedagogical decomposition that survives deterministic PIR validation and independent evaluation across multiple problem families?

The LLM is a **proposal/compiler component**, not the runtime authority.

```text
raw problem + learner evidence
        ↓
versioned LLM compiler policy
        ↓
candidate PIR proposal
        ↓
schema + semantic + pedagogy + representation + language validators
        ↓
accepted candidate
        ↓
deterministic controller/runtime/renderer/verifier
```

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

### 1. Minimal compiler contract

Add strict, versioned models for compiler input and compiler proposal.

Compiler input must include only legitimate candidate-visible information, such as:

- raw problem text / structured problem data;
- learner evidence snapshot with `UNKNOWN` permitted by default;
- known/current representation when applicable;
- public PIR/compiler constraints;
- compiler policy identity/version.

Compiler proposal should describe structure, not a finished lesson. Initial proposal fields should be limited to reusable concepts such as:

- problem objects and roles;
- prerequisite concepts;
- candidate state variables;
- dependencies;
- candidate microsteps/transitions;
- invariants/conditions;
- representation requirements;
- assessment targets;
- candidate misconception/failure classes;
- abstraction/generalization path.

Do not encode evaluator-only expected bridges or answers in the candidate input.

### 2. Prompt-policy versioning

Prompt/model configuration is part of the compiler identity and must be versioned independently from PIR.

Initial experimental policies:

- `compiler-p0@0.1.0`: weak natural-language decomposition baseline;
- `compiler-p1@0.1.0`: product-thesis / detailed pedagogical framing;
- `compiler-p2@0.1.0`: explicit decomposition constraints;
- `compiler-p3@0.1.0`: one-transition structured proposal;
- `compiler-p4@0.1.0`: PIR-only structured compiler output.

Every run receipt must pin prompt policy, model identity/revision, PIR revision, benchmarker revision, settings, and candidate-visible input hashes.

### 3. Diverse development DSA problems

Use structurally different visible-development problems rather than many array variants.

Initial development set:

1. **Binary search** — interval state, midpoint role, comparison semantics, invariant-driven elimination.
2. **Two pointers** — two simultaneous positional roles, coordinated transitions, crossing/boundary conditions.
3. **BFS shortest path / graph frontier** — queue/frontier state, visited invariant, non-linear representation.

These are development cases: failures may be inspected and may guide compiler/PIR improvements. They cannot later count as sealed generalization evidence.

A reusable PIR should express these primarily through generic constructs such as object, role, state, transition, invariant, dependency, condition, iteration, representation, prerequisite, misconception, assessment, and evidence. If each problem requires bespoke problem-family-specific control fields, treat that as evidence the abstraction is overfit.

### 4. Repeated-run compiler evaluation

Do not judge a prompt/model from one impressive completion.

For each candidate configuration, run multiple fresh independent generations per development problem and report distributions for at least:

- schema-valid proposal rate;
- legal/accepted proposal rate;
- prerequisite coverage;
- required bridge preservation;
- representation persistence;
- answer/future-information leakage;
- unsupported learner-knowledge assumptions;
- unsupported mastery claims;
- concept/variable complexity per step;
- semantic convergence across runs;
- surface terminology variance.

Retain failed runs. Do not cherry-pick the best sample.

### 5. Smaller-model calibration

Evaluate model size and task granularity separately.

Compare at least:

- stronger model, full/coarse PIR proposal;
- smaller model, full/coarse PIR proposal;
- smaller model, one-next-transition proposal.

The goal is to discover the smallest approved model for each bounded compiler operation, not to require one model to do the whole teaching job.

A smaller model may be acceptable for local transition proposals even if it is inadequate for unfamiliar-problem semantic decomposition.

### 6. Anti-overfitting lanes

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
2. A strict compiler input/proposal contract exists and contains no evaluator oracle.
3. Prompt policies are versioned and reproducible.
4. At least three structurally different visible DSA development problems can be compiled into valid candidate PIR proposals.
5. Repeated-run reports are produced; no result is based on one selected completion.
6. At least one configuration demonstrates stable semantic decomposition across all development families while deterministic validators continue to catch illegal shortcuts, representation loss, answer leakage, and unsupported learner/mastery claims.
7. Smaller-model performance is measured separately for coarse decomposition and local-transition generation.
8. Systematic Lane B masked September-4 evaluation exists and is reported honestly as masked regression, not unseen generalization.
9. A clean Lane C or Lane D evaluation boundary is prepared before any claim that the compiler works on unseen problems.
10. At least one clean sealed/prospective evaluation is run before promoting the architecture as generalizing beyond development cases.

There is deliberately no population-level learning-efficacy claim in this gate. This phase tests compiler structure, authority boundaries, and generalization behavior—not whether the system improves student outcomes at scale.

## Hard failure signals

Stop and revise the abstraction if experiments show any of these patterns:

- every new DSA family requires bespoke top-level PIR primitives;
- prompt success depends on embedding expected golden bridges in the prompt;
- good results occur only in selected runs while variance remains high;
- candidate proposals routinely assume learner knowledge not supported by evidence;
- semantic correctness is achieved by dropping required representation/pedagogical bridges;
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
2. implement compiler input/proposal models
3. implement prompt-policy identity/version registry
4. define binary-search, two-pointers, BFS development inputs
5. add candidate-run receipt/report format
6. run strong-model and smaller-model prompt-policy matrix
7. add systematic September-4 masked regressions
8. select best policy by repeated-run metrics, not anecdotes
9. prepare isolated sealed/prospective evaluation
10. run clean unseen evaluation
```

The next code change after this document should therefore be the minimal compiler contract and prompt-policy versioning surface, not another historical tutoring trajectory or production application feature.
