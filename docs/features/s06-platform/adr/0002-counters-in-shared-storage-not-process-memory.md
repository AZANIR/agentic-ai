---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0002 — Counters in shared storage, not in process memory

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The rate limit and the budget guard are counters. The simplest implementation keeps them in a dict
in the process's memory: zero dependencies, instant access, works flawlessly.

Exactly as long as there is one process.

This is the stage's central trap. A second worker makes every counter untrue **silently**: a limit
of 30 requests per minute lets 60 through with two workers, a budget of five dollars spends ten,
and there is not a single error in the logs.

## Decision drivers

- The stage **teaches** how to recognize this class of defect. Containing one itself is not irony
  but a discrediting of the lesson.
- A limit that silently doubles is worse than no limit at all: no limit is visible.
- The local profile has to work with no container whatsoever (C-2).
- Profile branching lives only in the factories under `shared/` (C-4).

## Considered options

1. **A counter factory in `shared/`**: in memory for `local`, shared storage for `prod`.
2. **Always in the process's memory**, with a single worker as a deployment requirement.
3. **Always in shared storage**, locally included.

## Decision outcome

**Chosen:** Option 1.

Option 2 converts an architectural defect into an operating instruction — that is, into the first
thing anybody breaks. "Do not run more than one worker" holds exactly until the first spike in
load.

Option 3 forces the reader to bring up a container just to run the checks, and breaks the course
rule "everything works offline". The price of the purity is higher than the purity.

**The most likely way this decision fails is named up front**: the in-memory implementation works
locally, the checks get written against the local profile, and the doubling shows up in
production. Hence the need for a check that **the same** counter, created twice, sees one number —
it goes red precisely on an implementation tied to the process.

## Consequences

**Positive**
- The limit means what it says, no matter how many workers there are.
- A local run needs no container.
- Stage 10 takes the same counter unchanged.

**Negative**
- An in-memory counter locally and a shared one in production are **two** implementations, which
  means two behaviours. The check has to assert the shared contract, not one of them.
- Shared storage becomes a dependency whose unavailability has to be handled (AC-11).
