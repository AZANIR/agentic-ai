---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0001 — The task contract is executable, not described

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The stage compares four implementations of one task. The comparison means something only when the
task is **the same one**: the same input, the same tools, the same model, the same stopping
condition, the same result shape.

The easiest way to pin that down is prose — a list in the README that the author of each
implementation looks at before writing. That is how almost every framework comparison does it, and
it is exactly why almost all of them measure the author's diligence.

The problem is not bad faith, it is invisibility. A CrewAI implementation naturally wants one more
delegation step; a LangGraph implementation naturally wants a separate validation node. Every such
deviation looks like "that is how it is done in this framework" — and every one of them makes the
number in a neighbouring column incomparable. Spotting it by looking at the code is nearly
impossible: both implementations look sensible.

## Decision Drivers

- A difference in the numbers must mean a difference between **frameworks**, not between authors.
- A deviation must be **caught**, not noticed.
- The author of a new implementation must learn about a violation from the run, not from a reviewer.

## Considered Options

**A. A prose contract in the README.** Cheap, familiar, catches nothing.

**B. Comparing against a reference output.** Every implementation must produce the same string.
It catches a deviation in the result — and does not catch a deviation in the **path**: an
implementation that called an extra tool and arrived at the same text passes.

**C. An executable contract.** A function that takes an implementation's result and trace and
returns the list of violated elements. A violating implementation gets no row of numbers.

## Decision

**C.** The contract is code that runs against every implementation before its numbers reach the
table. It checks all five elements, and the **path** among them: the set of tools called and the
condition the run stopped on.

A violator is neither dropped silently nor patched up: its row stays in the table **without
numbers**, naming the element it violated.

## Consequences

**Good.** An unfair comparison stopped being possible quietly. The author of a new implementation
learns about a deviation within seconds, and from the run.

**The price.** The contract constrains the implementations: what is "done this way" in a framework
has to be left undone. That is the price of comparability, and it is deliberate.

**The limit.** The contract does not make the implementations equally good — only equally on-task.
An author who wrote a clumsy LangGraph gets an honest number for a clumsy LangGraph.
