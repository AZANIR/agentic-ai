---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0008 — The stage writes a run key from its first line

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

Stage 8 measured what an evaluator is missing in the existing traces, and the answer turned out to
be a single thing: **the run key**. Three different fields across seven stages (`scenario`, `scene`,
`trace_ref`), and four stages that mark the run in no way at all. On traces like that the evaluator
sees one long trajectory instead of several short ones and cannot attribute a verdict to a scene.

Fixing the existing stages is deferred to stage 10: the edit would touch all seven and would break
stage 8's constraint.

But this stage is written **after** the measurement, and from scratch. The question is not whether to
fix the old, but whether to use one's own conclusion.

## Decision Drivers

- The requirement is already stated and already measured — there is no need to justify it again.
- The price here is zero: the field is added while writing, not while rewriting.
- A measurement nobody used was not needed.

## Considered Options

**A. Write like stages 1–7 — with no key.** Consistent with the past, and pointless after the
measurement.

**B. Wait for stage 10, where the key will be introduced centrally.** Defers something that is free.

**C. Write the key from the first line.**

## Decision

**C.** Every step of this stage's trace carries a `case` field — which implementation was run, and on
which input. The stage 8 evaluator, pointed at the stage 9 trace, extracts **more than one**
trajectory with no edit to itself.

The field name is taken from the list `trajectory.RUN_KEYS` already knows, so that stage 8's
measurement sees it automatically rather than after one more synonym is added.

## Consequences

**Good.** Stage 8's requirement is confirmed by use, not by text alone. The stage 9 check asserts it
by execution: the neighbouring stage's evaluator reads the trace and yields more than one
trajectory.

**The price.** One field in every step. That is the whole price, and it is exactly why four stages
without a key are not a hard problem but an unasked question.

**The limit.** This does not fix stages 1–7. It only stops adding an eighth case to the four that
exist — and gives stage 10 an example rather than one more task.
