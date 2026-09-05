# Study OS PIR — Current Status

> Generated from `docs/repository-state.json`, the PAM current handoff, and historical checkpoints. Run `make docs-sync` after changing those inputs. `make docs-check` fails on drift. Design specs remain human-reviewed.

## Current phase

PIR-0 executable golden replay and runtime/schema falsification

## Evidence snapshot

- September-4 turns accounted: **887**
- learner turns: **443**
- tutor turns: **444**
- candidate pedagogical events: **36**
- failure/repair regions: **18**
- retained unresolved questions: **4**

## Landed and tested capabilities

- byte-exact evidence and extraction accounting
- max-sum S[0] to S[i] vertical proof
- enumerate(a) vertical proof with visual answer-leak constraints
- branching foundations trajectory with correction/retry paths
- controller-only assessment registry separated from renderer-safe turn contracts
- deterministic local grading for current integer and integer-sequence probes
- generic local trajectory replay command
- persistent full-problem replay context artifact

## Current validation receipts

- September-4 evidence/accounting
- Max-sum and enumerate vertical proofs
- Branching trajectory and deterministic runtime
- Current PIR snapshot
- Current PAM handoff validation

## Current next action

Read assurance/NEXT_SESSION_HANDOFF.md, reconcile live main/CI, then wire persistent full-problem context into learner-visible renderer output. Extend the source-backed executable trajectory through i as box start, moved-box exercises, same-chart validation, and sum[i], including the observed PARTIAL path where correct box contents are given without the arithmetic sum. After replay is faithful through sum[i], run a small lexical/register falsification experiment before deciding whether first-class language state is needed.

## Current blockers

- Persistent problem context exists as an artifact but has not yet been proven in actual learner-visible rendering.
- Lexical/register hierarchy is a serious hypothesis, not yet a justified schema addition.
- Complete canonical September-4 golden remains unfinished.

## Not yet proven

- persistent full-problem context is visibly rendered on every required learner turn
- executable i-moves-box and sum[i] section with PARTIAL routing
- complete canonical September-4 golden
- automatic raw problem plus learner state to PIR decomposition
- lexical/register state as a required PIR primitive
- Luna masked, sealed, or prospective generalization results
- production tutoring or learning efficacy

## Historical PAM checkpoints

- `assurance/checkpoints/2026-09-05-executable-replay-frontier.json`

Historical checkpoints are immutable observations. Live repository and CI state wins when a checkpoint becomes stale.
