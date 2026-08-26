# Solutions — stage 10

Look **after** your own attempt.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_4_what_the_warmup_hides.py`](exercise_4_what_the_warmup_hides.py) | 4 | The same measurement in a cold and a warm process — and how much extra rides into the price of one request |

```bash
python -m stages.s10_capstone.solutions.exercise_4_what_the_warmup_hides
```

## Why there is only one solution

The remaining exercises produce an unambiguously red check with a readable message — the check's
output *is* the walkthrough.

Exercise 4 is different, and that is why it is here. The red check says "the work was executed once
— there is no warm-up" and stops there. **How much** the number changes it cannot say: by the time
its turn comes, the earlier checks have imported everything, and the effect is already gone.

So the solution measures in a **fresh process** — where the first call really is the first. The
difference comes out as 234 against 166: **forty-one percent**, all of it in the direction of
"assembly is expensive".

That is the most useful lesson of the exercise: a suite of checks can hide an effect simply by the
**order in which it runs**. The check was honest; the conditions it ran under were not.
