---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0006 — A key in the header, compared in constant time

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The service needs to know who is asking — and not for the sake of accounts, but because three
things depend on it: whether to let them in, at whose expense, and whose memory to read.

Full authentication with token issuing and revocation is a separate product. The course has to show
the **boundary**, not build an access-management system.

## Decision drivers

- The key determines the owner of the memory, so a mistake here is a leak, not an inconvenience.
- A refusal must not distinguish "no such key" from "the key has expired": a difference in the
  answer is an oracle for brute force.
- An ordinary string comparison finishes at the first differing byte, which means it leaks the
  length of the shared prefix through the response time.
- The keys are already in the configuration (`api_keys`) — the model was chosen at stage 0.

## Considered options

1. **A key in the header**, checked against a list with a constant-time comparison.
2. **A signed token** with an expiry and an owner field.
3. **An external identity provider**.

## Decision outcome

**Chosen:** Option 1.

Option 2 makes sense when there are many keys and they are issued programmatically. Here there are
a handful, and the expiry would have to be checked, revoked and refreshed — three mechanisms for a
property the stage does not use.

Option 3 moves the task outside, and half the lesson with it: the reader stops seeing **what
exactly** the guard does.

**Constant-time comparison is not pedantry.** It is the cheapest thing on the list (one function
from the standard library) and the only way not to give away the length of the shared prefix. A
course that shows a guard and compares keys with `==` teaches the defect.

**The price is named:** a key cannot be revoked without a restart, has no expiry, and draws no
distinction between permissions. All three are deliberate, and all three are written down in the
lesson.

## Consequences

**Positive**
- The guard is visible in full and fits on a screen.
- The response time does not depend on how close the key is to the right one.
- The owner of the memory is determined unambiguously and is not passed in as an argument.

**Negative**
- Revoking a key requires a restart. Named in the RUNBOOK.
- There are no roles and no permissions. Multi-tenancy is outside the stage's scope (spec §3).
