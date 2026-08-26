---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0001 — Trajectory is keyed by a parameter, not by a fixed field

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The evaluator reads traces that are already being written. Reading them is not enough — the steps
have to be **grouped into trajectories**, and that is exactly where the two existing stages
diverge.

Stage 1 opens a `trace_run` per scenario: one trajectory is one `trace_id`, bounded by the
`run_start` and `run_end` steps.

Stage 6 opens a `trace_run` **once per process** and marks every request with its own
`trace_ref`. Grouping by `trace_id` there would produce one gigantic "trajectory" spanning the
entire lifetime of the service.

Measured on real files: stage 1 — 4 trajectories of 5–7 steps; stage 6 — one trajectory by
`trace_id`, and as many by `trace_ref` as there were requests.

Both approaches are right for their own stage. Neither is a mistake to be fixed.

## Decision drivers

- AC-11: the same code evaluates both sources. An evaluator that can only read its own format
  only evaluates itself.
- C-2: stages 1–7 do not change for the sake of evaluation. Reducing them to one way of grouping
  would break that with the very first commit.
- The next stages (9, 10) will add a third way, and it cannot be declared wrong either.

## Considered options

**A. Pin `trace_id`.** The simplest — and it declares stage 6 broken. A single request stops
being the unit of evaluation exactly where it is one.

**B. Teach every level to read both formats.** Smears knowledge of the format across all the
levels: a third format would have to be written into three places, and one of them will be
forgotten.

**C. The key is a parameter of the extractor.** One module knows about formats; the levels see a
`Trajectory` and do not know where it came from.

## Decision

**C.** `trajectory.py` extracts trajectories through a key function. Two come ready: by
`trace_id`, and by `trace_ref` falling back to `trace_id`. The evaluation levels take a
`Trajectory` and know nothing about its source.

## Consequences

**Good.** A new format is a new key, not an edit to the levels. The AC-11 check runs the same
code over stage 1's and stage 6's traces and asserts that both produced non-empty trajectories.

**The price.** The key has to be chosen at the call site, and the wrong choice yields plausible
garbage — one long trajectory instead of many. So the extractor reports the **number** of
trajectories and their length, and the check asserts that on stage 6's trace there is more than
one.

**The limit.** The extractor does not guess the key by itself. Automatic selection would look
convenient and would silently get it wrong on a format that does not exist yet.
