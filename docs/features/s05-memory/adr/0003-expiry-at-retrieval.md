---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0003 — Expiry is checked at retrieval, not by deleting on write

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Not every fact is eternal. "My name is Olena" never expires; "order ord_4471 is in transit right
now" expires within a week and after that becomes worse than nothing — because it sounds
confident.

The question: when exactly does a fact stop being in force.

## Considered options

1. **At retrieval:** the record stays, and retrieval skips it with a named reason.
2. **A scheduled cleanup:** a separate process deletes what has expired.
3. **Deletion on writing the next fact** on the same topic.

## Decision outcome

**Chosen:** Option 1.

Option 2 and Option 3 both **delete history**, and that costs more than it seems. The question
"why did the system think a month ago that the order was in transit" has no answer once the record
is deleted: there is no record, and it is unclear whether it was wrong or simply expired.

The main reason, though, is different and practical. **Time has to be supplied explicitly.** If
expiry is decided on write, "now" is taken from the system clock inside the logic — and a TTL
check passes at night and fails in the daytime. Checking at retrieval allows time to be passed as
a parameter and makes expiry **deterministic**: supply a time a day later, and see the fact
disappear from the results in the same second.

This is not cosmetics for the tests. It is the same property that makes a call reproducible at
stage 4: take a record from the trace, repeat it, get the same thing.

**The price is named:** the file grows forever. Expired and replaced records stay, and a cleanup
will be needed one day. At stage 6, where a real datastore appears, it becomes a query with a
`WHERE`; here it is deliberately absent.

## Consequences

**Positive**
- Time is supplied as a parameter — TTL checks are deterministic at any hour of the day.
- The history stays: it is visible that a fact **existed** and **when** it stopped being in force.
- Expiry is visible as a reason in the trace, rather than as a silent disappearance.

**Negative**
- The file grows without bound. The cleanup is not implemented and is named as debt.
- Every retrieval checks the TTL of every record. On thousands of facts that will become
  noticeable — and that is exactly when it makes sense to move to a datastore with an index, which
  is to say to stage 6.
