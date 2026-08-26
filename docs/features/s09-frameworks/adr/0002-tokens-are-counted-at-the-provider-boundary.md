---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0002 — Tokens are counted at the provider boundary, not inside the implementation

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The "tokens above the request" column is the price of the scaffolding: the framework's system
prompts, the role descriptions, the history re-sent on every step. The question is **where** to
count it.

A counter inside the implementation sees what the implementation asked for. What the framework
added is, by construction, exactly what it does not see — and that is precisely the quantity being
measured.

The second option is to trust the framework's own reporting. Each one reports in its own way, some
do not report at all, and none reports in a neighbour's units. Comparing such numbers means
comparing three different definitions of the word "token".

## Decision Drivers

- What is measured is the **overhead**, that is, the difference between what was asked for and what
  went out.
- The unit must be one and the same for all four implementations.
- The offline number must be deterministic (NFR-6).

## Considered Options

**A. A counter in each implementation.** It does not see the overhead — that is, it measures
nothing of what it exists for.

**B. The framework's own reporting.** Three different definitions, one of them missing.

**C. A wrapper around the client from `shared.llm`.** The single point everyone is obliged to go
through (ADR-0007). It sees the actual request, whatever layer assembled it.

## Decision

**C.** `counters.py` wraps the client obtained from `shared.llm.get_client` and counts two numbers:
how many tokens are in what the implementation assembled, and how many in what actually went out.

The counter **does not store** the request text — only the numbers (spec §6.1).

## Consequences

**Good.** The overhead became an observable quantity, the same one for all four. For the baseline it
equals zero — and that is the mirror half, without which a counter is not a counter.

**The price.** An implementation that goes around `shared.llm` stays uncounted. That is why
ADR-0007 makes the bypass a caught error rather than a matter of discipline.

**The limit.** Tokens are counted approximately — by text length, not by the provider's tokenizer.
For **ratios** that is enough; for the provider's bill it is not, and the lesson says so outright.
