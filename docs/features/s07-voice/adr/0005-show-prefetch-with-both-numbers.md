---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0005 — Prefetch is shown with both numbers — what it buys and what it wastes

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

A slow tool costs a lot in voice: the person waits in silence. The obvious answer is to call it
**earlier**, while the model is still formulating the answer.

Just as obviously, this is where an article about prefetch would end — on the word "faster".

Prefetch performs a call that **may turn out not to be needed**. That is not free: it is a
request into someone else's system, a place in a queue, sometimes money.

## Decision drivers

- The course already has a rule: every speed-up is measured first.
- Showing only the gain means campaigning, not teaching.
- The share of requests that do not need the tool is the decision's main number, and it depends
  on the domain, not on the code.

## Considered options

1. **Both numbers: how much it buys and how much wasted work it creates.**
2. **Show only the gain.**
3. **No prefetch at all** — too complicated for a lesson.

## Decision outcome

**Chosen:** Option 1.

Option 2 is the commonest form of technical article and the worst: it hands the reader an
optimisation without the conditions for applying it.

Option 3 throws away the most interesting thing in a voice pipeline: here a tool's latency is
visible to the ear, not on a chart.

**AC-06b is not an appendix but half of the decision.** A request that does not need the tool has
to show the discarded result and name it **wasted work** in the trace. Without that criterion the
stage sells prefetch instead of explaining it.

## Consequences

**Positive**
- The reader gets both numbers and decides for themselves.
- Wasted work is named in the trace, so it can be counted on real traffic.
- Prefetch stays a single tool: one is enough to show the price.

**Negative**
- The pipeline gets more complicated: a result appears that may be discarded.
- A discarded call in a real system can have a side effect. Here the tool is deliberately
  read-only, and that is named — otherwise prefetch would turn into a trap.
