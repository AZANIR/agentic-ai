# Stage 7 — Voice: two numbers instead of one assumption

The lesson itself is in [`README.md`](README.md). This page is the map.

## What it is

Stage 6 built a service that answers. It answers slowly, and nobody minds while the answer is
read with eyes. Voice changes one thing: now a person is **waiting in silence**.

> **You can only optimise what you measured. A number before without a number after is a
> report; a number after without a number before is faith.**

So the pipeline is built twice.

```
batch:      1574 ms   recognition 600 · model 750 · synthesis 224
streaming:   450 ms
ratio:        3.5x
```

Delays are faked to the right order of magnitude. This is evidence about **pipeline
architecture**, not about model speed, and the lesson says so in its first paragraph.

## Run it

```bash
python -m stages.s07_voice.run     # seven scenes, no microphone, no models
python -m stages.s07_voice.check   # 44 checks, 37 of them on failure modes
python scripts/mutate.py s07 --expect
```

## The modules, in reading order

| File | What it holds | Lines |
|---|---|---|
| `clock.py` | the fake clock that does not sleep — why the timing checks never flicker | 26 |
| `measure.py` | one stopwatch, the breakdown, mean and nearest-rank p95 | 62 |
| `model.py` | the fake model; latency is a function of the run index, not state | 30 |
| `pipeline.py` | both pipelines; the difference is visible in the return type | 76 / 110 |
| `bargein.py` | two conditions, neither sufficient alone | 17 |
| `prefetch.py` | milliseconds bought, and work wasted — both in the same type | 24 |
| `ws.py` · `page.html` | live mode: one HTML file, no build; mic only after a click | 62 |
| `real.py` | faster-whisper + piper. Written, never run — see the limits below | 34 |

## The gain splits in two, and conflating them is expensive

| Part | What happens | Reduces total time? | Scales with |
|---|---|---|---|
| **Overlap** | recognition runs while the person is still speaking | yes | utterance length |
| **Earlier delivery** | first chunk goes to synthesis while the model writes the rest | **no** | nothing |

The second part does not make the work faster — 974 ms of answer in both pipelines. It only
starts returning sooner. A check asserts that the difference in totals equals the overlap
exactly, so any extra millisecond would mean streaming quietly did less work.

## The conservation law: whose time was it

A breakdown that does not reconcile is worse than no breakdown — people trust it and optimise
the wrong step. In batch it is simple: the steps sum to the total. Streaming adds a third
party, the **consumer**: between chunks it holds control, pushing a frame into a socket and
waiting on the network. That time passes, but it is not pipeline work.

The first edition did not separate it, so the stopwatch billed the consumer's pause to the
*next* step. A consumer spending a second between chunks produced a breakdown where the model
cost 2750 ms — with a model that slept 750. So the invariant is written in full:

```
sum of steps + handover to consumer = total
```

and the third term, the one attributed to nobody, must be **zero**. The check runs streaming
against a deliberately slow consumer and asserts both halves: that the sum reconciles **and**
that the model's step equals what the model actually slept. Without the second half, the law
would also be satisfied by blaming the model for someone else's delay.

## Why the fake clock matters more than the fake models

A timing check measured against a real clock depends on machine load. It passes nine times and
fails the tenth — and then it gets disabled, taking the stage's only evidence with it.

The fake clock does not sleep: it advances a counter and returns. A run that "takes" a second
and a half executes in microseconds, so asserting twenty identical consecutive runs is free.

Wide tolerances look like the cheaper answer. A tolerance broad enough to survive a loaded
machine no longer distinguishes batch from streaming.

The guard is not a grep for three names but a parse of the **imports**: the pipeline modules
pull in neither `time` nor `datetime` nor `random`. A word list is always incomplete — the
first edition looked for `perf_counter`, and `datetime.now()` walked straight through it.

## p95 is nearest-rank, and nearest-rank is `ceil`

Interpolated percentiles are a latency no run experienced. Nearest rank returns a run someone
genuinely sat through.

Nearest rank is `ceil(0.95·n)`, **not** `round`. The distinction looks pedantic until you see
where it bites: on roughly half of all sample sizes (11–19, 30–39, 51–59 …) rounding lands one
rank low. At thirty runs p95 came out as 400 ms while 6.7 % of runs were worse. The module
that exists to expose the tail was hiding it — and the first check missed it because it stood
at a hundred runs, one of the sizes where `round` and `ceil` agree.

## What this stage does not prove

- **Numbers are faked.** Right order of magnitude, wrong absolute values. Architecture
  evidence, not a benchmark.
- **The VAD is naive.** Two thresholds, no spectral analysis; sustained music will interrupt.
- **Live mode is written but never run.** `real.py` exists and turns on with one flag, but the
  author had neither model weights nor a microphone: AC-07 stays `NOT EVALUATED` on purpose. This
  is the stage's weakest point, and it is named rather than hidden.
- **The page's numbers differ from the demo's** — the utterance is different. What must match
  is the shape of the breakdown, not the values, and the page says so.
- **Prefetch is deliberately read-only.** A discarded call with a side effect would turn the
  optimisation into a trap.
- **Voice is not stitched into stage 6's service.** Separate module; stitching belongs to
  stage 10.

## Where to break it

Sixteen mutations. The ones worth your time are not about audio but about **measurement**: the
fake clock starts really sleeping, the stopwatch stops adding up, the consumer's time gets
billed to the model, p95 rounds instead of ranking, and first-audio can be marked twice. All
of them leave the code working and the numbers plausible.

Walkthrough in [`exercises.md`](exercises.md).
