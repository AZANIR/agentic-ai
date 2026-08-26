# Exercises — stage 1

Do these after you have read the [lesson](README.md) and run the demo.

**One rule: break it first, then look, then put it back.** Reading code gives you recognition;
broken code gives you understanding. They are not the same thing.

After each exercise, restore everything:

```bash
git checkout stages/s01_agent_loop/
```

Reference solutions are in [`solutions/`](solutions/). Look **after** your own attempt.

---

## Exercise 1 — Remove the confirmation gate

**Difficulty:** easy · **Time:** 10 min

In [`gate.py`](gate.py) replace `and tool.irreversible` with `and False` — the gate stops firing
at all.

> Do not make the "intuitive" edit — dropping just the word `not` from the condition in
> `loop.py`. That makes the gate block **always** rather than never, and the demo output does
> not change. This is a real trap: the first version of this lesson described exactly that as
> the correct edit.

Then run, in this order:

```bash
python -m stages.s01_agent_loop.run
python -m stages.s01_agent_loop.check
```

**What should happen:**

- Scenario 4 of the demo now **processes the return** instead of stopping.
- **Three** checks go red, and each names its own reason:
  `виконано попри блокування` · `незворотну функцію виконано без підтвердження` ·
  `у трейсі демо немає step_blocked`.
- The checks for the confirmed path and for reversible tools stay green.

**A question you should be able to answer:** all three failures are an `AssertionError` carrying
a description of what exactly was violated. Why does that matter more than the bare fact that
"something went red"? Hint: imagine a test that goes red because the fake ran out of script.

---

## Exercise 2 — Fool the validator with a boolean

**Difficulty:** medium · **Time:** 20 min

In [`validate.py`](validate.py) comment out the lines that exclude `bool` from the numeric type
check.

Add a fourth tool to [`tools.py`](tools.py) with an integer parameter — for example:

```python
def set_delivery_window(days: int) -> str:
    return f"Вікно доставки: {days} дн."
```

Register it with a schema where `days` has type `integer`. Now write a check in which the fake
model asks for this tool with `{"days": True}`.

**What should happen:** with `bool` no longer excluded, `True` **passes** validation and the
function receives `True` instead of a number. In the output you will see
`Вікно доставки: True дн.`

**Question:** why is `isinstance(True, int)` true in Python? What other types hold a similar
trap?

---

## Exercise 3 — Squeeze the step limit

**Difficulty:** easy · **Time:** 10 min

Set `AGENT_MAX_STEPS=1` in your `.env` and run the demo.

**What should happen:** scenario 1 no longer produces an answer. The model gets as far as
**asking** for the tool — and on the second step, the one where it would have answered with
text, there is no limit left.

**Question:** what is the minimum number of steps an agent needs to answer using one tool call?
And with two sequential calls? Derive the formula.

Do not forget to set `AGENT_MAX_STEPS=8` back.

---

## Exercise 4 — Ruin a tool description

**Difficulty:** medium · **Time:** 30 min · **Needs a provider key**

This exercise only makes sense **with a real model** — the fake follows a script and reads no
descriptions. Set up Groq using the checklist in the lesson.

In [`tools.py`](tools.py) replace the description of `get_order_status`:

```python
description="Does a thing.",
```

Run the demo and look at scenario 1.

**What should happen:** the model will either pick the wrong tool, or ask a clarifying question,
or invent an answer without calling anything. The exact behaviour depends on the model — which
is precisely what makes the exercise interesting.

**Question:** where is the bug now, in the model or in the code? Who is responsible for the
agent having picked the wrong tool?

---

## Exercise 5 (optional) — Offer the model a tool that does not exist

**Difficulty:** hard · **Time:** 30 min

Write a check in which the fake model asks for a tool called `delete_everything`, which is not
in the registry.

**What should happen:** the loop does not crash. Look in [`loop.py`](loop.py) to see how an
unknown name is handled and what exactly goes back to the model.

**Question:** why does that response contain the list of available tools? What happens if you
take it out?

---

## When to consider the stage passed

Not when every exercise is done, but when you can answer the three questions in
[`CHECKLIST.md`](CHECKLIST.md) **without a hint**.
