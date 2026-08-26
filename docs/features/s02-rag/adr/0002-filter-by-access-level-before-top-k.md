---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-23"
feature_size: "S"
ticket: "n/a"
---

# 0002 — Filter by access level before the top-k selection, inside the search

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** Contributor, Tech Lead

## Context

The knowledge base holds documents at different access levels: policies for shoppers and internal
instructions. Search by closeness knows nothing about access levels — it will return whatever is
closer in meaning, the internal document included.

This is the most typical production leak in RAG systems, and showing it on ten documents is
cheaper than explaining it at stage 6 behind a public endpoint.

## Decision drivers

- The abuse case "an internal document in a shopper's answer" (spec §6.1) has to be closed by a
  mechanism, not by discipline.
- The pattern is inherited by stages 6 and 10, where a public endpoint stands in front of the
  search.
- The reader has to see that **the order** of filtering changes the consequence.

## Considered options

1. **The filter inside the search, before the top-k selection** — the access level is a parameter
   of the search.
2. **The filter inside the search, after the top-k selection** — pick the best five, then remove
   the forbidden ones.
3. **The filter at the caller** — the search returns everything, each consumer filters for itself.

## Decision outcome

**Chosen:** Option 1.

Option 3 falls first: a guard that every caller has to remember is an agreement, not a line of
trust. We drew the same conclusion at stage 1 about `additionalProperties`, and there it cost us
a review finding.

Option 2 looks equivalent and is not. The difference is subtle and important:

| | filter after the selection | filter before the selection |
|---|---|---|
| an internal document in the answer | no | no |
| **a permitted document in the results** | **could have vanished** — an internal one displaced it | stays |

Both variants pass the check "the internal thing did not leak". But with the filter applied
**after** the selection, an internal document takes a slot in the top five, is then removed — and
the Shopper gets **a worse answer** with no way at all of noticing. There is no leak, quality
quietly dropped.

That is why the check asserts **both** properties: the internal thing did not leak **and** the
permitted thing did not disappear. Either one without the other lets option 2 through.

## Consequences

**Positive**
- The caller cannot forget the filter — it is not in the caller's area of responsibility.
- The quality of the results does not depend on how many internal documents happened to be close
  in meaning.
- The mechanism carries over to stage 6 with no rework: what changes is the source of the access
  level, not the place of the filter.

**Negative**
- The search gains one more parameter and cannot be called "just like that" — you have to state
  each time whose behalf you are searching on. That friction is deliberate.
- The search module grows: it already holds the cosine, the top-k, the threshold and the filter.
  The §10 limit is 80 lines; if it is exceeded, the filter moves out into its own module (SAD §11).

**Neutral**
- A hierarchy of levels (internal ⊃ partner ⊃ public) is not needed at this stage: two levels are
  enough to show the mechanism.

## Links

- Spec: [[../spec.md]] AC-05, §6.1
- SAD: [[../sad.md]] §4, §6 (flow 1), §8
- Related ADRs: [[0003-system-attaches-the-source]]
