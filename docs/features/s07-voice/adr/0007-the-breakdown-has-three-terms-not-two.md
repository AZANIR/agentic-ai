# 0007 · The breakdown has three terms, not two

- Status: Accepted
- Date: 2026-08-25
- Context: stage 7 (voice), AC-01, AC-01b

## Context

The stage's main invariant used to read: **the sum of the steps equals the total time**. In the
batch pipeline that is true and is proved in one line.

In the streaming one it is not, and the reason is not an implementation bug but that there are
now three participants. Between a `yield` and the next step, control belongs to the **consumer**:
the socket writes a frame into the network, the page draws a line, the test counts. That time
passes on the same clock, but it is not the pipeline's work.

A stopwatch that measures every step "from the previous mark" billed the consumer's pause to the
**next** step. Measured: a consumer that spends a second between chunks got a breakdown where the
"model reply" step costs 2750 ms — with a model that slept 750. The sum reconciled with the total
time perfectly, so the invariant was green and the breakdown lied.

The most expensive step became whichever one the browser thought after the longest.

## Decision

The invariant is written with three terms:

    sum of steps + handover to the consumer + unattributed = total time

The third term has to be **zero**. `Timing.handover` accumulates through explicit
`watch.handover()` calls at the points where the pipeline has delivered a chunk and is waiting;
`Timing.unaccounted()` counts the remainder.

`total` is NOT computed as the sum of the parts. A computed total would make the conservation law
a tautology and would stop catching a step somebody forgot to measure — that is, exactly what the
law exists for. It is taken from the clock independently.

## Consequences

**Good.** The breakdown reconciles on any consumer, not only on a fast one. The model's step
equals how long the model actually worked — that can be reconciled against the trace. The check
runs a deliberately slow consumer, so the defect is caught where it lives.

**The price.** The pipeline gained a call that is easy to forget to add at a new delivery point.
The guard is the invariant itself: a forgotten `handover()` gives a non-zero third term and a red
check, not a quiet shift in the number. Mutation 13 pins this down.

**What this would have cost without the decision.** A breakdown that does not reconcile is worse
than no breakdown: it gets believed. A breakdown that reconciles wrongly is twice as bad — on top
of that, it cannot even be suspected.

## Alternatives considered

**Keep two terms and measure only fast consumers.** The defect is invisible exactly until
somebody plugs in a real network. That is, until production.

**Exclude the consumer's time by stopping the clock on `yield`.** Then `total` stops being the
run's real time, and the number "how long this took for the person" disappears — and that number
is the stage's thesis.

**Compute `total` as the sum.** The conservation law becomes an identity: `sum == sum`. The check
stays green forever, including in the case where somebody forgot to measure a step.
