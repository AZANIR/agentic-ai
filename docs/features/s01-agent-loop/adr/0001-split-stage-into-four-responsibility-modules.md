---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-23"
feature_size: "S"
ticket: "n/a"
---

# 0001 — Split the stage into four responsibility modules

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** Contributor, Tech Lead

## Context

Stage 1 contains the ReAct loop and three guards: the step limit, argument validation and the
confirmation gate on an irreversible action. Together that is ~180 lines of code. The layout
chosen here is copied into all nine following stages — this is not a local decision about one
package but the template for the course.

## Decision drivers

- Transparent mechanics is quality goal №1 (SAD §1): the reader has to see the guards as separate
  things, not as lines inside the loop.
- Stages 2–10 inherit the guards; if they have no name and no file, nobody will carry them over.
- The lesson walks the reader through in order — it needs a unit larger than a function and
  smaller than a package.
- The loop module has to fit into ≤120 lines of executable code (spec §6).

## Considered options

1. **Four modules by responsibility** — `loop` (the loop + the limit + the gate), `validate`,
   `tools`, `run`; the checks separately in `check`.
2. **A single `agent.py`** — read top to bottom, as in the source article.
3. **Two modules: `agent` + `tools`** — the classic split of "mechanics apart, tools apart".
4. **A package with `domain/app/infra` subpackages** — as in a production service.

## Decision outcome

**Chosen:** Option 1. It is the only one that makes each guard **visible from the file tree**
rather than from comments inside a function. Option 2 gives ~250 lines in one module and turns
into an unreadable file at stages 6 and 10. Option 3 hides validation inside the loop — that is,
it destroys the exact property the stage exists for. Option 4 would give five levels of nesting
over 180 lines, and the reader would learn the layout instead of the agent.

The rule is simple and checkable: **one module, one responsibility, each fitting on one screen.**

## Consequences

**Positive**
- The guards have names and files, so stages 2–10 carry them over rather than reinventing them.
- The lesson leads the reader file by file, each one a separate finished thought.
- The "≤120 lines" limit on the loop module becomes checkable, because the loop contains nothing
  else.

**Negative**
- The reader jumps between four files instead of one continuous text — a real loss compared with
  the article's code. Compensated by the lesson stating the reading order explicitly.
- Four modules over ~180 lines look excessive if you only look at stage 1 and do not see that the
  same thing will repeat nine times.

**Neutral**
- Merging the modules back into one file is easy; splitting a merged file a year later is not. The
  decision is reversible in the cheap direction.
- The number of modules is not fixed as dogma: a stage that only needs two will take two.

## Update 2026-08-23 (after the review)

There are now **five** modules: the confirmation gate moved out of `loop.py` into its own
`gate.py`.

This is not a revision of the decision but an application of it. The review showed that the gate
has to work at the level of **the step**, not of an individual call; the new logic did not fit
into the loop without breaking the 120-line limit. The mitigation had been written down in advance
in [[../sad.md]] §11 for exactly this case — and it worked as planned.

The rule from the Decision outcome section stands and continues to govern the layout: **one
module, one responsibility, each fitting on one screen**. The number of modules was never dogma.

## Links

- Spec: [[../spec.md]] §6 (module sizes), AC-02, AC-03, AC-04
- SAD: [[../sad.md]] §5
- Repository ADR: [[../../../adr/0001-single-installable-package-with-per-stage-extras]]
- Related ADRs: [[0002-confirm-irreversible-action-by-second-run]], [[0003-hand-written-argument-validation-inside-the-stage]]
