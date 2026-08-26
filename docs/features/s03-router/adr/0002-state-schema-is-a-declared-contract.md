---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0002 — The state schema is a declared contract, not a free-form dictionary

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Every node reads and writes the graph state. The easiest thing is to make it a dictionary:
adding a field is one line, nobody declares anything. That is what most examples look like.

The goal of §2 of the spec is for the reader to see the **state schema as a decision** rather
than as a data structure, and to understand why adding a field to it six months later costs
more than anything else in the graph.

## Considered options

1. **A declared contract:** a fixed set of fields; reading an unknown field is an error.
2. **A free-form dictionary:** any node writes anything.
3. **A dictionary with a check on the way out** — free-form at runtime, reconciled at the end.

## Decision outcome

**Chosen:** Option 1.

A free-form dictionary is not merely risky — it **hides the very thing this stage exists for**.
When adding a field costs one line, the reader has no reason at all to stop and think about what
that field really costs: every node that relies on it will have to read it, and none of them
will say that it appeared.

The chosen option makes the cost visible at the moment of the act: to add a field you have to
open the schema, which means seeing everyone who reads it.

The second reason is the access level (ADR-0003). It lives in the state, and in a dictionary
`state.get("access")` returns `None` wherever the field was forgotten. That is exactly the flaw
stage 2 fixed in document metadata: an unrecognised value must not silently become the default.

Option 3 is out: a check at the end catches the fact once the decision has already been made on
the basis of a `None`.

## Consequences

**Positive**
- The cost of changing the schema is visible at the moment of the change.
- `state.access` cannot silently become `None` — ADR-0003 relies on that.
- The list of fields reads as a description of what the graph knows about the task at all.

**Negative**
- Adding a field is more expensive than in a dictionary. That is not a side effect, it is the
  point.
- A check of our own is needed for reading an unknown field (AC-02b) — a dictionary needs none,
  because there it is not an error.
