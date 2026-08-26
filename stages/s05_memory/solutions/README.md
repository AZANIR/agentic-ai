# Solutions — stage 5

Look **after** your own attempt.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_2_context_rot.py`](exercise_2_context_rot.py) | 2 | Three memories over the same facts. The second one is what all of it is for |

```bash
python -m stages.s05_memory.solutions.exercise_2_context_rot
```

## Why there is only one solution

The rest of the exercises produce an unambiguously red check with a readable message — the
check's output is the walkthrough. A separate script only makes sense where **a green result is
worse than a red one**.

Exercise 2 is exactly that. Memory that stores everything does not crash — it simply puts seven
superfluous facts into the prompt. Memory with the filter after the selection does not crash
either — it returns nothing, and that looks like "the agent forgot".

The red check says "your own fact disappeared". It does not show the intermediate state: how much
superfluous material the naive version actually brings in, and why both failing versions look
normal in the logs. The only way to see that is to put the three implementations side by side on
the same data.
