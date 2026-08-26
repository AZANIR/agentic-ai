---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---


# 0008 — Traces stay a JSONL file on a mounted volume

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Stages 1–5 write traces to a JSONL file: one line = one step. AC-10 requires the trace to survive a
container restart, and that on its own does not force a change of format — a volume is enough.

But **the repository has already made two promises on this stage's behalf**, and both were found
only during the architecture review:

- `shared/trace.py` raises a `ConfigError` whose text reads "the Langfuse sink is added **at stage
  6**".
- `deploy/docker-compose.yml` says that the full stack with Prometheus, Grafana and Langfuse "is
  added **at stage 6** in `docker-compose.prod.yml`".

A promise a stage neither keeps nor moves is not a debt but an untruth in the code, and the reader
will reach it sooner than the author does: `TRACE_SINK=langfuse` will hand them a failure on the
very first request.

## Decision drivers

- The reader has to **read traces with their eyes**. That is the property the format was chosen for
  at stage 1, and none of the later stages has outgrown it yet.
- Evaluation (stage 8) will read the traces and **will formulate the requirement** for the store.
  Right now there is no such requirement — there is a guess.
- Promises in the code have either to be kept or to be moved, naming the new stage. Leaving them as
  they are is not allowed.
- A trace in a database adds a table, a migration and a query in place of `cat` — for zero new
  lessons at this stage.

## Considered options

1. **A JSONL file on a mounted volume**; the promises move to stage 8, with a reason.
2. **A table in Postgres**: the traces in the same place as the facts.
3. **An external trace sink** (Langfuse) — keep the promise literally.

## Decision outcome

**Chosen:** Option 1.

Option 2 satisfies AC-10 and takes away the property the format was chosen for: looking at a trace
stops being `cat` and becomes a query. Plus a migration, plus a module, plus two implementations of
reading — all of that has a price and **not one** new lesson right here.

Option 3 is attractive because it keeps the promise literally. It is rejected for the same reason
as ADR-0005: the requirement for the trace will be formulated by whoever **reads** it, and that is
stage 8. Wiring up an external sink on a guess means designing an integration for an imaginary
consumer — and the course already has this lesson at stage 4, where a tool registry existed with no
consumer and therefore proved nothing.

**Both promises are moved, not hushed.** The text in `shared/trace.py` and the comment in
`deploy/docker-compose.yml` are corrected by the same commit as this decision, and they name the
new stage together with the reason. A promise moved in silence is worse than one left unkept: an
unkept one is visible.

**The volume is not a deployment detail but a requirement.** Traces in the container layer
disappear with every image update, and that is exactly what AC-10 goes red on.

## Consequences

**Positive**
- The trace stays readable with `cat` and `grep` — the same way as at stages 1–5.
- Zero new modules, zero migrations, zero second implementation of reading.
- The requirement for the store will be formulated by stage 8, when it really does read the traces.

**Negative**
- The traces will not survive the loss of the machine — backups arrive at stage 10.
- Search across the traces is linear. At this stage's volumes that is `grep`; at stage 8's volumes
  it no longer is, and that is exactly where the question will be posed properly.
- The promise about Langfuse now stands at stage 8. If that stage does not keep it either, this
  will have to be written down again — which means the debt stays visible.
