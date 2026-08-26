---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
ticket: "n/a"
---

# 0006 — A scenario checks the branch AND the final state

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

Five end-to-end scenarios have to prove that the assembly works. The simplest way is to check the
**answer**: the text is right, so everything is fine.

This course has already shown why that is not enough. Stage 8 caught an agent that gave the right
answer by the wrong path; stage 6 caught a service that answered and **put a password into
memory**. In both cases the text was flawless.

Assembly adds a third reason: a part may fail to fire and the answer may still come out plausible
— because another part produced it.

## Decision Drivers

- A scenario has to catch "the text is right, the state is not".
- It has to name **which part** answered, not merely that an answer exists.
- A part failing is not the system falling over — that is the lesson of stage 4, and the scenario
  has to respect it.

## Considered Options

**A. Check the answer.** Misses both classes the course has already caught.

**B. Check the answer and the branch.** Better; leaves the state unattended.

**C. Check the branch **and** the final state: what is in memory, what is in the trace, what is on
the counters.**

## Decision

**C.** Each of the five scenarios pins the expected branch **and** the expected final state. One
scenario deliberately breaks a part: the service has to stay alive, and the answer has to name
what exactly failed.

## Consequences

**Good.** The scenarios catch what they exist for: not "something answered", but "exactly what
should have fired did fire, and the trail it left is right".

**The price.** A scenario is longer than an answer check and needs access to the state. State is
supplied from outside, so this is access rather than peeking.

**The limit.** Five scenarios are not coverage. The full case set lives at stage 8, and the
capstone **uses** it rather than repeating it.
