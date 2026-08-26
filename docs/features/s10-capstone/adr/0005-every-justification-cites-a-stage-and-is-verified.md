---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
ticket: "n/a"
---

# 0005 — Every justification has a source stage, and code verifies it

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The capstone's `ARCHITECTURE.md` has to justify every decision by citing a source stage. That is
how the course design specification states it.

The problem is known and has already happened twice **in this very repository**. The message about
`TRACE_SINK` cited a stage 6 ADR that had made no such decision, and it lived that way until
review. Stage 8's ADR-0008 table contradicted its own measurement block in the same file.

Both times the text was plausible, nobody executed it, and it aged silently.

## Decision Drivers

- A bibliography nobody checks is decoration.
- A decision **without** a source also has a right to exist, but not the right to look like a
  decision with one.
- The check has to catch a dangling citation, not the presence of the word "stage".

## Considered Options

**A. Just write the citation.** Ages silently, as it has twice already.

**B. Review reads and reconciles it by hand.** Works once, on review day.

**C. Parse the document with code: every decision has a source, and every source exists.**

## Decision

**C.** `arch.py` parses `ARCHITECTURE.md` and asserts two things:

1. **Every** decision has a source stage, or stands in the section "the capstone's own decisions".
2. **Every** named stage and every named ADR exists in the repository.

An own decision is allowed and requires a reason for why there is no source stage.

## Consequences

**Good.** The document stopped ageing silently. A renamed ADR or a deleted stage reddens the check
the same day.

**The price.** The document's format is fixed: the parser demands a recognisable row. The freedom
of the prose is constrained exactly where it would have cost truthfulness.

**The limit.** The check asserts that the source **exists**, not that it really contains this
decision. The second is impossible without understanding the text; the first already catches the
whole class of errors that has occurred here.
