# Stage 8 exercises — break it and watch what turns red

Before every exercise, run the suite and make sure it is green:

```bash
python -m stages.s08_eval.check
```

The numbers are measured, not guessed; the reconciliation is automatic:

```bash
python scripts/mutate.py s08 --expect
```

**Read the names, not the count.** A mutation caught by an incidental check is worse than one
caught by the check that asserts about it.

**The most important ones are not about evaluation but about the honesty of the report** —
exercises 1, 2, 3 and 11. **Exercises 12–14 bring back defects found by an independent
review** — all three lived until then unnoticed, and all three break `--real` specifically,
that is, the mode in which a reader was supposed to repeat the proof against a real model. They
share one property, and it is what makes them the most expensive: each of them makes the report
**greener**. The code keeps working, the numbers stay plausible, and the run looks nicer. A
mistake that shows worse numbers is found in a day. A mistake that shows better ones is never
looked for at all.

---

## Exercise 1 · An empty level is counted as passed

`stages/s08_eval/levels.py`:

```python
# before
        return Verdict(COMPONENT, UNSCORED, DETERMINISTIC, "кроків підсистем у трейсі немає")

# after
        return Verdict(COMPONENT, PASSED, DETERMINISTIC, "кроків підсистем у трейсі немає")
```

**Red: 2.**

A trace with no subsystem steps is no longer "unscored" but "passed". The difference looks
cosmetic — until you notice the direction it pulls in: **the poorer the trace, the greener the
report**. A run in which tracing fell over entirely will show a hundred percent at the
component level.

The check on the third state turns red — and, separately, the teeth check (AC-09): it breaks
the trajectory level and demands that the other levels **not** suffer for it.

---

## Exercise 2 · The denominator is taken from the evaluated, not from all

`stages/s08_eval/report.py`:

```python
# before
        return self.count(level, state) / self.total if self.total else 0.0

# after
        judged = self.total - self.count(level, UNSCORED)
        return self.count(level, state) / judged if judged else 0.0
```

**Red: 1.**

The most insidious of them all. The formula looks **more honest** than the original: "we count
the share of what we managed to evaluate" — exactly what a careful engineer would say.

The consequence is the opposite, and it has two different faces, depending on **how** the judge
fails. The solution measures both:

```bash
python -m stages.s08_eval.solutions.exercise_2_the_denominator_climbs
```

When the failures are **uniform** (the quota ran out), the flattering share stays inside a band
of four percentage points while coverage collapses from twenty-one cases to three. The number
does not lie — it **goes silent** about exactly the thing that makes it meaningful.

When the failures are **correlated** — the judge stumbles on empty and truncated answers,
because a short body produces a request the provider rejects — the cases that drop out are
mostly the failing ones. The flattering share goes 57 % → 71 % → 85 % → **100 %**, while the
honest one falls to 24 % and only five cases out of twenty-one could be evaluated. The
instrument broke, and the report showed perfect quality.

The first mistake gets found eventually — when somebody asks how much was evaluated at all.
Nobody ever goes looking for the second: it arrives with good news.

And that is the reason the check hands over a judge that answers **every other time** rather
than one that stays silent completely. Total refusal zeroes both the numerator and the
denominator, and any formula gives zero: the mistake hides exactly where people look for it
most often.

---

## Exercise 3 · A judge's failure is counted as the agent's

`stages/s08_eval/levels.py`:

```python
# before
        return Verdict(E2E, UNSCORED, JUDGED, str(error))

# after
        return Verdict(E2E, FAILED, JUDGED, str(error))
```

**Red: 1.**

The **instrument** failed, and the agent was blamed. Two different facts merged into one, and
the worst part is not that the number is wrong — it is that it is wrong in a **plausible**
direction: with no key the report will show zero percent on e2e, and somebody will go hunting
for a regression in the agent.

The third state exists precisely for this. "Broken" and "not checked" are different events, and
a suite that merges them stops distinguishing a broken system from an interrupted run.

---

## Exercise 4 · A tie stops being a value of its own

`stages/s08_eval/bias.py`:

```python
# before
    if verdict.winner == TIE:
        return TIE

# after
    if verdict.winner == TIE:
        return order[0]
```

**Red: 1.**

A tie starts reading as "the one submitted first won". It looks like a trifle — and the
detector breaks **in both directions** at once.

