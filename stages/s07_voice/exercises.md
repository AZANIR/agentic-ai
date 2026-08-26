# Stage 7 exercises — break it and watch what turns red

Before every exercise, run the suite and make sure it is green:

```bash
python -m stages.s07_voice.check
```

The numbers are measured, not guessed; the reconciliation is automatic:

```bash
python scripts/mutate.py s07 --expect
```

**Read the names, not the count.** A mutation caught by an incidental check is worse than one
caught by the check that asserts about it.

**The most important ones are not about sound but about measurement** — exercises 1, 2, 3, 13
and 14. All of them leave the code working and give numbers that look plausible.

---

## Exercise 1 · The fake clock starts really sleeping

`stages/s07_voice/clock.py`:

```python
# before
        self.waits.append(millis)
        self._now += millis

# after
        import time as _t

        self.waits.append(millis)
        _t.sleep(millis / 100000.0)
        self._now += millis
```

**Red: 1.**

The fake clock starts really sleeping — only a little, a hundred times less than declared. The
numbers stay **correct**; the only thing that changes is that a run now costs real time.

At twenty runs this is still invisible. At two hundred the check starts taking seconds, and
somebody will reduce the number of runs. Then the flicker comes back, and it gets disabled.

What turns red is the check that measures the **real** duration of the fake sleep.

---

## Exercise 2 · First audio can be marked twice

`stages/s07_voice/measure.py`:

```python
# before
        if self.timing.first_audio is not None:

# after
        if False:
```

**Red: 1.**

The guard disappears, and first audio can be marked twice. The second marking overwrites the
first, so the stage's headline number becomes the time of the **second** chunk.

The nastiest part is that the number stays plausible: it is larger than the real one but
smaller than the batch one. The chart looks fine.

---

## Exercise 3 · The stopwatch's steps start overlapping

`stages/s07_voice/measure.py`:

```python
# before
        cost = now - self._mark
        self._mark = now

# after
        cost = now - self._started
```

**Red: 4.**

The stopwatch's steps start overlapping: each is measured from the start of the run rather than
from the end of the previous one.

The sum of the steps becomes larger than the total time — the breakdown stops reconciling. This
is the most common way to get numbers that cannot be added up, and it is exactly why there is
one stopwatch.

**Live mode** turns red too: the check that raises a socket and holds a conversation verifies
the same conservation law on numbers that arrived over the network. One defect caught by two
different routes is not double counting but two independent witnesses.

---

## Exercise 4 · Recognition stops overlapping with speech

`stages/s07_voice/stt.py`:

```python
# before
        cost = FINALISE_MILLIS if self.incremental else self.millis_per_second * seconds

# after
        cost = self.millis_per_second * seconds
```

**Red: 2.**

Recognition in streaming stops overlapping with speech and again costs full price.

The ratio falls from 3.5x to 1.7x — that is, the promise of "at least twice" breaks. In the
check's message that number has two decimals: 1.69. The mutation shows **where most of the
gain actually comes from**: not from the chunks, but from the work moving into the time when
the person was still speaking.

---

## Exercise 5 · Streaming collects every chunk before the first sound

`stages/s07_voice/pipeline.py`:

```python
# before
        for index, chunk in enumerate(think_chunks(heard.text, clock=clock)):

# after
        for index, chunk in enumerate(list(think_chunks(heard.text, clock=clock))):
```

**Red: 1.**

One `list()` call — and streaming stops being streaming while remaining streaming by the
structure of the code. The chunks are collected in full before the first one goes to synthesis.

This is the most frequent mistake in real code: `list()` gets added so it is "easier to look
at", and the optimisation disappears silently. The breakdown stays correct, the steps are in
place, the sum reconciles. The only thing that breaks is the thing everything was built for.

**The previous edition of this exercise did not compile.** It substituted `CHUNKS_SENTINEL`,
which does not exist in the code, and every red one was a `NameError` — not a single assertion
was reached. The lesson here is not about streaming: **after a mutation, read the reason for
the failure, not only the fact of it**.

---

## Exercise 6 · Barge-in looks only at the level

`stages/s07_voice/bargein.py`:

```python
# before
    if sound.millis < min_millis:

# after
    if False:
```

**Red: 3.**

The duration condition disappears, and the detector looks only at the level.

It still "works": loud speech interrupts, silence does not. What breaks is exactly what the
second condition exists for: mouse clicks and coughs now cut off the answer.

---

## Exercise 7 · Barge-in looks only at the duration

`stages/s07_voice/bargein.py`:

```python
# before
    if sound.level < level:

# after
    if False:
```

**Red: 2.**

The mirror image of the previous one: the level condition disappears, the duration stays.

Now the answer gets interrupted by the air conditioner, the fan and any sustained background
noise. Together the two exercises show why there are four checks and not one.

---

## Exercise 8 · P95 is interpolated instead of taking a real run

`stages/s07_voice/measure.py`:

```python
# before
        p95=ordered[rank],

# after
        p95=sum(ordered) / len(ordered) * 1.5,
```

**Red: 2.**

p95 starts being computed by a formula instead of being a real run.

The number looks plausible — it is even larger than the mean. But no run experienced that
latency, and showing it to the user means reporting an event that did not happen.

---

## Exercise 9 · A distribution from zero runs gives zeros

