---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0004 — The model picks the route from a list of competences

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The supervisor has to decide who gets the task. That decision can be made by rules (keywords,
regular expressions) or by a model call with a list of competences.

For a demonstration, rules are more convenient: deterministic, fast, no dependency on a provider.

## Considered options

1. **A model call** with a list of competences; determinism in the checks comes from the fake.
2. **Keyword rules** — deterministic without a fake.
3. **Rules with a fallback to the model** when none of them matched.

## Decision outcome

**Chosen:** Option 1.

A regular expression hides the very thing this stage exists for. A reader who has seen
`if "return" in query` has seen a dictionary lookup, not routing — and will understand none of
the problems this stage shows: not why a competence description matters more than a node's name,
not why a route is sometimes wrong, not what the revision loop is for.

The determinism that makes rules tempting is already solved differently in this course: the fake
replays a recorded script, and the script **reads as a specification of the model's behaviour**.
The same device as at stages 1–2.

Option 3 is the worst of the three for teaching: it gives a working system in which it is unclear
what exactly fired on any particular request.

**The consequence the lesson has to name:** on a real model the route may differ from what the
fake gives. That is not a defect of the implementation — it is a property that gets measured, and
the measurement arrives at stage 8. A manual checklist against a real provider is part of this
stage.

## Consequences

**Positive**
- The reader sees routing as a decision, not as a substring search.
- The competence description becomes visibly important — the model is what reads it.
- The revision loop makes sense: the decision can be wrong, and that is a normal state.

**Negative**
- The route is non-deterministic on a real model. Named in the lesson and in the test plan.
- Every route costs a model call. At stage 6 that becomes a question of budget, and that is where
  a cheaper classifier appears as a deliberate trade-off.
