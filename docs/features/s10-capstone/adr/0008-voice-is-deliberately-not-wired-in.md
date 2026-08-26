---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
ticket: "n/a"
---

# 0008 — Voice is deliberately not wired in, and that is stated

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

Stage 7 built a voice pipeline and a live mode. The course design specification calls voice an
"optional adapter" of the capstone.

The question is simple: wire it in or not. And it has a third answer, worse than either — **not
wiring it in and not saying so**.

## Decision Drivers

- Every part in the assembly table has to produce a non-zero number (ADR-0001). Voice wired in
  formally would produce a zero and would redden the check — correctly.
- Wiring it in for real drags in gigabytes of weights and makes the stage impassable on a bare
  installation.
- Skipping it without a word looks like a forgotten stage.

## Considered Options

**A. Wire it in for real.** Gigabytes of dependencies for a conclusion stage 7 has already reached.

**B. Wire it in formally.** Zero executed lines — and an honest check reddens that.

**C. Do not wire it in, and **name** that as a decision with a reason.**

## Decision

**C.** Voice stands in `ARCHITECTURE.md` in the list of parts **deliberately not wired in**, with
the reason: it adds no new conclusion, it adds a dependency of gigabytes, and it makes the stage
impassable offline.

The "deliberately not wired in" list is separate from the list of assembly parts, and that is
exactly why zero executed lines for voice is not an error.

## Consequences

**Good.** The reader sees the difference between "we forgot" and "we decided not to". The second is
an architectural decision and it has a reason.

**The price.** The capstone assembles six stages out of nine: voice and MCP are not wired in for
the reasons above, and stage 9 turned out to be an instrument rather than a part. The number is
smaller than a pretty one — and it is honest.

**The limit.** The decision holds for this repository and this installation. A reader with the
models on disk wires voice in with a single edit, and the list tells them so directly.
