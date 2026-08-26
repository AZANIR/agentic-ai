---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0001 — A hand-rolled mini-graph first, LangGraph second

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The source article shows LangGraph and mentions a hand-rolled implementation as a reference.
The course has to decide what the reader sees **first**, because the first thing is what they
will remember as "how it works".

## Considered options

1. **Our own graph, then LangGraph.**
2. **LangGraph only** — shorter, closer to production practice.
3. **Our own graph only** — no dependencies, but the reader never sees what everyone else uses.

## Decision outcome

**Chosen:** Option 1.

Routing is a `while`, a dictionary and a counter. Having read that in sixty lines, the reader
then recognises the same thing in `add_node` and `add_edge`, and the question "what am I paying
for with this dependency" becomes answerable. Having read LangGraph first, they get an API
instead of the mechanics.

Option 2 is out not because LangGraph is bad, but because this stage exists for the sake of
understanding rather than the result: the result is already in the article. Option 3 leaves the
reader with no bearing on what the rest of the world uses — and with nothing to compare against.

The price of the choice is named plainly: **two codebases instead of one**, that is, two places
that can drift apart. Which is why AC-06 compares the routes and fails on a divergence, rather
than relying on the author to update both.

## Consequences

**Positive**
- The reader sees that there is no magic in routing before they see the library.
- Comparison becomes possible: the same task, two codebases, the same route.
- LangGraph stays optional (NFR-5), so the stage can be completed without installing it.

**Negative**
- Two implementations have to be kept in sync. Pinned by a check, not by discipline.
- The hand-rolled graph is not fit for production, and the lesson must say so out loud, or
  somebody will carry those sixty lines into working code.
