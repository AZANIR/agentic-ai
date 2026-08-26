---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0003 — My lines and invisible lines are two numbers, and the invisible one is measured by execution

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

"Less code" is the main argument in favour of frameworks, and it is almost always presented as a
single number. One number here lies in a predictable direction: the code did not go away, it moved
somewhere you cannot see it, cannot read it during an incident and cannot fix it.

The question is not whether to count a second number, but **what exactly** it should count.

The most obvious candidate is the size of the installed package. That number is large, impressive
and almost meaningless: CrewAI brings support for dozens of integrations along with it, and on this
input not one of them will execute.

## Decision Drivers

- The second number must describe **this task**, not a catalogue of capabilities.
- It must be reproducible offline.
- The way it is counted must be named, because any two readings of it differ by multiples.

## Considered Options

**A. One number — my lines.** The classic form of the argument, and the very one the stage refutes.

**B. My lines + the size of the installed package.** The second number impresses and means nothing.

**C. My lines + the package's executed lines.** Tracing collects the line numbers that **executed**
during the run and keeps the ones belonging to the framework's package.

## Decision

**C.** Two numbers, both in the same unit — an executable line. Mine is counted by AST-parsing the
implementation module, the invisible one by tracing the run.

The limit is named outright in the lesson: the invisible number describes **this input**. A
different task will execute different lines, and that is a property of the measurement, not a defect
in it.

## Consequences

**Good.** "Less code" got its second half, and that half is measurable. The reader sees not "the
framework is big" but "on this task, this many lines I have never read work on my behalf".

**The price.** Tracing slows the run down. On a fake model it is imperceptible, and the NFR-2b
budget holds.

**The limit.** The number depends on the input and on the package version. Both dependencies are
named; comparing it against a neighbour's number obtained on a different task is not allowed.
