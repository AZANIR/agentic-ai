---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0006 — A missing package is a third state, but a flag that is on must not be silent

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

Three of the four implementations need optional packages, and one of them needs someone else's
credentials on top. The reader's machine may have none of it.

Going red on a missing optional package would mean demanding that everything be installed — and
making the stage impassable for anyone who came to have a look. Hence the "not evaluated" state,
which the repository already has (`shared/check_runner.NotVerified`).

But that answer is not enough, and this is exactly where the trap hides. If "not evaluated" is
applied to the case "the reader **explicitly turned on** ADK and there are no credentials", the flag
becomes silent: it was asked to switch on, it seemingly switched on, and the table showed three rows
instead of four. The reader never learns that nothing happened.

## Decision Drivers

- A base install stays passable.
- The absence of what was **not asked for** is not an error.
- The absence of what **was** asked for is an error, and a loud one.

## Considered Options

**A. Go red on any absence.** Demands installing everything, someone else's keys included.

**B. "Not evaluated" for any absence.** Makes the flag silent.

**C. Distinguish the asked-for from the unasked-for.**

## Decision

**C.** The package is missing and nobody asked for it — **not evaluated**, its own row in the table.
The flag is on and the credentials or the package are missing — **a loud failure** that names
exactly what is lacking, without showing the contents of the environment.

## Consequences

**Good.** The stage passes on a bare install and at the same time does not lie to whoever asked for
more.

**The price.** Two branches instead of one, and both have to be checked.

**The limit.** "Not evaluated" remains the stage's weakest spot: the ADK implementation is written,
but the authors have no credentials to run it. That is named in §11 of the SAD, not hidden.
