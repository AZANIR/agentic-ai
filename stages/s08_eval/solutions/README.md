# Solutions — stage 8

Look **after** your own attempt.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_2_the_denominator_climbs.py`](exercise_2_the_denominator_climbs.py) | 2 | What a denominator "from the evaluated" does under two different judge failure modes |

```bash
python -m stages.s08_eval.solutions.exercise_2_the_denominator_climbs
```

## Why there is only one solution

The rest of the exercises give an unambiguously red check with a readable message — the check's
output is the walkthrough.

Exercise 2 is different: the red check says "the denominator was taken from the evaluated", and
stops there. The interesting part begins after that line — because **there are two directions
here**, and they are opposites.

When the judge fails uniformly, the flattering share does not climb: it stands still while
coverage collapses from twenty-one cases to three. The number does not lie, it goes silent —
and it goes silent about exactly the thing that makes it meaningful.

When the failures are correlated with what breaks the judge — empty and truncated answers — the
cases that drop out are mostly the failing ones, and the share goes 57 % → 71 % → 85 % → 100 %
against an honest 24 %.

You can only see this by putting both modes side by side. One red check says the formula is
wrong; this table says **how** it is wrong — and why it is the second mode that nobody ever
finds.
