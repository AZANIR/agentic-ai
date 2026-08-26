---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
ticket: "n/a"
---

# 0002 — The measuring instrument is taken from stage 9, not written again

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The executed lines of a package have to be counted. Such a counter is already written —
`executed_lines` in stage 9, where it measured the price of a framework's scaffolding.

The temptation to write a new one is strong: the capstone measures **stages**, not third-party
packages, and the task feels like a different one.

## Decision Drivers

- Two definitions of the word "executed" would make the numbers of stages 9 and 10 incomparable.
- The stage 9 instrument already has its limits named: this input, this thread, a warm-up before
  the measurement.
- It already has checks of its own, including the one that catches a namespace package with an
  empty `origin`.

## Considered Options

**A. Write a counter of our own.** Duplicates, and diverges on the first small detail.

**B. Move the counter into `shared/`.** Right in form and premature in substance: the second
consumer appeared only just now, and moving it would make it a part with no source stage.

**C. Import it from stage 9.**

## Decision

**C.** The capstone imports `stages.s09_frameworks.counters.executed_lines`. That is the same path
as for every other part, and the same proof: stage 9 gets a non-zero count of executed lines
because its code really does run.

Moving it into `shared/` stays an open question for after the course.

## Consequences

**Good.** One definition of "executed" across two stages. Plus a pleasant side effect: stage 9 is
not decorative in the assembly table — its lines execute during the measurement itself.

**The price.** The capstone depends on stage 9 not only as a part but as an instrument. A change
there changes the numbers here — and that is right: the numbers have a single source.

**The limit.** The instrument's limits are inherited along with it: `sys.settrace` does not see
other threads, and the number describes one input. Both are named in the capstone's lesson, not
only in the lesson of stage 9.
