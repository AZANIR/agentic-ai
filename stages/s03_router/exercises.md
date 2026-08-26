# Exercises — stage 3

Do these after you have read the [lesson](README.md) and run the demo.

**One rule: break it first, then look, then put it back.**

```bash
git checkout stages/s03_router/
```

> **An environment trap.** If you replace a number with a number of the same length and put it
> back **within the same second**, Python may pick up the stale `.pyc`. Seeing "a check failed
> even though I already reverted everything"? Clear the cache:
> ```bash
> find . -name __pycache__ -type d -not -path "./.venv/*" -exec rm -rf {} +
> ```

The numbers below are **measured**, not guessed, and pinned by machine:

```bash
python scripts/mutate.py s03 --expect
```

The script applies every mutation on this page, counts the red checks, and fails if the number
disagrees with what is promised here. It exists because the first edition of this page promised
"nine red" in exercise 3 when in fact there are three: the mutation had been measured against
code that did not compile, and the nine red came from a broken specialist.

The measurements were taken **with LangGraph installed**; without it, exercises 1 and 2 produce
one red fewer — that check is marked `НЕ ПЕРЕВІРЕНО` rather than passing.

---

## Exercise 1 — Let the graph take the model at its word

**Difficulty:** easy · **Time:** 10 min

In [`graph.py`](graph.py) replace `if choice not in SPECIALISTS:` with `if False:`.

<details>
<summary>What happens</summary>

**Five** checks go red (four if LangGraph is not installed):

```
FAILURE · graph: вигадана моделлю назва вузла не стає маршрутом
graph: жоден прогін не завершується без названої причини (AC-02)
FAILURE · graph: збій провайдера не лишає прогін без названої причини
e2e · демо проходить офлайн, показує п'ять сцен і пише трейс
МЕЖА · langgraph: ті самі маршрути
```

The first is obvious. The rest are not, and the whole point is in them: without the validation
the graph tries to take `SPECIALISTS["weather"]`, gets a `KeyError`, and the run **does not
finish at all**. What broke is not the scenario you broke but an **invariant**: "every run ends
with a named reason".

Checks on invariants catch what you were not looking for. Which is exactly why their value is
invisible until they fire.
</details>

---

## Exercise 2 — Remove the revision limit

**Difficulty:** easy · **Time:** 10 min · **Start with this one**

In [`graph.py`](graph.py) replace `if state.revisions >= state.revision_limit:` with
`if state.revisions >= 10_000:` — the limit formally exists, but it is unreachable.

<details>
<summary>What happens</summary>

**Two** checks (one without LangGraph):

```
FAILURE · graph: цикл ревізій зупиняється лімітом, а не крутиться далі
МЕЖА · langgraph: обидві реалізації однаково зупиняються лімітом ревізій
```

The second is worth noting separately: that check was added **after the review**. Before it, the
second implementation had no revision loop at all — `add_edge("specialist", END)` ended the run
immediately — while the lesson claimed the return edge was there. AC-06 did not see it, because
across the six demo requests no revision ever happens.

And now the main part. Put `if False:` in place of `if state.revisions >= 10_000:` and watch what
happens: **the suite hangs**. It does not fail — it hangs.

Run the walkthrough and look at the numbers:

```bash
python -m stages.s03_router.solutions.exercise_2_revision_cost
```

In production that `if False` would raise no error at all. The model will happily answer as many
times as it is asked; no exception, no line in the logs. The only signal arrives at the end of
the month, as a number.
</details>

---

## Exercise 3 — Give the specialist a fixed access level

**Difficulty:** medium · **Time:** 20 min · **Do both halves**

In [`specialists.py`](specialists.py), inside `_knowledge`, replace `access=state.access` with the
literal `access="public"`. (A literal specifically: the `PUBLIC` constant is not imported there,
and the linter will not leave it, since nothing uses it.)

<details>
<summary>What happens — first half</summary>

**Four** checks:

```
graph: оператор тим самим маршрутом ОТРИМУЄ внутрішній документ
FAILURE · specialists: оператор ОТРИМУЄ те, що йому можна — дзеркальна перевірка
FAILURE · graph: текст запиту не підвищує рівень доступу
e2e · демо проходить офлайн, показує п'ять сцен і пише трейс
```

Now stop and look at **what is not among them**. There is no leak check at all: `"public"` is
fail-safe, everyone sees less than they are allowed to. There is nothing to leak.

What goes red is the mirror image: **the operator has stopped seeing what they are permitted to
see.** They will just as silently quote the wrong refund amount to a shopper, and no log will
show an error.

Now the second half.
</details>

Replace `access="public"` with `access="internal"` and run it again.

<details>
<summary>What happens — second half</summary>

**Five** checks, and the set barely overlaps with the first half:

