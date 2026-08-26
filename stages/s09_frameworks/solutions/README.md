# Solutions — stage 9

Look **after** your own attempt.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_3_where_the_overhead_hides.py`](exercise_3_where_the_overhead_hides.py) | 3 | Three observer positions on the same run — and the direction of each one's error |

```bash
python -m stages.s09_frameworks.solutions.exercise_3_where_the_overhead_hides
```

## Why there is only one solution

The remaining exercises produce an unambiguously red check with a readable message — the check's
output *is* the walkthrough.

Exercise 3 is different: the red check says "overhead on a purely contractual request" and stops
there. What is interesting starts after that line — because **a broken counter looks exactly like
an intact one**.

The solution puts three observer positions side by side: at the provider boundary, inside the
implementation, and in the framework's own reporting. All three produce a number. Two produce zero
where the truth is 66, and they are wrong **in the same direction**: they make the scaffolding look
cheaper than it is.

That is impossible to notice from the table. A zero for the baseline is correct, and a zero for a
framework looks like good news — which is why the check proves the instrument at **both** edges
instead of hoping that some framework will misbehave.
