---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0004 — State is explicit, through an ID in the payload

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The protocol specification made it **stateless**: a server is not obliged to remember anything
between calls. Servers may remain stateful, but **explicitly** — through identifiers in the
payload rather than through a hidden session.

The course has to decide how to show this on an example where state really is needed: the stage 2
search has an access level, and that lives in the stage 3 graph state.

## Considered options

1. **Everything needed travels in the call payload**, identifiers included.
2. **The server keeps a session** and remembers who asked.
3. **The client passes the state once** per connection.

## Decision outcome

**Chosen:** Option 1.

Option 2 contradicts the specification and loses in practice: a server with memory cannot be
restarted transparently, cannot be brought up a second time for load, and cannot be debugged from
a single call. Every response becomes a function of a history that is not in the logs.

Option 3 looks economical and hides the same flaw: after the second call it is already unclear
what state the server is in, and after a restart, all the more so.

An explicit payload gives a property worth naming outright: **the call is reproducible**. Take a
line out of the trace, repeat it, get the same thing. That is what stage 8 will lean on once it
starts measuring.

**Separately on the access level.** It travels in the payload as part of the request, but **not
as a parameter the model chooses** — exactly as at stage 3. The model formulates the query; who
is asking is decided by the client from its own state.

## Consequences

**Positive**
- The server can be restarted at any moment: it loses nothing.
- A call from the trace is reproduced verbatim — the basis of the measurement at stage 8.
- It follows the protocol specification rather than fighting it.

**Negative**
- The payload is larger, and some fields repeat on every call.
- The temptation to put superfluous things into the payload. The boundary is simple: whatever the
  call cannot be reproduced without belongs there; everything else does not.
