---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0004 — The owner is a field of the record; the filter sits before the top-k selection

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Memory stores what a person said about themselves. This is the third place a leak can happen in
the course — after documents (stage 2) and tool descriptions (stage 4), and the most sensitive of
the three.

## Decision drivers

- The lesson of stage 2: a filter **after** the top-k selection produces no leak, but quietly
  takes away your own answer.
- The lesson of stage 3: the access level is a fact about the asker, not an argument somebody
  picks.
- The lesson of stages 2–4: a "somebody else's did not get through" check stays green when
  **nothing** got through.

## Considered options

1. **A field of the record + a filter before the selection**, with the owner supplied by the
   system.
2. **An argument of the retrieval** — whoever asks passes the owner.
3. **A separate file per owner** — isolation by directory structure.

## Decision outcome

**Chosen:** Option 1.

Option 2 works right up until somebody forgets the line. Forgetting is cheap, the consequence is
silent, and this has already happened in the course literally: at stage 3 removing the access
level binding produced no leak — it **took access away from someone who was allowed it**, and no
leak check could see that.

Option 3 looks the most reliable and hides the same trap somewhere else: the file path is built
from the owner's identifier, and now that identifier has to be safe as part of a path. Instead of
one field check you get path validation.

**The order of the filter is not a detail.** The filter sits **before** the top-k selection for
exactly the same reason as at stage 2: if it comes after, somebody else's fact takes a slot in the
results, then gets removed — and your own fact, which should have arrived, disappears. There is no
leak; the answer has disappeared.

So there are two checks, and the second is the more important: **somebody else's did not arrive**
and **your own did**.

## Consequences

**Positive**
- The owner cannot be forgotten: it is in the record, not in an argument.
- The order of the filter is pinned by a check that goes red on exactly that transposition.
- The model does not see the owner and cannot name it.

**Negative**
- Every retrieval reads every record in the file, other people's included, and filters in memory.
  At stage 6 that becomes `WHERE owner = ...`; here it is accepted deliberately — an index in
  JSONL would be make-believe.
- One process sees the whole file. Real isolation is the datastore's level, and it arrives
  together with the datastore.
