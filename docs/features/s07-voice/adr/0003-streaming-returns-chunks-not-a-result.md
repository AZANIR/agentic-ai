---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0003 — The streaming pipeline returns chunks — and the type shows it

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The batch pipeline returns an answer. The streaming one could return **the same thing**, just
starting work sooner — and the difference would stay an implementation detail.

Then the reader sees two numbers and does not see **why** they differ.

## Decision drivers

- The difference between the pipelines is not in how fast they work but in **the moment of first
  delivery**.
- AC-02b requires showing that the total duration did not change. If both pipelines return the
  same type, that claim has nothing holding it up.
- A type is the cheapest documentation: it does not drift from the code.

## Considered options

1. **Streaming returns a generator of chunks**; batch — a finished result.
2. **Both return a result**, streaming is simply faster inside.
3. **Both return a generator**; batch yields a single element.

## Decision outcome

**Chosen:** Option 1.

Option 2 hides the difference. The reader sees two numbers and has to believe the explanation;
not one line of code confirms it.

Option 3 is symmetric and untrue: the batch pipeline **cannot** deliver earlier, and pretending
it can means erasing exactly what the stage is showing.

**The asymmetry of the types is the lesson.** A function that returns `Answer` has no way to hand
back half of it. A function that returns `Iterator[Chunk]` has no way to hide that it delivers in
parts. A difference visible in the signature needs no comment.

## Consequences

**Positive**
- The reader sees the reason for the difference in the code, not only in the numbers.
- Live mode's socket takes the generator and sends the chunks with no translation.
- AC-02b is checked literally: both pipelines are driven to the end and compared.

**Negative**
- Two different types mean two different call paths, and in `pipeline.py` both have to stay
  readable within the line budget.
- An error inside the generator surfaces later than in batch — and that has to be handled
  separately, because some of the audio has already been delivered.