Against an honest judge that says "tie" every time on identical answers, presenting AB gives A
and presenting BA gives B — and the detector reports a flip where there is none. That is why
the **mirror** check turns red (AC-05b) rather than the main one: a detector that always finds
bias cannot tell a biased judge from an honest one, and therefore is not a detector.

---

## Exercise 5 · Length bias gets a "within the noise" threshold

`stages/s08_eval/bias.py`:

```python
# before
        if gap > 0:

# after
        if gap > 2:
```

**Red: 1.**

The threshold sounds sensible: "a point or two of difference is noise, we react to what is
substantial". But the pairs for length are built so that the second answer is **literally the
first plus truthful extra text**. The content is the same, so there is nothing to add points
for.

So any strictly positive preference is a point for length, and a threshold here is not merely
unnecessary: it is **impossible**. Both gaps in the set equal two (3 → 5 and 4 → 6), and a
threshold of two silences exactly what the detector exists for.

---

## Exercise 6 · The judge loses its position bonus

`stages/s08_eval/judge.py`:

```python
# before
        left = self._points(first, expected) + self.position_bonus

# after
        left = self._points(first, expected)
```

**Red: 1.**

What breaks is not the detector but the **material**: the fake judge stops being biased, and
there is nothing left to find.

The exercise is about something else. Read the message of the check that turned red and ask
yourself whether you would tell this case apart from "the detector broke" — with nothing but a
report showing zero findings in your hands. That is exactly why the mirror half (exercise 4) is
mandatory: zero findings proves something only when there is a run beside it where the count is
not zero.

---

## Exercise 7 · The sampler sends everyone to the judge

`stages/s08_eval/online.py`:

```python
# before
    return int.from_bytes(digest, "big") % BUCKETS < share * BUCKETS

# after
    return len(digest) > 0
```

**Red: 2.**

Ten percent declared, a hundred going to the judge. The function stays **deterministic** — the
same identifier gives the same decision — so a flicker check will miss this.

And that is the lesson: determinism is not correctness. A sampler that always says "yes" is
deterministic too, and it also "matches the declared share" — any share, if you do not
reconcile it against a number.

The bill for that mistake comes not from the checks but from the provider.

---

## Exercise 8 · The grouping key is fixed again

`stages/s08_eval/trajectory.py`:

```python
# before
        name = key(step)

# after
        name = step.get("trace_id")
```

**Red: 4.**

The most red ones — and that is exactly what makes this mutation instructive. Grouping by
`trace_id` is **correct** for stages 1–5 and 7: there is one `trace_run` per scenario there. On
the stage 6 service, where one `trace_run` lives for the whole life of the process, it
collapses **the entire file** into one trajectory.

The worst part is that it "works" while doing so: totals are computed, the report prints, there
is no error. It is just that all the service's traffic is now one run with one answer.

Compare the four names that turned red with the single name in exercise 11: they share one
thing — blind measurements. That is not a coincidence. Both mutations strike at **how** the
evaluator sees the service's trace; this one breaks the grouping, that one the interpretation
of what the trace does not contain.

---

## Exercise 9 · Step order is taken from the file

`stages/s08_eval/trajectory.py`:

```python
# before
        trajectory.steps.sort(key=lambda step: step.get("seq", 0))

# after
        pass
```

**Red: 1.**

This exercise is interesting because the mutation was **almost impossible to catch**. While a
single appender is writing the file, the order in the file matches `seq`, and the sort changes
nothing: a check that reads a trace it has just written stays green without it.

Order breaks where the file was assembled from several sources — stitched shards, a buffered
log shipper, a tail caught up after a crash. So the check **deliberately reverses the lines**
of the written file: that is the cheapest model of exactly this case.

The moral is broader than the stage: a property that cannot be violated on the happy path
requires the check **itself** to create the conditions in which it is violated.

---

## Exercise 10 · Edge is declared by a status instead of being observed

`stages/s08_eval/cases.py`:

```python
# before
        said = [act for act in self.acts if act.fields.get("answer", "").strip()]
        return not said

# after
        return self.status != "ok"
```

**Red: 1.**

Edge stops being read from the trace and starts being read from a field the author sets by
hand.