```
FAILURE · graph: внутрішній документ не доходить до покупця через передачу
FAILURE · graph: дозволена відповідь ДОХОДИТЬ — передача не звузила видачу до нуля
FAILURE · graph: текст запиту не підвищує рівень доступу
FAILURE · specialists: спеціаліст знань бере рівень доступу зі стану, не з аргументів
FAILURE · specialists: оператор ОТРИМУЄ те, що йому можна
```

Now this is a leak, and different checks catch it.

**Two mutations of one line, two opposite flaws, two almost disjoint sets of red.** Neither set
covers the other — and that is exactly why there are three access checks rather than one.
</details>

---

## Exercise 4 — Allow writes to the access level

**Difficulty:** easy · **Time:** 10 min

In [`state.py`](state.py) break the immutability — in two different ways, one after the other:

```python
if False:                # instead of  if name in FROZEN:
FROZEN = frozenset()     # or like this: the list is empty
```

<details>
<summary>What happens</summary>

**Exactly one** goes red, and for both ways of breaking it:

```
FAILURE · state: рівень доступу не можна перезаписати з вузла (ADR-0003)
```

And that is enough, because right now no node writes to that field. That is the whole point: the
check guards not the current behaviour but the **possibility** of changing it.

The second way went unnoticed for a long time. The first version of this check said
`for name in sorted(FROZEN)` — that is, it iterated over the very constant it was guarding. Empty
`FROZEN` and the loop body never runs: **the suite stays entirely green while the door stands
open.** An independent review found this; the contents of `FROZEN` are now asserted on a line of
their own.

Now take the next step and write that possibility out by hand — add a line to `run_graph`
(`graph.py`) that takes the access level from the text of the query, and see how many checks
catch that instead. The difference between "the door is unlocked" and "somebody came in" is two
different events as well, and the checks for them are different.
</details>

---

## Exercise 5 — Take the list of competences away from the model

**Difficulty:** easy · **Time:** 10 min

In [`graph.py`](graph.py) replace `catalogue=catalogue()` with `catalogue=""`.

<details>
<summary>What happens</summary>

```
graph: модель бачить опис КОЖНОЇ компетенції, інакше вибір неможливий
```

One check — and no other, because on the fake the route is written into the script and does not
depend on the prompt. This is exactly the limit the lesson names outright: **on the fake the
route is right by construction.**

Now put in a real key and run the demo again with the empty list. Now you can see what actually
broke — and see how far from a formality the prompt check was.
</details>

---

## Exercise 6 — Remove one situation from the checklist

**Difficulty:** medium · **Time:** 15 min

In [`decision.py`](decision.py) replace `signals={"many_tools": True}` with `signals={}`.

<details>
<summary>What happens</summary>

```
decision: кожна ситуація має рівно одну відповідь
decision: кожне правило вмикається якоюсь ситуацією
FAILURE · decision: склад чекліста закріплено — підміна клонами не проходить тихо
FAILURE · decision: таблиця в DECISION.md збігається з тим, що дає код
```

Four red, and the last is a story of its own: `DECISION.md` is assembled from the code, so a
change in `decision.py` desynchronised the prose in the same motion. The second is the one all of
this is for. The rule `many_tools` stayed in the list, but now no situation switches it on: a
typo in a signal name would have lived there forever and never surfaced.

In stage 2 the same check was added **after** a review found exactly this gap in the "RAG or
fine-tuning" checklist. Here it was there from the start — and that is probably the best proof
that reviewing the previous stage paid for itself.
</details>

---

## Exercise 7 — Install LangGraph and break its version

**Difficulty:** medium · **Time:** 30 min

```bash
pip install -e ".[s03]"
python -m stages.s03_router.check
```

<details>
<summary>What to think about</summary>

First make sure the line `AC-06 перевірено: 7 маршрутів збіглися з власним графом` has appeared.
Before installation there was a different one in its place, saying the criterion was **not
verified**. Write down how much time this check added to the run.

Now break one of the implementations — stop recording `state.visit(choice)` in
`langgraph_impl.py`, say — and see how the check names the route divergence.

The main question of the exercise: **why keep two implementations at all?** The answer is in
ADR-0001, and it names the price honestly: two bodies of code can drift apart. The check exists
precisely because relying on the author's discipline here is not an option.
</details>

---

## Exercise 8 — Add a fourth specialist

**Difficulty:** hard · **Time:** 45 min

Add a specialist — for shipping, say — and **change nothing else**.

<details>
<summary>What to think about</summary>

This exercise tests the stage's thesis in practice: if a supervisor is an agent whose tools are
agents, then adding a competence should cost exactly what adding a tool cost in stage 1.

What is worth measuring rather than guessing:

- how many lines you had to change outside `specialists.py`;
- how many checks went red immediately after the addition (and whether any of them are the ones
  pinning counts — that is normal, that is what they are for);
- **whether you had to pass anything to the new specialist by hand.** If not, ADR-0003 just paid
  for itself in front of you: the access level was already in the state;
- how the route for the other six requests changed on a real model once there were four
  competences.

The last point is the most interesting and the least obvious. A new competence description
changes the choice for more than its own requests.
</details>
