# Solutions — stage 4

Look **after** your own attempt.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_1_naive_parsers.py`](exercise_1_naive_parsers.py) | 1 | Three parsers over five responses. The last row of the table is what all of it is for |

```bash
python -m stages.s04_mcp.solutions.exercise_1_naive_parsers
```

## Why there is only one solution

The rest of the exercises produce an unambiguously red check with a readable message — the
check's output is the walkthrough. A separate script only makes sense where **a green result is
worse than a red one**.

Exercise 1 is exactly that. `json.loads` over the whole response fails — and that is honest. A
regex over the text **never** fails: it returns a structure of the right shape with the wrong
contents, and no log will say a word about it. The only way to see the difference is to put both
side by side.

The numbers of every exercise are pinned by machine:

```bash
python scripts/mutate.py s04 --expect
```
