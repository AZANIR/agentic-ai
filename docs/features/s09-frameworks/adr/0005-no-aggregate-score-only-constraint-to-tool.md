---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0005 — No aggregate score: the conclusion has the shape "constraint → tool"

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

A comparison table naturally wants a bottom line. The reader wants to know which one to take.

An aggregate score requires weights: what a line of code costs against a token, what it costs to be
able to answer "why did this step run". Any set of weights is an opinion about whose constraint
matters more — and that opinion, baked into a number, stops being arguable.

This is the same ban as on stage 8, and for the same reason.

## Decision Drivers

- The reader has to choose within **their own** task, not within this table.
- The recommendation must be checkable: it has to rest on a column, not on an impression.
- The stage has no right to declare a winner, because it does not know the reader's constraints.

## Considered Options

**A. An aggregate score with weights.** Hides an opinion inside a number.

**B. No conclusion at all — just the table.** Honest and useless: the table is what the reader came
for.

**C. A list of "if your constraint is this — take that", where every line cites a column.**

## Decision

**C.** The table carries neither an aggregate score nor the word "best". In their place is a list of
rules shaped "constraint → tool", and every rule names the **column** it was derived from.

## Consequences

**Good.** A rule applies to a task that is not in the table — and the reader's task will be exactly
that kind.

**The price.** The answer is longer than one word. A reader who came for "take X" leaves
disappointed — and that is the right side of the trade-off for a teaching stage.

**The limit.** The rules are derived from **these** measurements. Change the task and the columns
change, and the rule has to be derived again; the lesson says so outright.
