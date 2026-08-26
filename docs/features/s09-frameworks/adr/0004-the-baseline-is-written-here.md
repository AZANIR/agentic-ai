---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0004 — The baseline is written here, not carried over from stage 3

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The thesis "scaffolding, not architecture" can only be tested against a variant that has no
scaffolding. So a "no framework" row is needed.

The repository already has a mini-graph of its own — stage 3. The temptation to take it is strong:
the code is written, it is checked, and reuse looks thrifty.

But stage 3 is a **supervisor router**: routing by the model's choice, a registry of specialists, a
revision loop with a counter. This stage's task is two sequential steps. Fitting one to the other
means either trimming stage 3's graph (that is, changing a stage, which is forbidden) or inflating
the task into the shape of a router — and then all four implementations would be a router rather
than research → writer.

## Decision Drivers

- The task contract is the same for all four (ADR-0001).
- Stages 1–8 do not change (C-2).
- The size of the baseline is a **conclusion** of the stage, not a detail.

## Considered Options

**A. Carry stage 3's graph over.** Breaks the task contract, or changes stage 3.

**B. Have no baseline.** The table then answers "which framework" rather than "is one needed".

**C. Write a minimal baseline here.** Two steps, explicit state passing, no scaffolding.

## Decision

**C.** The baseline is written in `baseline.py` and is deliberately minimal. Stage 3 remains the
source of the **pattern** — that is where you can see what explicit coordination by hand looks
like — but not a source of code.

## Consequences

**Good.** The task stays one and the same for all four. And the size of the baseline becomes the
table's first number — and its most eloquent one.

**The price.** A little duplicated idea between stages 3 and 9. Duplicating an **idea** is cheaper
than fitting the task to existing code.

**The limit.** The baseline is not production code: it has no retries and no safeguards, and
neither do the other three (C-8). It is honest about the comparison, not about running anything.
