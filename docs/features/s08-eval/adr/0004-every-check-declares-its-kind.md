---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0004 — Every evaluator declares its kind: deterministic, or judging

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The article states the principle: deterministic checks for everything that has a clear right
answer; the judge only for what genuinely needs judgement. Using an expensive non-deterministic
judge where a comparison would do is waste and unreliability at once.

A principle written down in prose is broken by the first convenient edit: "let it judge here
too, it is more flexible that way". Spotting that in somebody else's code is impossible — a call
to the judge looks like any other call.

## Decision drivers

- AC-04 requires the kind of check to be **visible**, not implied.
- Every call to the judge costs money and does not repeat; the number of calls has to be a
  counted quantity rather than a by-product.
- The lesson has to be a checkable claim rather than a wish — like "the sum of the steps" in
  stage 7.

## Considered options

**A. An agreement in prose.** It is already in the article; that is precisely why something
stronger is needed.

**B. Naming (`check_*` versus `judge_*`).** Better than nothing, but it is grepped rather than
checked, and it stays silent once a call to the judge appears inside a `check_*`.

**C. The kind is a field of the verdict, and a suite check asserts the split.**

## Decision

**C.** Every level **verdict** carries a kind field: deterministic, or judging. The words are
used precisely here (spec §1): an **evaluator** is the harness component that delivers a level's
verdict; a **check** is an `assert` function in `check.py`. The field lives on `Verdict`, not on
the check function.

The suite asserts two things:

1. A deterministic **evaluator** does not call the judge — proven by a call counter, not by
   reading the code.
2. The number of judge calls per run equals the number of judging evaluators **minus** those
   that had nothing to judge: for a trace with no answer the judge is not called at all. Nobody
   pays for missing data — and that is not an exception to the rule, it is the whole point of
   the third state.

## Consequences

**Good.** The article's principle became checkable. An attempt at "let it judge here too" turns
the suite red with a message that names the evaluator.

**The price.** One extra field on every verdict. It pays for itself with the first edit that
would otherwise have gone unnoticed.

**The limit.** The rule does not say **which** property needs judgement — that is the case
author's decision. It says only that the decision has to be stated and then kept.