The interesting part here is **why the red one is not the one you expect**. The number of edge
cases barely changes, so the "at least a third" requirement holds. What turns red is the mirror
half: the check takes a happy case and empties **every** field in turn except `acts`, demanding
that edge does not change. With the mutation, `status` flips it — and that is enough.

Which is how it should be. The count of edge cases can be satisfied by a flag on twenty-one
happy paths; the origin of the count cannot. The check asserts about the origin.

---

## Exercise 11 · A blind measurement turns into a finding

`stages/s08_eval/online.py`:

```python
# before
    if not any(spot.startswith("термінального") for spot in blind):

# after
    if True:
```

**Red: 1.**

The stage 6 service's trace contains no terminal step for a request. Without the guard every
trajectory gets the finding "the run did not finish" — that is, **a hundred percent of traffic
is marked problematic** because of something the evaluator cannot see.

This is the same mistake as in exercise 1, only mirrored. There, missing data was passed off as
success; here, as failure. Both times the right answer is the third one: there is nothing to
look at, and that has to be said in a word of its own.

---

## Exercise 12 · e2e judges the case description again, not the trace

`stages/s08_eval/levels.py`:

```python
# before
    said = trajectory.answer()

# after
    said = case.answer
```

**Red: 1.**

The most expensive of them all — and the one that lived until the independent review. The judge
starts evaluating what the agent **was supposed to** say instead of what it **said**.

The temptation is obvious: in the happy case both strings are identical, so no number changes.
It becomes visible only on a trace that has no answer at all — there e2e calmly says "passed,
score 3", judging text that never made it into the trace.

And worse: the check "the same answer, different paths" starts comparing **one string with
itself** through one and the same judge. That is an identity that cannot be violated — exactly
the shape AC-01b warns against on the neighbouring level.

What turns red is the check on judge calls: on the two traces with no answer the judge is no
longer called, and the counter diverges.

---

## Exercise 13 · The score parser collects every digit of the line again

`stages/s08_eval/judge.py`:

```python
# before
        number = re.fullmatch(r"(\d{1,2})", said)

# after
        number = re.search(r"(\d{1,2})", "".join(ch for ch in said if ch.isdigit()))
```

**Red: 1.**

The prompt asks for "answer with the number alone" — and a model judge regularly answers
otherwise. The old edition collected **every** digit of the line and took the first two:

```
'8'              -> 8      correct
'8/10'           -> 10     the scale became the score
'оцінка: 3 з 10' -> 10     a three became a ten
'0 з 10'         -> 1      a zero became a one
```

The consequence under `--real`: the e2e level gives everyone top marks, and a stage whose
thesis is "do not trust the instrument" hands over a broken instrument as a working one. An
unparseable answer has to be **unscored**, not a guessed number: the third state exists exactly
for this.

---

## Exercise 14 · Any step with text becomes the last answer

`stages/s08_eval/trajectory.py`:

```python
# before
            if step["kind"] not in SPEAKING:
                continue

# after
            pass
```

**Red: 2.**

The rule of attribution says: "e2e is about the **last answer** and about nothing else". The
`text` field exists not only on the model — a tool result has one too, and so does a service
step. Without the restriction by step kind, the "last answer" becomes the last line of any
origin, and the e2e verdict starts depending on what a tool returned **after** the answer.

On the happy set this is invisible: there only the model's steps carry text. So the check
**builds its own** case in which a tool answers after the model — a property that cannot be
violated with the data at hand requires the check to create the conditions itself.

---

## What to do next

A run of `python scripts/mutate.py s08 --expect` has to end with the line "Усі числа у вправах
збігаються з прогоном". If it does not, it is the **prose** that has drifted, not the code: the
numbers here are not written by hand, they are copied from the run, and the suite's check
asserts it.

What is worth your time after that:

1. **Add a twenty-second case** — one that passes e2e and the trajectory but fails the
   component level. See whether you can find a case in a real agent where this is not a
   labelling error but genuine behaviour.
2. **Set `--real`** with a configured key and run the detectors against a real model. The
   numbers will flicker; think about how many runs it takes to tell bias from noise — and why
   this stage deliberately does not have that answer.
3. **Take the `traces/` of your own run of stages 1–7** and run the demo's eighth scene. The
   list of blind measurements you get is a requirement for tracing formulated by **your** data
   rather than somebody else's.
