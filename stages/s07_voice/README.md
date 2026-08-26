# Stage 7 — Voice: two numbers instead of one assumption

Stage 6 delivered a service that answers. It answers **slowly** — and nobody minds while the
answer is read with eyes.

Voice changes one thing: now the person on the other end is **waiting in silence**.

## What you will be able to do after this stage

- Get two numbers from the same data with one command and explain the difference between them
- Say why the measurement is time to the **first sound** rather than total duration
- Show on your own numbers why p95 matters more than the mean — and why it is taken by rank
- Reproduce barge-in and name the **two** conditions that decide it
- Name the price of prefetch, not only its gain
- Reconcile the breakdown against the trace and see why one number needs two mechanisms

## Run this before reading

```bash
python -m stages.s07_voice.run     # seven scenes, no microphone and no models
python -m stages.s07_voice.check   # 44 checks
```

Watch the **third** scene. The first two give two numbers; the third explains why they differ,
and it is the one that separates a result from the well-known phrase "streaming is faster".

## Part 1. Why time to the first sound

In text, latency is an inconvenience. In voice, latency is a **pause in the conversation**, and
a person reads a pause as "they did not hear me" or "it is broken".

So what gets measured is not the total time but the moment the other person understands they
were heard:

```
batch:      1574 ms   recognition 600 · model 750 · synthesis 224
streaming:   450 ms
ratio:        3.5x
```

**The numbers are faked to the order of magnitude of real ones.** This is evidence about
**pipeline architecture**, not about how fast models are, and the lesson says so in its first
line rather than in a footnote.

## Part 2. The most important sentence of the whole stage

> **You can only optimise what you have measured. A number before without a number after is a
> report; a number after without a number before is faith.**

That is why the pipeline is built **twice**. The batch one is written in an hour, works, and
gives the baseline. A reader who saw 1574 ms and then 450 ms understands the **price** of
streaming's complexity. A reader handed streaming straight away takes it for the norm and has
no idea what it costs.

## Part 3. Streaming's gain is two different things

The most important part of the stage, and the easiest to confuse:

| Part | What happens | Reduces total time? | Scales with |
|---|---|---|---|
| **Overlap** | recognition runs **while the person is speaking** | yes | utterance length |
| **Earlier delivery** | the first chunk goes to synthesis while the model writes the rest | **no** | nothing |

The second part does not make the work faster. The model writes just as much, synthesis voices
just as much — 974 ms in both pipelines. Only the **moment of first delivery** changes.

Conflating them is expensive. The first gives more the longer the person speaks; the second
gives a fixed gain and does not depend on the utterance at all.

The check asserts this literally: the difference in totals must **equal** the overlap. Any
extra millisecond would mean streaming quietly did less work.

## Part 4. The conservation law: whose time was it

A breakdown that does not reconcile is worse than no breakdown: it gets believed, and the wrong
step gets optimised.

In batch this is simple — the steps sum to the total. Streaming adds a third participant: the
**consumer**. Between chunks control belongs to it — it pushes a frame into a socket, draws a
line, waits on the network. That time passes, but it is not the pipeline's work.

The first edition did not separate it, and the stopwatch billed the consumer's pause to the
**next** step. A consumer that spent a second between chunks got a breakdown where the model
cost 2750 ms — with a model that slept 750. The most expensive step became whichever one the
browser happened to think after.

So the stage's invariant is written in full:

```
sum of steps + handover to the consumer = total time
```

and the third term — the one attributed to nobody — must be **zero**. A non-zero one means
something was measured past the mark. The check runs streaming against a deliberately slow
consumer and asserts both halves: that the sum reconciles **and** that the model's step equals
what the model actually slept. Without the second half the conservation law would also be
satisfied when the model is blamed for someone else's delay.

## Part 5. Reading the code — six files

### `clock.py` — why this stage's checks never flicker

The clock is passed as a parameter and is read from the system **nowhere**. Stage 5 decided the
same thing for the sake of TTL determinism; here the reason is stronger:

> A check that measures time with a real clock depends on the machine's load. It passes nine
> times and fails the tenth — and then it gets **disabled**, and with it disappears the only
> evidence for the stage's main thesis.

**The fake clock does not sleep.** `sleep(200)` moves a counter and returns control
immediately. A run that "takes a second and a half" executes in microseconds, so the
requirement "twenty consecutive runs give the same number" costs nothing.

The alternative — a real clock and wide tolerances — looks simpler and hides its price: a
tolerance broad enough not to flicker on a loaded machine **no longer distinguishes** batch
from streaming.

The guard is not a grep for three names but a parse of the **imports**: the pipeline module
pulls in neither `time` nor `datetime` nor `random`. A word list is always incomplete — the
first edition looked for `perf_counter`, and `datetime.now()` walked straight through it
unnoticed.

### `measure.py` — a stopwatch, not measurements scattered around

One stopwatch that knows about steps. Scattered `perf_counter()` calls give numbers that cannot
be added up: something was measured twice, something not measured at all, and the sum does not
match the total.

**p95 is taken by nearest rank, without interpolation.** An interpolated number is a latency
that no run experienced. Showing the user an invented figure instead of the worst real one is a
strange form of honesty.

Nearest rank is `ceil(0.95·n)`, and **not** `round`. The difference looks pedantic until you
look at where it shows up: on roughly half of all sample sizes (11–19, 30–39, 51–59 …) rounding
gives a rank one lower. At thirty runs p95 came out as 400 ms while 6.7 % of runs were worse.
The module that exists precisely to expose the tail was hiding it — and the first check did not
see this, because it stood at a hundred runs, that is, at a lucky number where `round` and
`ceil` agree.

