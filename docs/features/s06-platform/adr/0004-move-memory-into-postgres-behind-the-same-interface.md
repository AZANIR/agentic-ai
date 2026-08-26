---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0004 — Move memory into Postgres behind the same interface

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Stage 5 keeps facts in a JSONL file and promises outright: "stage 6 will replace the store behind
the same interface — and that is exactly why the interface here is narrow".

The moment to test that promise has come. If the move requires editing `long_term.py`, then the
interface was not narrow, and stage 5's promise was decoration.

## Decision drivers

- A file does not survive two processes: two simultaneous writes lose data.
- AC-10 requires memory to survive a container restart.
- C-1 forbids editing stages 1–5.
- A promise made at an earlier stage is a debt, not a wish.

## Considered options

1. **A second implementation with the same methods**, chosen by the factory in `shared/`; stage 5
   and its checks stay untouched and go on working with the file.
2. **A file on a mounted volume** — survives a restart, does not survive two processes.
3. **Rewrite `long_term.py`** for the database.
4. **Extract the interface into a `Protocol`** and teach `Memory` to accept a store — that is, an
   edit to stage 5.

## Decision outcome

**Chosen:** Option 1.

Option 2 satisfies AC-10 literally and leaves the data loss with two workers in place — that is,
the very trap the stage warns about in two other places.

Option 3 breaks C-1 and devalues stage 5: if the interface has to be rewritten, the reader is
entitled to ask why it was ever called narrow.

Option 4 is the cleanest engineering and is rejected deliberately: it edits stage 5, which breaks
C-1, and it does so for a property stage 5 does not use.

**Stage 5's promise is half kept, and that is recorded here rather than passed over in silence.**
Stage 5 wrote: "stage 6 will replace the store behind the same interface — and that is exactly why
the interface here is narrow". What turned out to be narrow was the **set of methods**:
`all_facts`, `remember`, `context_for` — that really is enough to write a second implementation and
drop it into the service.

But `Memory` is a concrete class that takes a `Path`, not a store; its checks build
`Memory(Path(tmp) / "memory.jsonl")` directly. Which means **substituting the implementation inside
stage 5 without editing it is impossible**, and the phrase "behind the same interface" was more
precise than the code that backs it up.

So stage 5's checks stay with the file, and the contract shared by the two implementations is
asserted by **stage 6**: one set of assertions, run against both stores. That is weaker than the
promise, and more honest than it.

## Consequences

**Positive**
- Stage 5 and its 42 checks do not change by a single line.
- Memory survives both a restart and a second worker.
- The owner filter becomes a `WHERE`, which means it stops reading other people's records (the debt
  from stage 5's ADR-0004).

**Negative**
- Two store implementations are two behaviours. The contract is asserted by stage 6, and stage 6 is
  what goes red when they diverge.
- Stage 5's promise is half kept, and its lesson will have to be made precise: a narrow **set of
  methods** is not the same thing as a swappable store.
- Postgres becomes mandatory for the `prod` profile and unavailable to some of the checks offline:
  those are marked `NOT EVALUATED` rather than skipped silently.
