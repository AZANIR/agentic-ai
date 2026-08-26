---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0007 — Selection into the sample is deterministic, and the actual fraction is verified

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

Online evaluation: cheap deterministic checks on every request, the judge on 5–10 %. The natural
way to implement the selection is a random number against a threshold.

Random selection has two flaws exactly here. The first: no check can be written for it without
flapping — the fraction over ten requests wanders from zero to three. The second, worse one: the
declared fraction and the actual one drift apart silently. Somebody changes the threshold, forgets
the divisor, and for a year nobody sees that the judge is looking at one request in a thousand.

## Decision drivers

- NFR-6: the check does not flap. Random selection either flaps, or is checked with a tolerance so
  wide that it asserts nothing.
- AC-07c: the actual fraction is checked against the declared one. A fraction nobody verified is
  an intention, not a setting.
- The stage 7 lesson: a tolerance wide enough not to flap no longer distinguishes what is being
  measured.

## Considered options

**A. A random number against a threshold.** The most familiar, and impossible to check
deterministically.

**B. Every Nth request.** Deterministic and checkable, but systematic: if the traffic has a
periodicity, the sample catches the same phase every time.

**C. A hash of the request identifier against a threshold.** Deterministic by identifier, uniform
by distribution, and the same request always gives the same decision.

## Decision

**C.** The "judge or not" decision is a function of the **request identifier** and the threshold.
The same identifier always gives the same decision, and the distribution of identifiers gives the
uniformity.

The harness computes the **actual** fraction for a run and reports both numbers — the declared one
and the one obtained. The limit on the divergence is named explicitly and depends on the number of
requests: on a hundred requests, demanding accuracy to the percent is demanding what is not in the
data.

## Consequences

**Good.** The check is deterministic: the same stream of identifiers gives the same fraction. A
divergence between declared and actual is visible **as a number**, not as a guess.

**The price.** A request identifier is needed. The stage 6 service already has one (`trace_ref`),
so the price is zero here and non-zero for anyone who has no such identifier.

**The limit.** Deterministic selection means that **the very same** request will never fall into
the sample if it did not fall in the first time. For evaluating quality that is rather a good
thing — repeats do not inflate the statistics — but debugging one particular request needs a
separate path, and the stage does not build one.
