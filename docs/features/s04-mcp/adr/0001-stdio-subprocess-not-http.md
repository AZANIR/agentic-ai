---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0001 — stdio and a subprocess, not HTTP

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

MCP describes several transports. The course has to pick one for the stage where the protocol is
introduced for the first time.

## Considered options

1. **stdio, the server as a subprocess.**
2. **HTTP on a local port** — closer to what it looks like in production.
3. **A mock instead of a transport** — the fastest and the most deterministic.

## Decision outcome

**Chosen:** Option 1.

Option 3 is the first one out, and the reason is not purity. **Half of the stage's lesson is
parsing the response**, and on a mock there is nothing to parse: a mock returns what it was told
to return, in whatever form is convenient. Text around the data, a break mid-call, a process that
never came up — all of that exists only when the boundary is real.

Option 2 gives the same reality and adds a port. A port means: a clash with a busy port on
somebody else's machine, a firewall, "what if I am in a container". The course promises offline
and no configuration, and HTTP keeps that promise only for as long as everything goes well.

stdio gives a process boundary with none of those questions: two channels, `stdin` and `stdout`,
and not one external resource. The reader sees a real subprocess and a real exchange.

**The price is named plainly:** bringing a process up costs seconds, and the stage's checks
become the slowest in the course. NFR-5 raised the bound to eight seconds deliberately —
pretending there is no price would mean either not starting the server or hiding that price.

## Consequences

**Positive**
- The process boundary is real, with all of its failure modes.
- No ports, no network, no configuration: the stage can be completed offline.
- The HTTP transport at stage 6 will read as a change of transport rather than as the arrival of
  a protocol.

**Negative**
- The slowest checks in the course.
- stdio shows no authentication — that arrives at stage 6, and until then the reader may decide
  there is no such thing.
