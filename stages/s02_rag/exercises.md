# Exercises — stage 2

Do these after you have read the [lesson](README.md) and run the demo.

**One rule: break it first, then look, then put it back.** Reading code gives you recognition;
broken code gives you understanding. They are not the same thing.

After each exercise, restore everything:

```bash
git checkout stages/s02_rag/
```

> **One environment trap.** If you replace a number with a number of the same length
> (`0.2` -> `0.0`) and put it back **within the same second**, Python may pick up the stale
> `.pyc`: it compares the modification time to the second, plus the file size. Seeing "a check
> failed even though I already reverted everything"? Clear the cache:
> ```bash
> find . -name __pycache__ -type d -not -path "./.venv/*" -exec rm -rf {} +
> ```

Reference solutions are in [`solutions/`](solutions/). Look **after** your own attempt.

---

## Exercise 1 — Move the access filter after the top-k selection

**Difficulty:** medium · **Time:** 20 min · **The most important exercise of the stage**

In [`store.py`](store.py), inside the `search` method, make the sort run over **all** fragments
and apply the filter to the selected three:

```python
ranked = sorted(range(len(self.fragments)), key=lambda i: float(scores[i]), reverse=True)
closest = [Hit(self.fragments[i], float(scores[i])) for i in ranked[:top_k] if i in allowed]
```

Run the checks, and **try to predict first** what will happen, then look.

<details>
<summary>What actually happens</summary>

**Exactly one** check goes red:

```
FAILURE · store: дозволений документ не зник — фільтр стоїть ДО відбору
```

And the leak check — `внутрішній документ не потрапляє у видачу покупцю` — **stays green**. That
is the main thing to take away from here.

The internal document really did not leak: it was removed, just later. But `returns-policy`,
which was third by closeness and should have reached the shopper, no longer does — two internal
fragments took the slots ahead of it and took the whole result set with them.

The shopper gets "nothing found" for a question that has an answer. No log shows an error. No
leak check fires.

**The moral:** a test for "the bad thing did not happen" is not a substitute for a test that
"the good thing did". These are mirror properties, and covering one of them creates a false
sense that both are covered.

**And a second, sharper point.** Run the walkthrough and look at the two blocks — `top_k=3` and
`top_k=2`. At `top_k=3` the right answer still fits into the three alongside the two internal
ones, and **both orderings give the same result**. The flaw is there, and it is invisible. At
`top_k=2` the internal documents take both slots and the result set goes empty.

The code is broken identically in both cases. All that changes is whether it shows — and that
depends on a parameter which has nothing to do with access control. This is exactly why the
check pins `top_k=2` hard: a check written "the way production has it" would have been green on
broken code.

Walkthrough with numbers: [`solutions/exercise_1_filter_after_topk.py`](solutions/exercise_1_filter_after_topk.py)

</details>

---

## Exercise 2 — Let the model cite itself

**Difficulty:** easy · **Time:** 10 min

In [`answer.py`](answer.py) replace the sources with the ones the model wrote in its own text:

```python
import re
sources=re.findall(r"[a-z-]+#\d", model_text) or [h.fragment.label for h in result.hits],
```

<details>
<summary>What happens</summary>

One check goes red:

```
FAILURE · answer: посилання, вигадане моделлю, не стає джерелом відповіді
```

The check hands the model the text "According to document `secret-internal-policy#9` a return is
impossible". No such document exists — and now it stands in the `sources` field as the source of
the answer.

Note the shape of this failure: **an invented reference looks exactly like a real one**. There is
no signal by which a reader could tell them apart. The mechanism introduced precisely to
separate a grounded answer from an invented one has itself become a source of invention.

That is why the source is attached by the system (stage ADR-0003), not by the model following an
instruction.
</details>

---

## Exercise 3 — Remove the access-level binding

**Difficulty:** medium · **Time:** 15 min

In [`tools.py`](tools.py), inside `tool_for`, replace `partial(search_knowledge_base,
access=access)` with the bare `search_knowledge_base`.

Predict first: is this a leak or not?

<details>
<summary>What happens</summary>

**There is no leak.** In `search_knowledge_base` the access level defaults to `PUBLIC`, so
without the binding everyone sees public material — that is, less rather than more. This is the
right default: err in the direction of showing less.

But this goes red:

```
tools: оператор ОТРИМУЄ внутрішній документ — прив'язка доступу справді працює
```

The support operator has stopped seeing the internal refund thresholds. The tool silently hands
them the public answer, and they will just as silently quote the wrong amount to a shopper.

This exercise is the pair to the first. The first shows that the filter can be put in the wrong
place; this one shows that the binding can be forgotten altogether, and that **the leak check
will again fail to see it**. "Nothing found" is not a leak either.
</details>

---

