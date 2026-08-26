---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
ticket: "n/a"
---

# 0001 — Assembly is proven by executed lines, not by a list of imports

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The capstone had to prove the claim "it assembles what stages 1–9 made mature". The most obvious
proof is a list of imports: show the `from stages.sNN_… import …` lines and count the stages.

This was measured before the first line of code, and the measurement is what changed the
decision: **stage 6 already imports stages 1, 2, 3 and 5.** So a list of imports does not tell the
capstone apart from what happened four stages ago.

Worse. From stage 2, stage 6 imports exactly one name:

    from stages.s02_rag.documents import PUBLIC

That is an **access-level constant**, which travels on as an argument. Retrieval, embeddings, the
access filter — everything stage 2 exists for — **never** runs. In the import list stage 2 is
present; in the work it is absent.

A list of imports is not merely weak proof. It is proof that **hides exactly the thing** being
asked about.

## Decision Drivers

- The proof has to tell "present" from "works".
- It has to be a number, not the author's judgement.
- It has to work identically for nine stages written in nine different ways.

## Considered Options

**A. A list of imports.** Cheap, familiar, hides a zero.

**B. Test coverage of the parts.** Speaks about a part's own checks, not about the capstone's work.

**C. Executed lines per request.** Tracing collects the line numbers that fired and groups them by
the stage's package.

## Decision

**C.** The stage's headline number is the table "stage → how many of its lines executed on one
request". A stage named as part of the assembly that yields **zero** reddens the check.

A stage may be declared deliberately not wired in — but then it stands in a different list and
does not count as part of the assembly.

## Consequences

**Good.** The stage's claim became checkable, and the very first check found a real case — stage 2
inside the stage 6 service. That case goes into the lesson as an example, not as a reproach.

**The price.** Tracing costs run time and demands a warm-up: the first run in a process also
executes the import lines. Both prices were already paid at stage 9 and are named there.

**The limit.** The number describes **this request**. Another request executes other lines — which
is exactly why there are five scenarios and not one.
