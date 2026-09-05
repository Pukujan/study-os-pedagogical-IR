# Intended behavior — experimental `max_sum` vertical slice

This file is for human inspection. It is deliberately narrower than a generic pedagogy ontology and does **not** claim that the full September-4 trajectory has been compiled.

Source anchor: `Pukujan/Study-os@bef88216d9052eeb7e135916ea7fb6f8d84e0ccc:sessions/2026-09-04/sliding-window-pedagogy-calibration/raw/chat-visible-transcript-part08.md`.

## Calibrated accepted path

```text
first box visible; no comparison yet
        ↓
max_sum starts from S[0]
        ↓
changed chart: learner gives concrete max_sum value
        ↓
VALIDATE WHY THE VALUE WAS RIGHT IN THE SAME CHART
        ↓
changed chart: learner writes max_sum from S[0]
        ↓
VALIDATE THE S[0] ASSIGNMENT IN THE SAME CHART
        ↓
bridge only: while i = 0, S[0] and S[i] name the same current entry
        ↓
changed chart: learner writes the max_sum assignment using S[i]
        ↓
VALIDATE THE LEARNER-PRODUCED S[i] ASSIGNMENT IN THE SAME CHART
        ↓
only now move to i = 1 and ask the first comparison
```

At every pre-comparison step, the visible representation keeps the aligned `index(i)` row, `numbers(a)` row, active window box, current `i`, and current sum annotation. The bridge is not allowed to reveal the target assignment line.

## Observed tutor moves that this slice must reject

- Moving from the learner's value answer directly into `S[0] = S[i]` and comparison.
- Asking the next code exercise before showing why the prior answer was correct.
- Repeating another `S[0]` exercise after the learner had already produced and validated it, instead of bridging to `S[i]`.
- Showing `max_sum = S[i]` before asking the learner to produce it.
- Removing any required chart layer while claiming the same pedagogical step.
- Deleting `S[0] -> S[i]` merely because both denote the same entry when `i = 0`.

## What a passing test is allowed to prove

A passing vertical-slice test proves only that the current experimental IR can represent this calibrated micro-trajectory, render it legibly, and mechanically reject the listed structural shortcuts.

It does **not** prove that PIR is complete, that the full September-4 golden has been extracted, that a model can generate this trajectory from a novel problem, or that Study OS improves learning outcomes.