## Exercise 4 — Drop the threshold to zero

**Difficulty:** easy · **Time:** 10 min

In [`tools.py`](tools.py) set `THRESHOLD = 0.0` and ask the tool about something the knowledge
base has nothing on at all.

<details>
<summary>What happens</summary>

```
FAILURE · tools: питання не по темі дає чесне «не знайдено», а не найближчий шум
```

The query "what is the weather in Kyiv tomorrow" returns the closest fragments with scores
0.141, 0.129 and 0.126 — the jug, shipping, the embroidered shirt. None of them has anything to
do with weather, but **something closest always exists**: cosine always returns a number, and
the largest of a set of numbers always exists.

The threshold is the only place where the system can say "I do not know". Remove it and the
agent gets three random paragraphs, puts them in the prompt, and asks the model to answer from
them. The model will honestly try.

See if you can find a threshold at which "what is the weather" returns nothing while "how many
days do I have to return this" still finds the policy. Hint: the first gives 0.141, the second
0.503. There is more room to manoeuvre than it looks — which is precisely why this number is
worth tuning on your own data rather than taking from a textbook.
</details>

---

## Exercise 5 — Hand the access level to the model

**Difficulty:** medium · **Time:** 15 min

In [`tools.py`](tools.py) add `access` to the tool's schema:

```python
"properties": {
    "access": {"type": "string"},
    "query": {...},
},
```

<details>
<summary>What happens</summary>

```
tools: інструмент має ту саму форму, що й на етапі 1
```

The check asserts `list(params["properties"]) == ["query"]` — exactly one lever. Not "query is
among the others" but **only** query.

The difference is not pedantry. The first version of this check said `"query" in
params["properties"]`, and the mutation adding `access` sailed straight through it. The check
was green, the property was broken.

Now try the next step: make the model pass `access="internal"` (you can swap the script in
`run.py`). Stage 1's validator should reject the extra argument via
`additionalProperties: false` — make sure it rejects it **before** the function is called, not
after.
</details>

---

## Exercise 6 — Turn off fragment overlap

**Difficulty:** easy · **Time:** 10 min

In [`chunk.py`](chunk.py) replace `step = size - overlap` with `step = size`.

<details>
<summary>What happens</summary>

**Three** checks go red, and the third is more interesting than the first two:

```
FAILURE · chunk: перекриття не плодить фрагмент, цілком вкладений у попередній
chunk: перекриття зберігає думку, що припала на стик
kb: пастка AC-05 справді пастка — без фільтра внутрішній виграє
```

The first two are obvious.

The third is not: without overlap the content of the fragments was redistributed such that the
internal document **stopped winning** on closeness for the question about the refund amount.

Which means the exercise broke not only the chunking but also the **fixture** the access-filter
check rests on. Had that fixture check not existed, AC-05 would still be green — but it would be
checking a coincidence rather than a mechanism: the internal document does not appear in the
results not because it was filtered out but because it was never the closest in the first place.

**The moral:** a check asserting that the data is still arranged the way it was meant to be looks
redundant right up until it saves you.
</details>

---

## Exercise 7 — Switch to real embeddings

**Difficulty:** medium · **Time:** 30 min · **No API key needed**

```bash
pip install -e ".[embed]"
# .env:  EMBEDDINGS_PROVIDER=fastembed
python -m stages.s02_rag.run
```

Compare scene 1 with what you saw before. Does "як оформити відмову від покупки" still fail to
find the returns policy — or does it find it now?

<details>
<summary>What to think about</summary>

The point is not "it got better" but **what exactly changed and by how much**. Write down both
sets of numbers.

The second, more important question: how many checks went red? Their numbers are pinned to the
word hash. That is not an oversight — it is the honest price of a deterministic fixture, and it
is worth seeing before you write checks tied to specific similarity scores.

Third: `fastembed` pulls a model onto disk and the first run is noticeably longer. Compare the
time of `python -m stages.s02_rag.check` before and after. That is the same price production
pays on every cold start.
</details>

---

## Exercise 8 — Split on headings instead of on words

**Difficulty:** hard · **Time:** 60 min

Right now [`chunk.py`](chunk.py) cuts by word count, and a fragment boundary can land in the
middle of a sentence. Write an alternative that splits on markdown headings and compare the
results.

<details>
<summary>What to think about</summary>

This exercise deliberately has no reference solution: it turns the module into a markdown
parser, which is exactly why the main implementation does not have it (recorded in SAD §11 as an
accepted risk).

What is worth measuring rather than guessing:
- did the top-1 score on the literal question go up;
- what happened to `tiny.md`, the one-sentence document;
- did any fragments appear that are too large for the context window.

Splitting on structure is almost always better — but "almost always" is not "always", and the
difference is only visible in the numbers.
</details>
