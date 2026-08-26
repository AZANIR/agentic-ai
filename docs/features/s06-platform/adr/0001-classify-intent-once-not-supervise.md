---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0001 — Classify intent once instead of a full supervisor

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Stage 3 produced a working supervisor: the route, the handoff to a specialist, the assessment of
the answer, a revision loop with a counter. The stage 6 service has to pick a branch for every
request, and the temptation to take what is already built is obvious.

The question is not whether the supervisor is better. The question is **how many model calls the
branch choice costs** — and whether that price is justified for three branches.

## Decision drivers

- The supervisor spends at least two calls per request: the route and the assessment. Every
  revision loop adds two more.
- There are three branches, and they are easy to tell apart from the wording of the request.
- Stage 6 has a **budget guard**: a stage that spends twice what it needs would contradict its
  own lesson.
- The trade-off has to be **named with a number**, not proclaimed.

## Considered options

1. **An intent classifier** — one call, one answer out of the list of branches.
2. **Stage 3's full supervisor** — route, handoff, assessment, revisions.
3. **Keyword rules** — zero model calls.

## Decision outcome

**Chosen:** Option 1.

Option 2 gives what the service does not use: a revision loop makes sense when there is somebody
to re-assess the answer, and the service hands it to the user. Paying for an assessment whose
result goes nowhere is not architecture, it is inertia.

Option 3 looks attractive and breaks on the first rephrasing: "how long does a return take" and
"how long do I wait for the money back" — the same intent with not a single keyword in common.

**There is deliberately no fallback path when the budget is exhausted.** The temptation is
obvious: classify by keywords and answer somehow. It is rejected, because it turns the guard into
advice: AC-05 requires that the model call **does not happen**, and a service that answers in that
state would make the refusal soft exactly where it has to be hard. An exhausted budget is a
refusal, not a degradation.

**The limit is named with a number, not with an opinion.** The classifier gets it wrong on
requests that touch two branches at once ("refund order 4471 — and how many days does that take").
A supervisor would decompose such a request; the classifier will pick one branch. The stage lesson
names that share as measured on a set of requests, rather than estimating it in words.

## Consequences

**Positive**
- One model call for the branch choice instead of two or more.
- The branch is known **before** the agent runs, so it lands in the trace as the first step.
- Classification costs exactly one call, so the budget accounting has one addend per branch.

**Negative**
- Compound requests are handled by a single branch. Named in the lesson with a number.
- There is no self-assessment of the answer. That is deliberate: evaluation is stage 8, and it is
  done on traces offline, not on the hot path at the user's expense.
