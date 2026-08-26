---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-23"
feature_size: "S"
ticket: "n/a"
---

# 0003 — Attach the source with the system rather than asking the model to cite

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** Contributor, Tech Lead

## Context

AC-02 requires every answer issued to name the document it was assembled from. The question is not
whether to cite but **who does it**: the model, following an instruction in the prompt, or the
system, from the list of fragments it found itself.

## Decision drivers

- Quality goal №2: an ungrounded answer must not exist as a state, not "must happen rarely".
- The check has to assert a property, not observe a frequency.
- The pattern is inherited by stage 10, where a real client stands behind the answer.

## Considered options

1. **The system attaches the source** from the list of fragments found, after generation.
2. **The model cites on instruction** — the prompt tells it to name the source.
3. **The model cites, the system verifies** — the generated citation is reconciled against the
   list of what was found and the answer is rejected if it does not match.

## Decision outcome

**Chosen:** Option 1.

Option 2 falls for one reason: **an invented reference looks exactly like a real one**. A model
asked to cite will sometimes name a document that was not in the results — and a system that
trusts it will hand that to the user. That is, the citation introduced precisely to tell a
grounded answer from an invented one itself becomes invented.

Option 3 removes that flaw and costs an extra round trip: when the reconciliation does not match,
the answer has to be regenerated. At stage 2 that is complexity with no new lesson in it. It
becomes appropriate where the citation has to point at a specific sentence rather than at a
document — and that is a topic for later.

The consequence of option 1 is worth naming outright: **the source is guaranteed to exist, but it
does not guarantee that the answer actually follows from it.** The model received the fragment and
could have answered right past it. The lesson has to say so: stage 2 closes "there is a source",
while "the answer matches the source" is a question of measurement, that is, stage 8.

## Consequences

**Positive**
- 100% of answers carry a source **by construction**, not by observation.
- The check asserts the property in three lines, with no LLM judge.
- It is impossible to get a reference to a document that was not in the results.

**Negative**
- The source may not match the content of the answer, if the model answered past the fragment it
  was given. That is a real boundary, and the lesson names it outright.
- The citation format is fixed by the system — the model cannot weave a reference into the text
  naturally.

**Neutral**
- Moving to option 3 means adding a reconciliation after generation; the interface does not change.

## Links

- Spec: [[../spec.md]] AC-02, AC-04, §7
- SAD: [[../sad.md]] §4, §8, §11
- Related ADRs: [[0002-filter-by-access-level-before-top-k]]
