# Checklist: what to measure in a voice pipeline

Not "which metrics to collect". Every item here answers a question somebody will ask after the
first complaint that "it lags".

## 1. Time to the first sound — not the total

**The question:** how many milliseconds after the pause does the person understand they were
heard?

Total duration describes the system's work. Time to the first sound describes the **pause in
the conversation**, and that is what a person calls lagging.

An optimisation that reduces total time and leaves the first sound alone is not felt in voice
at all.

## 2. A breakdown by step — not one number

**The question:** which step is the most expensive?

One number says that things are bad. A breakdown says **where** they are bad. Without it,
people optimise the most visible step instead of the most expensive one — and visibility and
cost rarely coincide.

And separately: **the breakdown has to reconcile in full**. Not "the sum of the steps equals
the total" — that is only true where the pipeline owns the time on its own. The moment a
consumer appears that takes the chunks at its own pace, the invariant is written with three
terms:

```
sum of steps + handover to the consumer + attributed to nobody = total time
```

and the third has to be zero. The short form is not merely incomplete — it **silently bills
somebody else's time to your step**: a consumer that thinks for a second between chunks makes
the most expensive step the one it happened to think after. The sum still reconciles, and the
breakdown looks flawless.

A breakdown that does not reconcile is worse than no breakdown, because it gets believed. A
breakdown that reconciles wrongly is twice as bad.

## 3. p95 — not the mean

**The question:** what does that twentieth user feel?

The mean is a number for a report. If every twentieth run is four times slower, the mean will
barely notice, and the person will notice immediately and leave.

**And p95 has to be a real run**, not an interpolation: showing a latency nobody experienced is
a strange form of honesty.

## 4. Both halves of the gain — separately

**The question:** what exactly got faster?

"Overlap" and "earlier delivery" are different things with different behaviour. The first
scales with utterance length, the second gives a fixed gain. Mix them and you get a forecast
that will not hold on longer utterances.

## 5. The price of the optimisation — next to its gain

**The question:** how many times did we do work that turned out not to be needed?

Prefetch, cache, speculative call — all three buy time with wasted work. The number for the
wasted work has to be **in the trace**, otherwise it cannot be counted on real traffic.

## 6. Flicker in the measurement — separately from the system's quality

**The question:** does the same input give the same number?

A timing check that fails one run in ten will be disabled. Not "might be" — it **will be**, and
quickly. So the time source has to be substitutable, and determinism has to be checked
separately.

## 7. What happens on silence

**The question:** how much does a cough into the microphone cost?

Empty recognition that goes on into the model is tokens and seconds for zero benefit. Silence
has to stop the pipeline **before** the expensive step, not after it.

## What this checklist deliberately leaves out

**Recognition quality.** It is measured differently (WER on a labelled set) and belongs to a
different discipline. Confusing speed with accuracy is the cheapest way to optimise the wrong
thing.

**Answer quality.** That is stage 8, and it measures it on traces rather than in the hot path.

**Load.** How many simultaneous conversations the service withstands is a stage 10 question,
and it only makes sense once the latency of one is known.