**`None`, not zero.** Twice: first audio and total time. Zero is a plausible number, so a
breakdown read in the middle of streaming showed "total 0 ms" next to a non-empty list of
steps, and an empty model reply gave "to first audio: 0 ms" — the best possible latency for a
run that had no audio in it at all.

### `model.py` — where the spread comes from

There is one fake model for the whole stage, and the latency in it is a **function of the run
index**, not state. That is needed for the distribution: a hundred runs have to give a hundred
different numbers, otherwise there is nothing to show p95 on.

The clock gives no spread by construction — and that is its chief virtue. So the spread comes
from the model: every tenth run is four times slower, every fiftieth eight times. A hundred runs
give a mean of 1859 ms, p95 of 3824 ms and a worst of 6824 ms, and a repeat run gives the same
hundred numbers.

A single tier of tail would give a p95 equal to the worst — and the difference between "almost
the worst" and "the worst" would disappear exactly where the stage is showing it.

### `pipeline.py` — the difference is visible in the type

```python
batch(...)     -> Reply     a finished answer
streaming(...) -> Stream    chunks
```

The asymmetry is deliberate. A function that returns a finished result **has no way** to hand
back half of it; a function that returns an iterator has no way to hide that it delivers in
parts. A difference visible in the signature needs no comment — and cannot drift from the code.

**Chunks are traversed once.** A bare generator hands back the tail after a partial pass:
`next(chunks)` and then `list(chunks)` gives not the whole answer but its second half —
silently. Half an answer that looks like the whole one is worse than an error, so the second
pass is a refusal.

**Silence is not a request.** Empty recognition stops the pipeline **before** the model call:
otherwise every cough into the microphone costs tokens and a second and a half. Silence from
the **model** is a different failure mode, and it too is named separately.

### `bargein.py` — two conditions, and neither is enough alone

    level       is this voice at all, rather than background
    duration    is this a word, rather than a click

A detector that goes by level alone interrupts on a cough and on keystrokes. By duration alone
— on the air conditioner. So there are **four** checks: noise does not interrupt, short does not
interrupt, long does interrupt — and the fourth moves both thresholds, proving that each of them
really does affect the decision. Without it both numbers could be decorative.

**0.35 and 200 ms are the exercise's bounds, not production settings.** The real threshold
depends on the microphone, the room and the language, and it is tuned by ear.

### `prefetch.py` — both numbers, not one

A slow tool costs a lot in voice: the person waits in silence. The obvious answer is to call it
earlier.

Just as obviously, an article that ends on the word "faster" hands the reader an optimisation
**without the conditions for applying it**. Prefetch performs a call that may turn out not to be
needed: that is a request into someone else's system, a place in a queue, sometimes money.

So the gain and the price live in **one type**: `millis` and `wasted_millis`. The first edition
kept them apart — the synchronous path did not sleep the thinking time at all — and a reader
comparing two `.millis` head-on would have seen that prefetch is 250 ms **slower**. The correct
number existed only in the demo, which added the thinking from outside by hand.

And separately: the discarded result is **not waited for**. A latency paid for a thing that is
declared wasted work one line below is not an optimisation.

## Part 6. The trace — the same number by another route

The pipeline's steps are written into `shared.trace`, as on every stage since the first. This is
not duplicating the breakdown: the breakdown lives in the run's memory, the trace on disk, and
the mechanisms are independent.

That is exactly why one can be **reconciled** against the other. A number that matched in both
would have had to be wrong twice in the same way — and that is no longer chance. The demo's
seventh scene prints the reconciliation, and the check asserts the same thing: time to first
audio in the trace equals the number from the breakdown, and the sum of the model's steps in the
trace equals the model's step in the breakdown.

The trace carries **numbers and reasons**, not content: the text of the answer is not in it, and
that is checked too. Stage 8 will read it.

## Part 7. What to break

```bash
python scripts/mutate.py s07          # all sixteen mutations
python scripts/mutate.py s07 --expect # and reconcile against the promised numbers
```

**The most interesting ones are not about sound but about measurement.** The fake clock starts
really sleeping; the stopwatch stops adding up steps; the consumer's time is billed to the
model; p95 gets rounded; first audio can be marked twice. All of them leave the code working and
give numbers that look plausible — which is exactly why they are hard to spot without a check.

The walkthrough is in [`exercises.md`](exercises.md).

## The limits of this stage — so you do not carry them into production

- **The numbers are faked.** The order of magnitude is real, the absolute values are not. This
  is evidence about architecture, not a benchmark.
- **The VAD is naive.** Two thresholds with no spectral analysis; sustained music will interrupt
  the answer.
- **One voice, one language.** Multilingual support and voice selection are configuration, not a
  lesson.
- **Live mode is written but never run.** `real.py` exists and turns on with one flag, but the
  author had neither model weights nor a microphone: AC-07 stays `NOT EVALUATED` on purpose.
  This is the stage's weakest point, and it is named rather than hidden.
- **The numbers on the page and the numbers in the run differ** — because the utterance is
  different. What has to match is the shape of the breakdown, not the values; the page says so
  directly.
- **Prefetch has one tool**, deliberately read-only. A discarded call that changed state would
  turn the optimisation into a trap.
- **Voice is not stitched into stage 6's service.** A separate module; stitching makes sense at
  stage 10.

## The numbers

**44 checks, 37 of them on failure modes.** Modules: `pipeline.py` — 76 of 110 allowed lines.
The demo run takes microseconds of real time, despite the "second and a half" in its output.

## Next

Stage 8 — **evaluation**: stopping saying "seems to work". A harness on three levels over the
traces, a deterministic check and a model judge, plus position and length bias — shown live on
the stage's own data.
