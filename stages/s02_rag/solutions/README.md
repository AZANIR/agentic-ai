# Solutions — stage 2

Look **after** your own attempt. Taking apart broken code you have already seen is worth far more
than taking apart code you have only read.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_1_filter_after_topk.py`](exercise_1_filter_after_topk.py) | 1 | Both filter orderings side by side, with numbers. And separately — that at `top_k=3` the very same flaw does not show up at all |

```bash
python -m stages.s02_rag.solutions.exercise_1_filter_after_topk
```

## Why there are fewer solutions than exercises

The remaining exercises are mutations that produce **an unambiguously red check with a readable
message**. A solution adds nothing there: the check's output is the walkthrough.

A separate script only makes sense where the check says "broken" and the reason can only be
understood from numbers. Exercise 1 is exactly that: the difference between the right and the
wrong ordering is one document that vanished from the results, and you can only see it by
putting both runs side by side.

Exercises 7 and 8 deliberately have no reference: the first depends on which model you
installed, and the second turns the module into a markdown parser and is therefore left outside
the implementation on purpose (SAD §11).
