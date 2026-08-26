# Solutions — stage 6

Look **after** your own attempt.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_1_two_workers.py`](exercise_1_two_workers.py) | 1, 14 | The three faces of one piece of state in process memory, side by side and as numbers |

```bash
python -m stages.s06_platform.solutions.exercise_1_two_workers
```

## Why there is only one solution

The rest of the exercises produce an unambiguously red check with a readable message — the
check's output is the walkthrough. A separate script only makes sense where **a green result is
worse than a red one**.

Exercise 1 is exactly that, and it is the least convincing of all sixteen. A counter in process
memory does not break: requests go through, refusals arrive, metrics get counted. The only way to
see the defect is to put a second number next to it — and that is precisely why the red check here
explains less than three lines of output.
