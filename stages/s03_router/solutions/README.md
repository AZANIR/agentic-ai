# Solutions — stage 3

Look **after** your own attempt.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_2_revision_cost.py`](exercise_2_revision_cost.py) | 2 | How many model calls one request costs at different revision limits — and why "remove the limit" raises no error at all in production |

```bash
python -m stages.s03_router.solutions.exercise_2_revision_cost
```

## Why there is only one solution

The rest of the exercises produce an unambiguously red check with a readable message — there the
check's output is the walkthrough. A separate script only makes sense where the check says
"broken" and the scale can only be understood from numbers.

Exercise 2 is exactly that: the red check shows the limit is gone and **says nothing about the
price**. The price is a column that gets multiplied by the number of requests per month.

The numbers of every exercise are pinned by machine:

```bash
python scripts/mutate.py s03 --expect
```
