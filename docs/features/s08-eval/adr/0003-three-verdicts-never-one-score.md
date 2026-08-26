---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0003 — Three levels are three independent verdicts, never one score

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The article names three levels: e2e (was the task done), trajectory (was the path sensible),
component (what exactly broke). The temptation to collapse them into one score is strong: a
single number is easier to show, easier to compare with yesterday's, easier to put on a
dashboard.

One score destroys exactly what having three levels is for.

An agent that produced the right answer through a redundant loop and a call to the wrong tool
looks "almost good" in a combined score — that is, the same as an agent that produced a slightly
worse answer by the direct route. Those are two fundamentally different production risks, and a
weighted sum confuses them.

## Decision drivers

- AC-03b: a case can pass one level and fail another, and the report shows both.
- The article says it outright: an agent that is technically successful but takes an unstable
  path is a risk that will surface on exactly the distribution of inputs you did not test.
- A combined score hides "unscored": it either counts it as zero (unfair), or as one (a lie), or
  drops the case (silently).

## Considered options

**A. A weighted sum.** The weights would have to be invented, and any weights are a hidden
opinion about which level matters more, built into a number.

**B. The worst of the three.** It does not lie, but it loses information: "failed" does not say
what.

**C. Three verdicts side by side, totals for each one separately.**

## Decision

**C.** A case's row in the report carries three verdicts. The summary counts three fractions —
one per level — and a fourth column, "unscored". The report prints no combined number at all.

## Consequences

**Good.** "It broke" answers the question "where". A case with the right answer and a bad path
is visible **as a row of its own**, not as 0.7.

**The price.** The report is wider, and "one number for the dashboard" is left for somebody to
compute themselves. That is deliberate: whoever computes it chooses the weights explicitly and
answers for them.

**Consequence for stage 10.** It inherits three fractions rather than one score, and its
dashboard will show three lines. That is right: a single line sagging slowly because of
trajectories while e2e stays flat is exactly the drift that gets noticed too late.
