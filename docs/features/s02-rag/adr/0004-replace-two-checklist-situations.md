---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-23"
feature_size: "S"
ticket: "n/a"
---

# 0004 — Replace two checklist situations and the third verdict

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** Contributor, Tech Lead
- **Amends:** spec.md AC-07

## Context

AC-07 names six situations — changing data, the need to cite, **not enough examples**, an
inconsistent tone, **a narrow high-volume task**, none of the above — and three verdicts: RAG,
fine-tuning, **"start with RAG"**.

The implementation (`decision.py`) diverged from that list: instead of "not enough examples" and
"a narrow high-volume task" it has **differing access levels** and **a volume larger than the
context window**, and the third verdict is **"just a prompt"** instead of "start with RAG". The
divergence was found by an independent review; it was **silent**, which the repository's rules do
not allow.

This ADR does not legalise a silent substitution after the fact — it records the decision and the
reasons, after which the spec is brought into line.

## Decision drivers

- The checklist has to rest on signals **the reader of this stage has already seen in the code**.
- A verdict has to be an action, not advice in the conditional mood.
- The spec and the implementation must not diverge; a divergence is closed in one direction,
  explicitly.

## Considered options

1. **Restore the spec's list word for word** — six situations and "start with RAG".
2. **Change the spec to match the implementation** — record the substitution as a deliberate
   decision.
3. **Merge them** — seven or eight situations, both sets.

## Decision outcome

**Chosen:** Option 2 — with three amendments to the spec: two situation replacements and **a
seventh situation**.

The seventh appeared through that same composition check. There are six rules, and there were six
situations, one of which is "no signal fired". So one rule (`domain_language`, the language of the
subject domain) was switched on by no situation at all: a typo in the signal's name would have
stayed unnoticed for ever. There are now seven situations: one per rule plus the empty one.

**Why "differing access levels" instead of "not enough examples".** The access level is the
central mechanism of this very stage: ADR-0002, a check of its own, a demo scene of its own, the
most important exercise. The reader arrives at the checklist already knowing that a fine-tuned
model cannot forget part of itself for one particular interlocutor. "Not enough examples" is a
fine-tuning signal that the stage shows with nothing at all, so in the checklist it would remain a
word with nothing under it.

**Why "a volume larger than the window" instead of "a narrow high-volume task".** A narrow
high-volume task is a signal about **cost**, not about the nature of the problem; an honest answer
to it needs a calculation (how many requests, how often the data changes) that stage 2 does not
provide. Volume against the context window is a signal you can see straight away and without a
calculator.

**Why "just a prompt" instead of "start with RAG".** "Start with RAG" is not a verdict but advice
not to decide. It is systematically biased on top of that: it recommends building infrastructure
where the material could simply have fitted into the prompt. The cheapest solution is skipped most
often precisely because it does not look like a solution — and a checklist that does not name it
entrenches that flaw.

Option 1 falls: restoring the literal list would mean teaching signals the stage never showed.
Option 3 — eight situations instead of six make the checklist longer than the problem it solves.

## Consequences

**Positive**
- Every signal in the checklist has support in code the reader of this stage has already seen.
- The third verdict names the cheapest solution outright rather than proposing to start with the
  more expensive one.
- The spec and the implementation match again, and the match is nailed down by a composition check.

**Negative**
- Two fine-tuning topics — not enough examples and the cost of a narrow task — drop out of the
  course entirely. Recorded in SAD §11 as a gap with an address: the stage where cost measurement
  appears.
- The divergence lived for three commits and was found by the review, not by the author. The
  checklist composition check (the names of the situations and the presence of all three verdicts)
  was added for exactly that reason: the previous check reconciled `decide()` against a fixture in
  the same module and stayed green even if all six situations were replaced by identical clones.
