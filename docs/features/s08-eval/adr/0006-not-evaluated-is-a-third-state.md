---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0006 — "Unscored" is a third state of the report in its own right

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The judge can be unavailable: no key, the budget is spent, the provider refused. That is not "the
case failed" and it is not "the case passed".

The repository has already made this decision for checks: `NotVerified` in
`shared/check_runner.py` is counted separately, printed in yellow and carried into the summary.
The reason is written down there in plain words: the difference between "it matched" and "it was
never checked" disappears from the output, and a green suite starts meaning less than it looks
like.

The evaluation report is a different artefact, and the decision has to be made for it separately,
because the temptation is stronger here: the "passed" fraction looks worse when the denominator is
honest.

## Decision drivers

- AC-08: an unavailable judge yields "unscored", and it is counted separately.
- A silent failure turns a missing key into poor quality — and a reader without a key sees a
  devastating report about a healthy agent.
- A silent success makes a green report meaningless: without a key everything is green, always.
- Dropping the case from the denominator is the worst of the three: the fraction looks honest and
  is computed over the wrong set.

## Considered options

**A. Count it as a failure.** Penalises the missing key rather than the quality.

**B. Count it as a success.** Produces a hundred-percent report out of nothing.

**C. Drop it from the denominator.** Silently changes what the report is about.

**D. A state of its own and a column of its own.**

## Decision

**D.** A level's verdict has three values: passed, failed, unscored. The summary prints three
numbers and the **denominator** they were taken from. The "passed" fraction is computed over all
cases rather than over the scored ones — otherwise it grows when the judge goes down.

## Consequences

**Good.** A report without a key is honest: the agent is not declared bad, and the evaluation does
not pretend to have happened. The reader sees what scoring the rest would have cost.

**The price.** Three numbers instead of one at every level. It is the same price as in ADR-0003,
and it is paid for the same reason.

**Consequence.** The suite's check asserts that the passed fraction **falls** when the judge
disappears, rather than staying the same. Otherwise the denominator would have changed silently.
