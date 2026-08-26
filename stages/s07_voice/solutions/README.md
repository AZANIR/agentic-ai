# Solutions — stage 7

Look **after** your own attempt.

| File | Exercise | What it shows |
|---|---|---|
| [`exercise_4_where_the_gain_lives.py`](exercise_4_where_the_gain_lives.py) | 4 | The two parts of the gain on utterances of different lengths |

```bash
python -m stages.s07_voice.solutions.exercise_4_where_the_gain_lives
```

## Why there is only one solution

The rest of the exercises give an unambiguously red check with a readable message — the check's
output is the walkthrough.

Exercise 4 is different: the red check says "the ratio fell below two" and does not say **why**.
And the reason is the most interesting thing in the stage: overlap grows with utterance length,
earlier delivery does not grow at all, and you can only see that by putting several lengths side
by side.

The number "twice as fast" with no mention of utterance length is a number without conditions,
and this is exactly where you see how far without conditions it is.
