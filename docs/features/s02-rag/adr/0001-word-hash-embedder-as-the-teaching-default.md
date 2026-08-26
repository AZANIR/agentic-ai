---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-23"
feature_size: "S"
ticket: "n/a"
---

# 0001 — Use a word-hash embedder as the teaching default

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** Contributor, Tech Lead

## Context

The stage has to show that retrieval is arithmetic and sorting. That needs an embedder that works
**offline, deterministically and with no key**, because otherwise none of the stage's checks is
reproducible and the reader runs into a sign-up before their first run.

At the same time the teaching embedder must not be too good: if it finds everything, the reader
will not understand why one would ever move to real ones.

## Decision drivers

- The checks are offline and deterministic (repository ADR 0006); the course can be taken with no
  payment card.
- Transparent mechanics is quality goal №1: the reader has to see **why** this particular thing
  was found.
- The boundary has to be visible rather than described: the argument for real embeddings must be
  a conclusion the reader draws from their own run, not a claim by the author.
- Zero heavy dependencies in the base install.

## Considered options

1. **A hash over words** — every word gives a position in the vector, weighted by frequency. Finds
   things by a literal match; does not find synonyms at all.
2. **Character n-grams** — more robust to word forms and typos, which is noticeable for Ukrainian
   with its morphology. But harder to explain, and the boundary blurs.
3. **`fastembed` straight away** — real embeddings on the CPU, with no network after the model is
   downloaded. ~50 MB of model and a first download on the first run.

## Decision outcome

**Chosen:** Option 1. The deciding argument is not simplicity but **the visibility of the
boundary**. A hash over words gives exactly the behaviour the lesson has to show: a question in the
document's own words is found, the same question in synonyms is not. The reader sees the gap as a
number and draws the conclusion themselves.

Option 2 would make the search better and the lesson worse: partial n-gram matches blur the
boundary, and instead of a clear "synonyms are not found" you get "sometimes it finds them,
sometimes it does not" — from which no conclusion can be drawn.

Option 3 is right for production and available immediately through `[embed]` — but as **the
default** it would give a working search and zero understanding of what is inside.

## Consequences

**Positive**
- The checks are deterministic down to the last digit; the order of fragments is reproducible.
- Zero dependencies beyond NumPy; the course can be taken with no downloads.
- The "literal versus synonyms" gap becomes **a measurable metric** (spec §7) rather than a claim.

**Negative**
- The search is objectively bad. The lesson has to say so outright at the start, or the reader
  will decide that RAG does not work at all — and that is this stage's most likely wrong
  impression.
- Ukrainian morphology hits harder than English: "повернення" and "повернень" are different words
  to this embedder. That is lesson material too, but it has to be named.

**Neutral**
- Moving to `fastembed` or a provider is a swap of the adapter behind the same interface; the
  stage's code does not change (repository ADR 0002).

## Links

- Spec: [[../spec.md]] AC-01, AC-06, §7
- SAD: [[../sad.md]] §4, §10
- Repository ADR: [[../../../adr/0002-profile-switched-adapters]]
