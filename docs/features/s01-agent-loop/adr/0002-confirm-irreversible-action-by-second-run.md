---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-23"
feature_size: "S"
ticket: "n/a"
---

# 0002 — Confirm an irreversible action by a separate repeat run

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** Contributor, Tech Lead

## Context

The source article names as its third and most dangerous failure mode the situation where an
agent performs an irreversible action on its own after misreading the task. Stage 1 introduces
the confirmation gate as a separate guard; the manner of confirming has to be fixed, because from
the specification's text two engineers would write different things — one an interactive prompt,
the other a flag.

The gate is inherited by stages 6 and 10, where the irreversible tool becomes a real return
filed through a public endpoint.

## Decision drivers

- The stage's checks have to stay deterministic and offline (repository ADR 0006).
- CI has no interactive input: `input()` there reads end-of-stream and fails.
- The reader has to see the gate as **an explicit state of the system**, not as a dialogue that
  flashed past in the console.
- The mechanism has to scale to stage 6, where there is no console and no human nearby at all.

## Considered options

1. **Two separate runs** — the first stops and states how to confirm; the second executes.
2. **An interactive y/n prompt in the console** — closer to how it looks in CLI agents.
3. **A confirmation callback** — the loop takes a callable; the demo passes an interactive one,
   the checks a constant one.

## Decision outcome

**Chosen:** Option 1. The deciding argument is not simplicity but **reproducibility**:
confirmation becomes an ordinary argument of the run, so a check describes both states in three
lines, with no mocking of standard input. Option 2 would force mocking `stdin` into the very
first stage of the course — the first piece of magic the reader would not understand, and it
would have appeared for the sake of cosmetics.

Option 3 is technically the best and is exactly where stage 6 will end up — but at stage 1 it
introduces the notion of a callback before the reader has seen an ordinary function call.
Deliberately deferred.

## Consequences

**Positive**
- The gate's check is written with no mocking at all — two calls with a different argument.
- The gate is visible as a state, not as an event: the first run leaves a record in the trace
  saying "the action was not performed".
- It works identically in a terminal, in CI and when imported.

**Negative**
- Less like the live CLI agent the reader is used to. The lesson has to name that outright, or it
  will look like an unfinished feature.
- Two runs mean the confirmation state does not survive the run — irrelevant for stage 1, but
  stage 6 will need real storage.

**Neutral**
- Moving to a callback (option 3) is a swap of one parameter; prepared but not done.
- The irreversibility flag lives in the tool registry rather than as a list of names inside the
  loop, so a fourth irreversible tool can be added without editing the loop.

## Links

- Spec: [[../spec.md]] AC-04, §6.1 (abuse cases)
- SAD: [[../sad.md]] §4, §6 (flow 2), §8
- Stage article: [Three Guards Every Agent Loop Needs](https://artstroy.net/articles/three_guards_every_agent_loop_needs) — failure mode 3
- Related ADRs: [[0001-split-stage-into-four-responsibility-modules]]
