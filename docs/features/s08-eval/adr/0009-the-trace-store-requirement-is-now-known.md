---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0009 — The trace store requirement: stated, and JSONL satisfies it

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The second promise that lands here. Stage 6's `adr/0008`:

> "Evaluation (stage 8) will read the traces and **state a requirement** for the store. Right now
> there is no such requirement — there is a guess… A promise in the code must either be kept or
> moved with the name of the new stage. Leaving it as it is is not allowed."

The promise of an external trace sink (Langfuse) has been moved twice already: first from stage 1
to stage 6, then from stage 6 to here. The text in `shared/trace.py` still says the sink "moved to
stage 8". A third move without a new reason would not be a decision, it would be a habit.

Now the reader exists, and the requirement no longer has to be guessed.

## What the evaluator actually needs from the store

Derived from the code as written, not from an idea of it:

1. **Read everything for a period in one pass.** `trajectory.extract` reads the file whole and
   groups in memory. On the demo's daily file that is milliseconds.
2. **Grouping by the run key.** Done by the reader (ADR-0001), not by the store. It is enough for
   the store to hand over the steps; the evaluator asks for no index by key.
3. **Appending without rewriting.** AC-02b requires the file the evaluator reads to stay
   byte-for-byte unchanged. Append-only gives that for free; a store with in-place updates would
   make the invariant unprovable.
4. **The order is recoverable from the data.** `seq` is on every step, so the physical order of
   the lines does not matter — two processes can write into one file.
5. **Reading with your eyes.** `cat` and `grep` remain the way to look at what happened. It is the
   property the format was chosen for back in stage 1.

What the evaluator does **not** ask for: transactions, queries, partial reads, indexes, retention,
multi-user access, deduplication.

## Decision

**JSONL on a volume satisfies all five requirements. An external sink adds none.**

The promise **is kept by the requirement now existing** — and it turned out to be smaller than the
guess. Langfuse is rejected not "for now" but **on the facts**: it solves problems (search across
trajectories, comparing runs in a web UI, team access) that are not in the list above and will not
be at this scale.

The text in `shared/trace.py` promising a sink "in stage 8" **is fixed by this very commit**:
there is no third move, there is an answer.

## Consequences

**Good.** A promise that travelled through three stages is closed. The next person who wants an
external sink will have a list of five items and will see that not one of them requires it — so
they will have to name a **sixth** requirement, and it will be a real one.

**The price.** The traces will not survive the loss of the machine — that is already recorded in
stage 6's `adr/0008` and addressed to backups in stage 10. Evaluation does not change it.

**The limit, named out loud.** The five requirements are derived from a **teaching** scale: the
demo's daily file and fifteen requests to the service. At a million trajectories item 1 ("read
everything in one pass") stops being cheap, and requirement No. 6 will appear on its own. The
stage says so rather than pretending that JSONL scales.

## Alternatives considered

**Move the promise to stage 10.** A third move in a row. There is no reason for it: the question
is not when to wire up the sink but whether it is needed — and that already has an answer.

**Wire up Langfuse to keep the promise literally.** Keeps the letter and breaks the spirit: an
integration for a consumer that is not asking for it. The course already has this lesson in
stage 4, where a tool registry existed with no consumer at all and therefore proved nothing.

**A table in Postgres.** Gives the queries the evaluator does not make, and takes away the reading
with your eyes that it does. Plus a migration and a second read implementation for zero new
lessons.
