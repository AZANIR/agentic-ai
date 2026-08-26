---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0007 — Every implementation goes through the shared provider boundary, and execution proves it

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

Frameworks love clients of their own. The LangChain ecosystem has its wrappers, CrewAI has its own,
ADK has its own. The shortest way to write each implementation is to let the framework do what it
does by default.

There are three consequences, and all of them are silent. Such a client **does not pass through**
the counter (ADR-0002), so the token column comes out empty or false. It **does not see** the fake
model, so the stage stops passing offline. And it **reads the key from the environment itself**, so
a run on a machine that holds someone else's key goes to the network with no warning.

The rule "everyone takes the client from `shared/llm.py`" already exists in the repository (the
repository's ADR-0003). Here it meets, for the first time, code that has an opinion of its own.

## Decision Drivers

- Offline is a condition of the course, not a convenience.
- Token accounting is impossible outside the boundary.
- A violation must be **caught**, not documented.

## Considered Options

**A. An agreement in CONVENTIONS.** Already there; the framework does not read it.

**B. A check by inspecting imports.** Catches a direct import, and does not catch a client the
framework creates inside itself.

**C. A check by execution: run every implementation with no key and no network.**

## Decision

**C.** Every implementation receives the client **as a parameter**, and the check runs all four in an
environment with no key. An implementation that created a client of its own either dies on the
missing key or goes to the network — and both outcomes are caught, because the check run has no
network.

## Consequences

**Good.** Offline and token accounting became a property proven by a run. Going around the boundary
can no longer be quiet.

**The price.** Every framework has to be talked into accepting someone else's client — this is the
largest part of the code in each of the three implementations. And that is **a finding in itself**:
the lines spent on not letting the framework do it its own way are the price of the scaffolding, and
they land in the "my lines" column honestly.

**The limit.** A framework that cannot be talked into it stays unimplemented — and that will be a
result of the stage, not its failure.
