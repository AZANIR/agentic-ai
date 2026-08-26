---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0002 — A contradiction is decided by a fact's topic, not by its content

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

A person gave an address. A month later they gave a different one. Two active addresses must not
be left in memory — otherwise the system will answer one way or the other depending on which fact
won on proximity.

The question: how to tell that a new fact **replaces** an old one rather than adding to it.

## Considered options

1. **By topic:** a fact carries a "what it is about" field, and a new fact on the same topic
   replaces the old one.
2. **By content:** compare the texts and decide whether they contradict.
3. **Do not decide:** store both, sort it out at retrieval.

## Decision outcome

**Chosen:** Option 1.

Option 3 moves the problem to where it is harder to see. Two active facts about the address will
end up in the context together, and the model will get contradictory data with no marker at all.
It will answer something — and the answer will be plausible.

Option 2 looks smarter and drags in exactly what the stage avoids: **comparing content requires
inference**. Either a second model, or rules that will themselves become a debugging subject. At a
stage about memory that would replace the lesson's subject.

Topic is a blunt instrument, and that is precisely what makes it honest: it makes exactly one
statement — "this is a fact about the same thing". Whoever sets the topic answers for the
consequences.

**The boundary is named plainly:** two facts about **different things** that in truth contradict
("I live in Kyiv" / "I moved to Lviv" with different topics) will not be noticed. Detecting
contradictions by content is a separate problem with a separate price, and pretending the stage
solves it would be worse than an honest gap.

## Consequences

**Positive**
- A state with two active truths does not exist — that is a property, not a wish.
- The replacement is visible: the old record stays, with its status and the time of replacement.
- No inference: the rule is checkable in three lines.

**Negative**
- The topic has to be right. A mistake in the topic means either a lost replacement or a false one.
- Contradictions across different topics go undetected. Named in the test plan.
