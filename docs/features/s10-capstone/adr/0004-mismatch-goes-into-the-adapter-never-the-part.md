---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
ticket: "n/a"
---

# 0004 — A mismatch goes into the adapter, never into the part

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

During assembly there is inevitably a part that **one edit** would make more convenient: rename a
field, add an argument, return a different type.

The temptation to make that edit is nearly irresistible: it is cheaper than an adapter, it looks
cleaner, and it improves the stage itself.

## Decision Drivers

- The capstone's claim is "the parts were mature". A part you had to edit disproves it.
- Stages 1–9 have lessons, checks and tags of their own; a change touches all of them.
- The price of assembly has to stay **measured**, not hidden inside somebody else's stage.

## Considered Options

**A. Edit the part.** Cheap here, expensive everywhere: the lesson, the checks, the tag, the
article.

**B. Edit the part "just a little", compatibly only.** The same act under a softer name.

**C. Every mismatch goes into the adapter.**

## Decision

**C.** The parts do not change (C-2). Every mismatch becomes adapter lines and lands in the number
that is the price of assembly.

If an edit to a part really is needed, it goes **into the report** "what assembly revealed", naming
the stage — not into the code.

## Consequences

**Good.** The price of assembly is honest: it is visible in full, in one place, and it cannot be
lowered by moving it into somebody else's stage.

**The price.** A few adapters exist purely because two parts call the same thing by different
names. It looks wasteful — and that is precisely the finding about the course.

**The limit.** The decision does not forbid editing the stages **at some point**. It forbids doing
it **during assembly**, when an edit looks small exactly because you are looking at it from the
capstone's side.
