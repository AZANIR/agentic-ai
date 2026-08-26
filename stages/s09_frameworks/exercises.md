# Stage 9 exercises — break it and watch what turns red

Before each exercise, run the suite and make sure it is green:

```bash
python -m stages.s09_frameworks.check
```

The numbers are measured, not guessed; the reconciliation is automatic:

```bash
python scripts/mutate.py s09 --expect
```

**Read the names, not the count.** A mutation caught by an incidental check is worse than one
caught by the check that claims it.

**The most important ones are not about frameworks but about the honesty of the comparison** —
exercises 1, 3, 4 and 6. In all four the bench stays operational, the table prints, the numbers
look comparable. That is exactly why they are hard to notice: a broken comparison looks precisely
like an intact one.

**Three exercises — 5, 8 and 9 — are holes the mutation sweep found itself**, before anyone looked
at the code. Two of them were in the checks, one was in the first draft of the exercise itself.

---

## Exercise 1 · The contract stops looking at the path

`stages/s09_frameworks/contract.py`:

```python
# before
    if result.tools_used != TOOLS:

# after
    if False:
```

**Red: 2.**

The contract no longer checks **which** tools were called. The result does not change: the same
answer, the same stop, the same shape.

And that is exactly why it is the most expensive mutation of the stage. An implementation that
called an extra tool and arrived at the same text now passes — and lands in the table with numbers
that look comparable. Comparing against a golden output does not catch this **by construction**:
it looks at the destination, and stage 8 already explained why that is not enough.

---

## Exercise 2 · The contract accepts any stop

`stages/s09_frameworks/contract.py`:

```python
# before
    if result.stopped_by != ANSWERED:

# after
    if result.stopped_by is None:
```

**Red: 1.**

An implementation that exhausted its step budget and stopped without an answer is now considered
to have done the task. The number in the "my lines" column stays — and it now describes an
implementation that does not do the task.

---

## Exercise 3 · The overhead is counted from what the implementation asked for

`stages/s09_frameworks/counters.py`:

```python
# before
            matched = [tokens(owned) for owned in self.owned if owned in part]

# after
            matched = [tokens(part)]
```

**Red: 1.**

Now "what the author asked for" equals "what actually went out" **always**, so the overhead is
zero for everyone. The counter keeps working, the numbers keep printing, the column is in place.

It simply no longer measures anything. And that is impossible to notice by looking at the table: a
zero for the baseline is correct, and a zero for a framework looks like good news.

That is why the check proves the instrument **at both edges**: a purely contractual request gives
zero, foreign text gives a strictly positive number, and exactly by its own size.

---

## Exercise 4 · Invisible lines are located by `origin` alone

`stages/s09_frameworks/counters.py`:

```python
# before
    if locations := list(spec.submodule_search_locations or []):
        return str(Path(locations[0]))
    return str(Path(spec.origin).parent) if spec.origin else ""

# after
    return str(Path(spec.origin).parent) if spec.origin else ""
```

**Red: 1.**

This is not an invented mutation — it is a **real defect of the first draft**, caught by its own
check.

`langgraph` is a namespace package: its `origin` is `None`. Locating it by `origin` alone returns
an empty root, tracing sees no file at all, and the invisible-lines column shows **zero**.

A quiet zero in a column that exists precisely in order not to be zero. The framework would look
free — so the mutation does not merely break the measurement, it breaks it in favour of the
conclusion one would like to reach.

---

## Exercise 5 · "Prose places" stops seeing task descriptions

`stages/s09_frameworks/compare.py`:

```python
# before
    {"role", "goal", "backstory", "description", "instruction", "expected_output"}

# after
    {"role", "goal"}
```

**Red: 1.**

The set no longer counts where the behaviour of the **task** lives — only where the behaviour of
the agent lives. Implicit coordination immediately looks twice as cheap.

**This exercise turned nothing red at first**, and that deserves its own attention. The check
demanded "at least four prose places in CrewAI", and the narrowed set left exactly four: two
agents times two fields. A threshold tuned to the current number lets through exactly the change
it was supposed to guard against.

