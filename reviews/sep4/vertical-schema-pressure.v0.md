# Full-source schema pressure on experimental vertical IR

Status: **blocking evidence against unchanged promotion**

Source: September-4 source review at `Pukujan/Study-os@bef88216d9052eeb7e135916ea7fb6f8d84e0ccc`.

## Falsified assumption

The max-sum experimental type currently makes `VerticalRepresentation.box` mandatory.

That assumption fits the calibrated max-sum slice because those turns intentionally preserve the array/index/window-box representation.

It does **not** fit the calibrated `enumerate(a)` representation at source sequences 589–597. That representation consists of:

- `numbers(a)` row;
- `index(i)` row;
- `number(num)` row;
- the `(index, number)` pair relation;
- optional highlighting of the current index/value/pair during validation.

There is no sliding-window box in that concept. Adding a fake box would mutate the pedagogy to satisfy the schema.

Therefore:

> mandatory window-box structure is a slice-specific representation feature, not a general PIR representation invariant.

## Smallest authorized change

For the second vertical slice only, permit a representation with no window box. Do not introduce a generic education ontology or replace the structured chart with opaque prose.

The next slice must prove that the same experimental representation machinery can express:

```text
explain enumerate in chart
↓
non-answer-revealing probe
↓
learner answer
↓
same-chart validation/highlight
↓
changed-array probe
↓
learner answer
↓
same-chart validation/highlight
↓
advance to append after learner says two probes are enough
```

## Mutations that must fail

- show `(3,6)` before asking for it;
- ask a probe before explaining `enumerate` sufficiently;
- validate with detached prose while dropping the chart;
- move to the next exercise before same-chart validation;
- introduce an unnecessary third enumerate exercise after the learner explicitly says two are enough;
- inject sliding-window concepts or a window box into the enumerate representation.

## Claim boundary

Passing this second slice would show that the experimental chart representation survived one non-window concept and preserved the calibrated exercise/validation sequence. It would still not justify freezing the full G2 schema or claim general pedagogy coverage.
