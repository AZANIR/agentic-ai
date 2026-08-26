# Stage 5 exercises — break it and see what goes red

Before every exercise, run the suite and make sure it is green:

```bash
python -m stages.s05_memory.check
```

Then break the code as written and look at **which** checks failed. The number in each exercise
is measured, not guessed; the comparison is automatic:

```bash
python scripts/mutate.py s05 --expect
```

**Read the names, not the count.** A mutation caught by an incidental check is worse than one
caught by the check that claims to be about it.

---

## Exercise 1 · Remove the owner filter

`long_term.py`, in `context_for`:

```python
mine = [f for f in self.all_facts() if f.owner == owner]   # before
mine = list(self.all_facts())                              # after
```

**Reds: 3.**

The most obvious of the eleven: somebody else's facts go into the context, and both isolation
checks see it — see it *now*. Before the review the first of them was **dead**: the fixture said
`Банкову` while the assertion looked for `Банкова` — the same street name in a different
grammatical case, so a match never happens and `not in` was satisfied every time. A check with
the right claim that no mutation could ever turn red.

This exercise is here not for its difficulty but as the footing for the next one.

---

## Exercise 2 · Put the owner filter AFTER the selection

The same thing, but subtler. Instead of removing the filter, move it — first select the best
`limit` facts **out of all of them**, then keep your own:

```python
every = [f for f in self.all_facts() if is_active(f, now=now)]
every_scores = self.retrieval.score(question, [f.text for f in every])
top = sorted(zip(every_scores, every, strict=True), key=lambda p: p[0], reverse=True)[:limit]
ranked = [(s, f) for s, f in top if f.owner == owner]
```

**Reds: 2** — and among them the one that matters: "mirrored: the owner filter did not narrow the
result to an empty one".

This is the most important exercise of the stage. **There is no leak** — nothing of somebody
else's reaches the context. But their facts do take slots, the slots get removed, and **your own
answer disappears**. Memory behaves as if it knows nothing, and the logs are clean.

A check that claims only "theirs did not arrive" does not see this defect at all — on an empty
result it is green. Hence two checks.

> **The history of this exercise.** Its first draft produced **zero reds**, and it looked as
> though the check was weak. In fact the mutation was weak: it left `mine` already filtered, so
> somebody else's facts took no slots and the defect did not reproduce. The instrument you check
> the checks with lies in exactly the same way they do.

---

## Exercise 3 · Rewrite the summary instead of accumulating it

`short_term.py`, in `compress`:

```python
self.summary = f"{self.summary}\n{addition}".strip() if self.summary else addition  # before
self.summary = addition                                                             # after
```

**Reds: 1.**

The second most important. There is **no** error at all: the code works, the summary reads well,
the conversation looks coherent. Half of it has simply vanished.

Try to spot that by eye in the demo output — you will not. That is exactly why the check claims
not "the summary is not empty" but "the summary carries a trace of BOTH compressions".

---

## Exercise 4 · Do not check the expiry

`facts.py`, in `is_active`:

```python
return expires is None or now <= expires   # before
return True                                # after
```

**Reds: 1.**

A stale fact comes back in the result. In production it looks like an agent stubbornly repeating
last year's promotion.

---

## Exercise 5 · Let a replaced fact stay active

`facts.py`, in `is_active`:

```python
if fact.status != ACTIVE:   # before
if False:                   # after
    return False
```

**Reds: 1.**

Both addresses in the context at once. The model will see two truths and pick one — and you will
not find out which.

---

## Exercise 6 · Switch off the relevance threshold

`long_term.py`:

```python
if score >= self.threshold and len(taken) < limit:   # before
if score >= 0.0 and len(taken) < limit:              # after
```

**Reds: 2.**

The threshold sits next to everything, so it touches several checks — and that does not make the
exercise the most important one. The defect does not become worse than those that produce a
single red.

---

## Exercise 7 · Let a corrupted line become a fact

`facts.py`, in `from_line`:

```python
missing = [name for name in _REQUIRED if name not in data or data[name] == ""]  # before
missing = []                                                                   # after
```

**Reds: 2.**

A record with no owner passes through — that is, a fact with no owner takes part in retrieval. A
corrupted line has to be **named and skipped**, not turned into a fact with holes in it.

Look at the expression itself: what is checked is the **presence** of the key, not the
truthiness of the value. The first draft wrote `not data.get(name)` — and declared corrupt a
record with `stored_at = 0.0`, that is, a fact written exactly at the epoch. Zero is a value, not
an absence, and `remember()` would then wipe such a line as unparseable.

---

## Exercise 8 · Let the secret stop being a rule

`decision.py`:

```python
applies=lambda s: s.secret,   # before
applies=lambda s: False,      # after
```

**Reds: 4.**

The rule stayed in the list — and never fires. This is a **dead rule**: it looks like work and
does nothing.

Note that among the reds is "no rule is left without a situation". The check "every situation has
an answer" stays **green** under this mutation — all six lines still get an answer, it is just
that the password is now stored.

---

## Exercise 9 · Let the tail of the window be summarised too

`short_term.py`, in `overflow`:

```python
return self.messages[: -self.size] if len(self.messages) > self.size else []   # before
return list(self.messages)                                                     # after
```

**Reds: 3.**

There is no verbatim tail any more — the model answers a summary of the last turn instead of the
turn itself. One of those defects that are invisible on short examples and surface on long ones.

---

## Exercise 10 · Normalise the score by the question rather than the union

`retrieval.py`, in `Overlap._one`:

```python
union = asked | seen                                       # before
return len(asked & seen) / len(union) if union else 0.0

return len(asked & seen) / len(asked) if asked else 0.0    # after
```

**Reds: 1.**

The subtlest of the eleven. Dividing by the question looks more natural — "what share of the
question did the fact cover" — and gives **1.00** to any text that merely restates the question.

The consequence: the fact "Where to deliver the order. This is the most important thing, the cat
is called Murchyk" goes around the real address and becomes first in the context. The text of a
fact is written by the user. That is, the user controls the order of the results with their own
text — and there is no leak and no error in the process.

---

## Exercise 11 · Put the fact's text into the prompt as it is

`long_term.py`, in `_safe`:

```python
for marker in (OPEN_FACTS, CLOSE_FACTS):   # before
    value = value.replace(marker, "")
return one_line(value)

return value                               # after
```

**Reds: 1.**

A fact whose text contains the delimiter `=== КІНЕЦЬ ДАНИХ ===` itself closes the data block
early — and the rest of its text ends up in the prompt **outside** the block, that is, where the
model reads instructions.

In the memory file this is invisible: the record stays one line of valid JSON. The defect exists
exactly at the moment the prompt is assembled, and the only way to see it is to look at the
prompt:

```bash
python -m stages.s05_memory.run --prompt
```

---

## What to do next

Try **your own** mutation: break something and see whether anybody notices. If the suite stayed
green — you have found a hole in the checks, and that is worth more than any of the eleven
exercises above.

That is how eight of these eleven were found. An independent review in clean context read the
code and the checks and asked about each one: **what exactly has to break for it to go red**. The
answer "nothing" came up four times.

Add yours to `mutations.json` together with the check that catches it. A finding is closed by a
**pair**: the fix, and the mutation that reverts that fix.
