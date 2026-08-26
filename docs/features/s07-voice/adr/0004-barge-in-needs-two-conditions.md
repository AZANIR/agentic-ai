---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0004 — Barge-in is decided by two conditions — level and duration

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Interrupting by level is one line: louder than the threshold, therefore a person is speaking.

Such a detector interrupts the answer on a cough, on keystrokes and on a mouse click. The
conversation turns into a monologue that keeps breaking off.

Interrupting by duration is one line too, and it interrupts on the sustained noise of an air
conditioner.

## Decision drivers

- A false interrupt is worse than a missed one: the agent falls silent mid-sentence for no reason.
- A missed interrupt is bad too: the person says "stop", the agent keeps talking.
- Both conditions are **numbers**, and the reader has to see which one fired.
- A spectral VAD solves this better and drags in a separate dependency and a separate discipline.

## Considered options

1. **Two conditions: level above the threshold AND duration above the minimum.**
2. **Level only.**
3. **A spectral VAD** from a library.

## Decision outcome

**Chosen:** Option 1.

Option 2 gives a detector that interrupts on any loud sound. That is the same class as a
guard that lets everyone through: the rule exists, and it decides nothing.

Option 3 is right for production and wrong for a lesson: it hides the decision inside somebody
else's library, and the reader sees **not a single** number.

**Three checks, not one.** Noise does not interrupt; short speech does not interrupt; long speech
does interrupt. The first two look redundant exactly until somebody removes one of the conditions
— then one of them goes red.

**The limit is named:** 100 ms and 300 ms are the **exercise's** numbers, not production
settings. The real threshold depends on the microphone, the room and the language.

## Consequences

**Positive**
- The reader sees both numbers and can play with them.
- Each condition has a check of its own, so removing it silently is impossible.
- Zero dependencies.

**Negative**
- The detector is naive: sustained loud music will interrupt the answer. Named in the lesson.
- The thresholds will have to be tuned for every microphone, and the stage does not automate that.
