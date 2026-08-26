---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0005 — Leave stages 2 and 5 out of the trace

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The spec promises a trace that answers the question "why did the agent decide that". While the
criteria were being written it turned out that stages 2 and 5 write **not a single** step into the
trace: `store.search()` takes no tracer, and `Memory.context_for()` returns its reasons in
`Context.skipped`.

So the service's trace will show **which branch** was chosen, and will not show **why** exactly
these documents and exactly these facts were found. Half the promise stays outside.

## Decision drivers

- C-1: editing stages 1–5 requires a record, and this record is it.
- Adding `tracer=None` is additive and cheap. Cheapness is not an argument in favour.
- Stage 8 builds evaluation **on traces** and will say what it actually lacks.
- The reasons already exist in the structures (`Context.skipped`, the search scores) — they are not
  lost, they are simply not in the trace.

## Considered options

1. **Do not thread it through**; name the limit in AC-02 and in the lesson.
2. **Thread an optional tracer** into both stages now.
3. **Duplicate the reasons on the service side**: the service itself writes down what the
   structures returned.

## Decision outcome

**Chosen:** Option 1.

Option 2 looks like the right one and is being taken **not now**. The reason is not the cost of the
edit but that the requirement for it will be formulated by stage 8: it will read the traces and say
which fields evaluation is missing. Threading a tracer through on a guess means designing an
interface for an imaginary consumer, and the course already has exactly this lesson at stage 4,
where a tool registry existed with no consumer at all and therefore proved nothing.

Option 3 gives a trace that looks complete and lies: the reasons are written down by whoever did
not take the decision. The divergence between what is written and what happened will appear on the
first change in stage 2 — silently.

**The limit is not hidden.** AC-02 names it word for word, the lesson repeats it, and §11 carries a
line with an owner and a due date.

## Consequences

**Positive**
- Stages 1–5 stay unchanged; the claim about the boundaries between stages is not broken.
- The requirement for the trace will be formulated by whoever reads it.
- There is no trace that looks fuller than it is.

**Negative**
- Stage 6's trace answers "which branch" and does not answer "why exactly these documents". That is
  named in AC-02, rather than discovered at stage 8.
- The debt is recorded in §11 with an owner and a due date.
