---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0005 — Cases are generated from scenarios, not left lying around as fixtures

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The evaluator needs trajectories. Twenty of them, with edge cases. Stage 1 gives four scenarios —
too few, and they do not cover what has to be shown (an interrupted run, an endless loop, a call
to a tool that does not exist).

The obvious answer is to write twenty traces into a file and read them back. The obvious flaw:
the trace format lives in `shared/trace.py` and will change one day. Recorded files survive that
change silently, and the stage goes on evaluating a format that no longer exists.

## Decision drivers

- NFR-6: twenty runs produce the same report. Generation has to be deterministic.
- AC-02: evaluation requires no changes in stages 1–7 — so the cases cannot be taken from "a
  stage 1 run that we tweak a little".
- Edge cases have to be **described**, not drawn by hand in JSON: a description gets read, JSON
  does not.

## Considered options

**A. Fixtures in files.** They rot silently when the format changes; nobody re-reads twenty
blocks of JSON.

**B. Record traces from real stage 1 runs.** Ties stage 8 to stage 1's scenarios and yields none
of the edge cases that are not there.

**C. A declarative scenario → a generated trace through `shared.trace`.**

## Decision

**C.** A case describes **what the agent did**: which steps, in what order, with which tools. The
generator runs that description through the same `shared.trace` every stage uses, into a
temporary file. The trace is real — in the real format, with the same fields.

Whether a case is an edge case is **a field of the description**, not the reader's opinion.
NFR-7 counts it.

## Consequences

**Good.** A change to the trace format breaks generation **loudly**, together with every stage,
rather than silently in one stage. Twenty cases read as twenty sentences, not as twenty blocks
of JSON.

**The price.** The generator is code, and code can be wrong too. Against that — AC-11: the same
evaluator runs over the real traces of stages 1 and 6, so if the generated traces diverged from
the real ones, it would show.

**The limit.** Generated trajectories are what the author **was able to think up**. Real traffic
brings something else, and that is exactly why the stage's online part is not decoration.
