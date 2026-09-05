# Enumerate calibration — second vertical intended behavior

Source authority: September-4 transcript sequences 585–598 at pinned Study OS commit `bef88216d9052eeb7e135916ea7fb6f8d84e0ccc`.

This fixture is experimental schema pressure. It is not a canonical G2 golden.

## Accepted trajectory

```text
show index/number chart
↓
explain enumerate(a): each loop turn gives current index + number
↓
learner asks for the calibrated question form
↓
ask: when the loop reaches a = 6, what pair does enumerate(a) give?
WITHOUT displaying (3,6) first
↓
learner: 3,6
↓
validate WHY in the SAME chart by highlighting index 3, number 6, pair (3,6)
↓
changed array
↓
ask pair for a = 7
↓
learner: 4,7
↓
validate WHY in the SAME changed chart
↓
learner says two exercises are enough
↓
advance to append
```

## Observed rejected behavior

1. The tutor displayed `(3,6)` before asking for it. Learner rejected the answer leak.
2. The tutor repaired the leak but asked before explaining `enumerate` enough. Learner rejected the under-explained probe.
3. After learner correctly answered `(3,6)`, the tutor said correct and immediately moved to another exercise without showing why in the chart. Learner explicitly restored the same-chart validation rule.
4. After two successful enumerate probes, learner explicitly said `no 2 is enough` and authorized moving to append.

## Representation contract

The enumerate chart is not a window representation. It contains structured aligned rows/relations:

```text
numbers(a):      [4,  7,  2,  6,  1,  9]

index(i):         0      1      2      3      4      5
number(num):      4      7      2      6      1      9
pair:            (0,4)  (1,7)  (2,2)  (3,6)  (4,1)  (5,9)
```

Validation may highlight the current index/value/pair. It must not invent a sliding-window box merely because the first experimental PIR representation required one.

## Must fail

- target pair is shown before the learner is asked;
- probe occurs before sufficient explanation;
- same-chart validation is deleted;
- next exercise occurs before validating the previous answer;
- third enumerate exercise is forced after the learner says two are enough;
- `k`, sliding recurrence, max comparison, or a window box is injected into this representation.

## Allowed conclusion if green

Only: the experimental representation/probe machinery can represent both the max-sum window-chart slice and this non-window enumerate chart while preserving their calibrated sequencing constraints.

Not allowed: universal PIR completeness, compiler discovery, or learning efficacy.
