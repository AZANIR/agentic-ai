---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0001 — A JSONL file, not a database and not process memory

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Long-term memory has to outlive the session. The question is where exactly it lives at a stage
that promises offline and no configuration.

## Considered options

1. **A JSONL file**, one record per line.
2. **Process memory** — a dictionary that lives between "sessions" within one run.
3. **SQLite** — a real database with no server.

## Decision outcome

**Chosen:** Option 1.

Option 2 is the first one out, and the reason is not durability. **Two sessions in one process
sharing a dictionary prove nothing**: the fact is "available" because it is the same object in
memory, not because it was written and read back. AC-02 demands the opposite — that the second
session read **what was written**.

Option 3 would give real persistence and take away the main thing: **memory would stop being
readable by eye**. The most useful thing the reader can do at this stage is open the file after
the demo and look at what ended up in it. A line of JSON is visible; a SQLite table means
`sqlite3` and one more tool.

JSONL gives both properties: the record really does cross the process boundary, and it is visible
with no tooling at all.

**The price is named:** the file will not survive concurrent writes, and there are no transactions
here. That is acceptable for exactly as long as the memory is local and single-user — that is,
until stage 6, where a service appears and Postgres with it. The interface will stay the same.

## Consequences

**Positive**
- The second session really does read what was written, rather than a shared object.
- Memory is readable by eye — the cheapest way to understand what the system remembered.
- Swapping in Postgres at stage 6 changes nothing but two functions.

**Negative**
- No transactions and no concurrent writes. Named as a boundary, not hidden.
- The file grows forever: `replaced` and expired records stay. That is deliberate — the history
  of a replacement is valuable in itself — but a cleanup will be needed one day, and it is not
  implemented here.
