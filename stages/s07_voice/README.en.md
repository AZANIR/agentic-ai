# Stage 7 — Voice: two numbers instead of one assumption

The lesson itself is in Ukrainian ([`README.md`](README.md)). This page is the map.

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
python -m stages.s07_voice.run     # six scenes, no microphone, no models
python -m stages.s07_voice.check   # 33 checks, 25 of them on failure modes
python scripts/mutate.py s07 --expect
```

## The modules, in reading order

| File | What it holds | Lines |
|---|---|---|
| `clock.py` | the fake clock that does not sleep — why the timing checks never flicker | 26 |
| `measure.py` | one stopwatch, the breakdown, mean and p95 | 46 |
| `pipeline.py` | both pipelines; the difference is visible in the return type | 48 / 110 |
| `bargein.py` | two conditions, neither sufficient alone | 17 |
| `prefetch.py` | milliseconds bought, and work wasted | 19 |
| `ws.py` · `page.html` | live mode: one HTML file, no build; mic only after a click | 34 |

## The gain splits in two, and conflating them is expensive

| Part | What happens | Reduces total time? | Scales with |
|---|---|---|---|
| **Overlap** | recognition runs while the person is still speaking | yes | utterance length |
| **Earlier delivery** | first chunk goes to synthesis while the model writes the rest | **no** | nothing |

The second part does not make the work faster — 974 ms of answer in both pipelines. It only
starts returning sooner. A check asserts that the difference in totals equals the overlap
exactly, so any extra millisecond would mean streaming quietly did less work.

## Why the fake clock matters more than the fake models

A timing check measured against a real clock depends on machine load. It passes nine times and
fails the tenth — and then it gets disabled, taking the stage's only evidence with it.

The fake clock does not sleep: it advances a counter and returns. A run that "takes" a second
and a half executes in microseconds, so asserting twenty identical consecutive runs is free.

Wide tolerances look like the cheaper answer. A tolerance broad enough to survive a loaded
machine no longer distinguishes batch from streaming.

## What this stage does not prove

- **Numbers are faked.** Right order of magnitude, wrong absolute values. Architecture
  evidence, not a benchmark.
- **The VAD is naive.** Two thresholds, no spectral analysis; sustained music will interrupt.
- **Live mode was not verified against a real microphone.** AC-07 stays not-verified.
- **Prefetch is deliberately read-only.** A discarded call with a side effect would turn the
  optimisation into a trap.
- **Voice is not stitched into stage 6's service.** Separate module; stitching belongs to
  stage 10.

## Where to break it

Twelve mutations. The three worth your time are not about audio but about **measurement**: the
fake clock starts really sleeping, the stopwatch stops adding up, and first-audio can be marked
twice. All three leave the code working and the numbers plausible.

Walkthrough in [`exercises.md`](exercises.md), written in Ukrainian.