`stages/s07_voice/measure.py`:

```python
# before
    if not values:
        raise ValueError("розподіл із нуля прогонів не існує")

# after
    if not values:
        return Distribution(runs=0, mean=0.0, p95=0.0, worst=0.0)
```

**Red: 1.**

A distribution from zero runs stops being an error and starts returning zeros.

A silent zero in a report looks like a very fast service. In reality it is the absence of a
number — and the difference between "fast" and "not measured" is expensive here.

---

## Exercise 10 · Silence goes into the model

`stages/s07_voice/pipeline.py`:

```python
# before
    if heard.silent:
        return _silence(watch, tracer)

# after
    if False:
        return _silence(watch, tracer)
```

**Red: 1.**

Empty recognition no longer stops the pipeline, and silence goes into the model.

Every cough into the microphone costs tokens and a second and a half. The proof in the check is
not the names of the steps but the **cost**: the fake model sleeps 750 ms, and the clock shows
it.

---

## Exercise 11 · Prefetch stops naming the wasted work

`stages/s07_voice/prefetch.py`:

```python
# before
    outcome.note = f"{WASTED}: інструмент викликано, результат відкинуто"

# after
    outcome.note = ""
```

**Red: 2.**

Prefetch stops naming the wasted work: the note becomes empty.

The gain stays, the price disappears from view. A stage that shows only the first number is
campaigning for prefetch instead of explaining it — and the reader turns the optimisation on
where the tool is needed by one request in ten.

---

## Exercise 12 · Prefetch waits out both delays instead of overlapping them

`stages/s07_voice/prefetch.py`:

```python
# before
        clock.sleep(max(tool_millis, think_millis))

# after
        clock.sleep(tool_millis + think_millis)
```

**Red: 2.**

Prefetch starts waiting out both delays in sequence instead of overlapping them.

It still "works": the call happens earlier, the code looks the same. There simply is no gain
any more — complexity added for nothing.

---

## Exercise 13 · The consumer's time is billed to the next step

`stages/s07_voice/measure.py`:

```python
# before
        gap = now - self._mark
        self._mark = now
        self.timing.handover += gap

# after
        gap = now - self._mark
        self.timing.handover += gap
```

**Red: 1.**

The stopwatch stops moving the mark after a chunk is delivered. The time during which control
belonged to the consumer is no longer closed off separately — it lands in the **next** step.

This is the same defect the lesson describes in part 4, and it is the quietest of them all: the
breakdown stays consistent on a fast consumer and falls apart only on a slow one. A model that
slept 750 ms shows 2750 — and the most expensive step becomes the one the browser thought after
the longest.

The conservation law turns red, and specifically its **second** half: the sum may still
reconcile while the model's step is already lying.

---

## Exercise 14 · P95 is rounded instead of taking the nearest rank

`stages/s07_voice/measure.py`:

```python
# before
    rank = max(0, min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1))

# after
    rank = max(0, min(len(ordered) - 1, int(round(0.95 * len(ordered))) - 1))
```

**Red: 1.**

Nearest rank is replaced by rounding — one word, and it looks equivalent.

At a hundred runs there is no difference: `round(95)` and `ceil(95)` give the same thing. The
difference appears on roughly half of all sample sizes — 11–19, 30–39, 51–59 — where the rank
drops one lower. At thirty runs p95 comes out as 400 ms while 6.7 % of runs are worse, and
`tail_ratio` becomes less than one: "there is no tail".

The first edition of the check did not see this, because it stood at exactly a hundred runs.
The lesson: **a check on boundary arithmetic has to run several input sizes**, otherwise it is
checking one lucky point.

---

## Exercise 15 · Discarded prefetch waits for the tool anyway

`stages/s07_voice/prefetch.py`:

```python
# before
    clock.sleep(think_millis)
    outcome = Outcome(millis=clock.now() - start, used=False)

# after
    clock.sleep(max(tool_millis, think_millis))
    outcome = Outcome(millis=clock.now() - start, used=False)
```

**Red: 1.**

Discarded prefetch waits for the tool again — the tool that is declared wasted work one line
below.

With a slow tool the answer is delayed by its full price, for the sake of a result that gets
thrown away. That is not an optimisation but an optimisation in reverse, and it is only visible
when the tool is **slower** than the thinking. The first edition took 500 against 600
everywhere, so this case never occurred anywhere.

---

## Exercise 16 · Chunks can be traversed twice

`stages/s07_voice/pipeline.py`:

```python
# before
        if self._walked:

# after
        if False:
```

**Red: 1.**

Chunks can be traversed twice again. The second pass does not fail and is not empty — it
continues from the middle.

`next(chunks)` and then `list(chunks)` gives back the tail of the answer, which looks like the
whole answer. A silent half is worse than an error: an error is visible.

---

## What to do next

Try **your own** mutation: break something and see whether anyone notices. If the suite stayed
green, you have found a hole in the checks, and that is worth more than any of the sixteen
above.

And separately — move the **thresholds** around:

```bash
python -c "from stages.s07_voice.bargein import *; print(should_interrupt(Sound(0.4, 250)))"
```

Find the pair of numbers where your own "uh-huh" in the middle of an answer does not interrupt
it but "stop" does. That is the real work with VAD, and it does not automate.
