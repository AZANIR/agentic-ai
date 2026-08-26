---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
ticket: "n/a"
---

# 0003 — An adapter does not decide; whatever decides is a part

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

Nine modules designed independently do not join for free. Stage 2 and stage 6 both have an
`Answer` class, and they are different classes; stage 1 returns a `RunResult`, stage 3 returns
graph state. Every such seam needs code.

The question is not whether to write adapters but **where the boundary lies** between an adapter
and a new part. The boundary has to be hard, because this is exactly where the capstone most
easily turns into a tenth stage inside the tenth: "just a little more logic here", "one small rule
there" — and within an hour the capstone holds behaviour that appears in no lesson and is covered
by no stage's checks.

## Decision Drivers

- New behaviour has to have a lesson, checks and a place in the course.
- The price of assembly has to stay **small** — otherwise the capstone is not assembling, it is
  rewriting.
- The boundary has to be visible to whoever reads the code six months from now.

## Considered Options

**A. No boundary: write whatever is needed in the capstone.** Quietly turns the capstone into a new
stage.

**B. Forbid adapters altogether.** Requires changing the parts — forbidden by C-2.

**C. An adapter joins and nothing more: it translates shape, it takes no decisions.**

## Decision

**C.** An adapter converts a part's result into the shape the service expects, and back. It does
not pick a branch, does not decide what to remember, does not interpret a refusal.

Every adapter **names its seam**: which two parts do not meet, and why. A check asserts this
mechanically.

The sum of the adapters is bounded: ≤ 1/5 of what executed (NFR-7). Above that it is red, and that
is the signal that assembly has turned into rewriting.

## Consequences

**Good.** The price of assembly stays measurable and small. New behaviour, if it is needed, becomes
visible as a gap in the course rather than as a line in the capstone.

**The price.** Some seams look awkward: the adapter translates back and forth where one edit in a
part would have removed the need. That is the deliberate price of the claim "the parts were
mature".

**The limit.** The rule cannot be checked completely: "does not decide" is a property of intent.
The check catches the crude cases — a branch inside an adapter — and relies on the named seam for
the rest.
