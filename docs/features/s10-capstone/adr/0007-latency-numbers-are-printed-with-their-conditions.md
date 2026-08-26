---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
ticket: "n/a"
---

# 0007 — Latency numbers are printed together with their conditions

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The capstone has to give a p50 and a p95. The question is what happens to them next: an operator
will see a number and start planning capacity.

These numbers are obtained on a **fake** model, against a locally started service, on the author's
machine. None of those three facts is visible in the number "p95 = 40 ms".

Stage 7 has already paid for this: there the numbers were right and the conditions were not, and
the lesson had to open with the line "the latencies are fake".

## Decision Drivers

- A number without its conditions is not a measurement.
- The operator has to see the conditions **before** the number.
- A missing instrument must yield neither green nor red.

## Considered Options

**A. Print p50/p95.** A true number, a false impression.

**B. Do not print them at all.** Removes the only evidence about the wrap.

**C. Print them together with the conditions: how many requests, which model, which machine.**

## Decision

**C.** The numbers are always accompanied by their conditions in the same output. A real deployment
stays `NOT EVALUATED` — exactly as trust in a public authority's certificate did at stage 6.

If the load tool is missing, or the service is not up, the state is **not evaluated** with a named
reason.

## Consequences

**Good.** The operator cannot read the number without reading the conditions: they are in the same
paragraph.

**The price.** The output is longer, and there is no single pretty number in it for a slide. That
is the right side of the trade-off.

**The limit.** The conditions describe a run; they do not predict production. The capstone does not
know what a real model would cost, and does not pretend to.
