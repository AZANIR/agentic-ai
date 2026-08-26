---
status: Accepted
owner: "Contributor"
reviewers: ["Tech Lead"]
updated_at: "2026-08-27"
feature_size: "n/a (amends a repository-wide decision)"
ticket: "n/a"
---

# 0009 — the third state is recorded, not forbidden

- **Status:** Accepted
- **Date:** 2026-08-27
- **Deciders:** Contributor, Tech Lead
- **Amends:** ADR-0006 (checks as bare asserts, and the third state), ADR-0007 (the
  `optional-extras` job and its unverified gate)

## Context

The `optional-extras` job exists for one reason: a check that says `NOT EVALUATED` under the base
install must actually execute somewhere. Otherwise the pipeline is green and nothing was proved.
Its final step greps the log for the marker and fails the build if it finds any.

That step has never executed. The step above it failed first, and a failed step skips the rest of
the job. The pipeline had exactly one run in its history, and in it the gate was `skipped`.

When the failure above it was fixed and the step ran for the first time, it failed — and it would
have failed on the day it was written, because **it is unsatisfiable by construction**. Two of
stage 10's checks are third-state permanently:

- `FAILURE · навантаження: без інструмента — третій стан (AC-08b)` — needs a load tool, which is in
  no extra.
- `FAILURE · деплой: прогін проти справжнього HTTPS — третій стан (AC-13c)` — needs a live machine
  with a domain. No package resolves that, and stage 10's own materials say so in as many words.

A rule that can never pass is not a strict rule. It is an absent one, and this repository has now
seen that shape twice in the same step: ADR-0007 records it going blind because `check_all.py` did
not print the marker for green modules, and this ADR records it going blind because nothing ever
reached it.

## Decision drivers

- A third state is a **first-class outcome** of this course, not a failure to be stamped out.
  ADR-0006 introduced it precisely so that "not proved" would stop being reported as "proved".
- A gate must be able to pass, or it teaches the team to ignore it.
- What is permitted must be **enumerated**, not inferred from a marker string, because a marker
  cannot distinguish "nobody installed the package" from "no machine has a domain".

## Considered options

1. **Keep the blunt grep.** Rejected: unsatisfiable, as above.
2. **Narrow it to whole modules skipped for a missing package.** Rejected: `check_all.py` forwards
   per-check third states from green modules specifically so this step can see them (ADR-0007).
   Narrowing would quietly discard the guarantee that ADR was written to create.
3. **Install everything and repair whatever then fails.** Attempted, and it surfaced a genuine
   defect: with `crewai` present, stage 9's CrewAI implementation fails on every call with
   `Counted.call() got an unexpected keyword argument 'from_task'`. Repairing that means
   re-measuring stage 9's numbers on an interpreter where `crewai` cannot be installed at all.
   That is its own decision, not a side effect of fixing a gate.
4. **Record what may stay silent.** Chosen.

## Decision outcome

**Chosen:** option 4. `ALLOWED_UNVERIFIED` in `scripts/check_all.py` names every check permitted to
remain third-state in the `optional-extras` environment, each with its reason.
`python scripts/check_all.py --strict-unverified` compares the run against it and fails on a
difference **in either direction**:

- a third state that is not in the register is a regression — something stopped being verified;
- a register entry that no longer appears is equally a failure — the check started passing and the
  register is now promising silence that does not happen.

Both halves matter. Only the first is the obvious one, and a register with only the first half
rots into a list of excuses nobody revisits.

The entries are **copied from a run**, exactly as `expect_failed` is in each `mutations.json`. A
hand-written entry asserts something about a check nobody has seen. The failure message therefore
prints a paste-ready block for the run that produced it, so the correct thing to do is also the
easiest one.

## Consequences

**The register describes one environment** — the extras, services and interpreter of the
`optional-extras` job. Elsewhere the set legitimately differs: stage 9's line counts are measured
on one interpreter and report a third state on another (that is the point of the condition stated
in its lesson). So `--strict-unverified` belongs to that job and not to the daily local run;
`python scripts/check_all.py` without the flag is unchanged.

**Two entries are expected to be permanent** — stage 10's load tool and its HTTPS deploy. Two more
are temporary and name a defect rather than a limit: stage 9's contract and boundary checks stay
silent until the CrewAI shim is repaired. Writing the reason next to each is what keeps the second
kind from quietly becoming the first.

**A new check that lands third-state now fails the build** rather than passing unnoticed, which is
what ADR-0007 wanted and what the grep, in the whole of its existence, never once did.