Now the check asserts the **composition** of the set rather than a number, and proves the
measurement on a synthetic source — where the answer is known in advance.

---

## Exercise 6 · A contract violator quietly disappears from the table

`stages/s09_frameworks/compare.py`:

```python
# before
        if self.broken:
            return [

# after
        if False:
            return [
```

**Red: 1.**

An implementation that broke the contract gets an ordinary row with numbers instead of a reason.
The table looks complete again — and that is exactly the trouble: three honest rows and one
dishonest one are indistinguishable.

Silent inclusion is worse than exclusion. An excluded row is noticeable; an included wrong one is
not.

---

## Exercise 7 · The ADK flag stays silent when the key is missing

`stages/s09_frameworks/via_adk.py`:

```python
# before
    if wanted() and (reason := unavailable_because()):

# after
    if False and (reason := unavailable_because()):
```

**Red: 1.**

The reader explicitly turned on `S09_ADK=1`, there are no credentials, and the harness silently
shows three rows instead of four.

The subtle part is that this looks **right**: "not evaluated" is a legitimate state, and three
rows are perfectly readable. But whoever asked for the fourth will not learn that nothing
happened.

A flag you were asked to turn on and that silently did not fire is worse than no flag at all.

---

## Exercise 8 · The reason for unavailability collapses into one

`stages/s09_frameworks/via_crewai.py`:

```python
# before
    if sys.version_info[:2] > MAX_PYTHON:

# after
    if False:
```

**Red: 1.**

The distinction between "the package is not installed" and "the package cannot be installed on
this interpreter" disappears. A reader on Python 3.14 sees the advice `pip install -e ".[s09]"` —
and follows it, and it does not work, and they never learn why.

**This exercise also turned nothing red at first.** The check accepted any reason ("Python" **or**
"package not installed"), so collapsing two states into one passed straight through. Now it
asserts the **distinction** itself: on an interpreter above the supported one, the reason must
name the version.

---

## Exercise 9 · The baseline disappears from the comparison

`stages/s09_frameworks/run.py`:

```python
# before
    (baseline, "baseline.py", ()),

# after
    (nothing — the line is removed)
```

**Red: 1.**

The table becomes a comparison of three frameworks against each other — that is, it answers "which
of them", while the stage asks something else: "is one needed here at all".

**The first draft of this exercise was empty.** It added `langgraph` tracing to the baseline and
hoped the invisible-lines column would break. It did not: the baseline executes no `langgraph`
code, so there is nothing to count there. A mutation that breaks nothing teaches that the checks
have no teeth — even when they do.

---

## Exercise 10 · The table no longer parses back

`stages/s09_frameworks/compare.py`:

```python
# before
        found[cells[0]] = cells[1:]

# after
        found[cells[0]] = cells[1:-1]
```

**Red: 1.**

Parsing loses the last column. The run's numbers stay correct, the file stays correct — only the
reconciliation between them diverges.

And that is the whole point of a second source: if the check computed the sum twice with the same
code, it would agree here too. An equality computed from a single source is an identity.

---

## What to do next

The run `python scripts/mutate.py s09 --expect` should end with the line saying every number in
the exercises matches the run. If it does not, what diverged is the **prose**, not the code.

Worth your time after that:

1. **Install Python 3.12 and drive the stage there.** CrewAI will install — and that is where the
   real exercise starts: **nobody knows what will be in its row.** The stage's expectation is a
   non-zero token overhead. But it is entirely possible you will see "contract violated" instead of
   numbers: a role framework may call the tool twice or stop differently.

   Both outcomes are outcomes. Write down what happened and compare it with what the lesson
   promised.
2. **Add a fifth implementation** — a bare provider call with no coordination at all. See where it
   lands in the "my lines" column, and whether it adds a new conclusion.
3. **Change the task to one that branches.** Recompute the table. The numbers will change — and
   that is exactly why the choosing rule is stated through columns rather than through framework
   names.
