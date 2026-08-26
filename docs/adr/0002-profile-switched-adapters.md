---
status: Accepted
owner: "Repository owner"
reviewers: []
updated_at: "2026-08-22"
feature_size: "n/a (foundational decision for the repository)"
ticket: "n/a"
---

# 0002 — Switch environments with adapters behind APP_PROFILE, not with separate codebases

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** repository owner

## Context

The repository has to live in two modes at once: teaching (everything local, free,
deterministic, no API key) and production (the same code on a VM behind HTTPS, with a real LLM,
Postgres, Redis and metrics). Those are two very different sets of dependencies and behaviours
for one and the same logic.

## Decision drivers

- A reader must get through the whole course without a payment card (map: Constraints).
- The same code has to carry real traffic — otherwise the reader learns on code nobody deployed.
- Checks have to be deterministic and offline (spec §5.3).
- The difference between modes must not leak into lesson code — otherwise the lesson stops being
  about agents and becomes about configuration.

## Considered options

1. **One codebase plus an adapter layer chosen by `APP_PROFILE=local|prod`** — stores, LLM,
   embeddings and tracing each have two implementations behind a shared interface.
2. **Two codebases (or two branches)** — a "teaching" one and a "production" one.
3. **Production mode only** — the reader brings up Postgres and pays for an LLM on day one.

## Decision outcome

**Chosen:** Option 1. Option 2 diverges within a fortnight: a fix in one branch does not reach
the other, and the teaching code stops matching what is actually deployed — which destroys the
repository's central promise. Option 3 loses most of the audience at stage 1.

The constraint that makes this decision work: `if PROFILE == ...` is **forbidden** in stage code.
The branching lives in exactly one place, the adapter factory in `shared/`.

## Consequences

**Positive**
- `scripts/check_all.py` passes offline, with no key, in seconds — and checks **the same** code
  that runs in production.
- The reader sees domain logic in lesson code, not configuration.
- Adding a third profile (say `staging`) is a new branch in the factory, not a new codebase.

**Negative**
- Every store has to be written twice: in-memory and Postgres/Redis. That is genuine double work.
- The adapter interface has to be designed before it is obvious what it should be — and a mistake
  in it is expensive to fix later.
- It is easy to leak profile-specific behaviour by accident (relying on dict key order, which SQL
  does not guarantee). Mitigated by stages 6 and 10 running their checks against both profiles.

**Neutral**
- Nobody cares about the performance of the in-memory implementations — they exist for
  determinism, not speed.

## Links

- Spec: [[../../planning/2026-08-22-agentic-ai-course-design.md]] §5.1
- Architecture map: [[../architecture-map.md]] §Conventions
- Related ADRs: [[0003-openai-compatible-llm-shim]], [[0004-postgres-pgvector-single-store]], [[0006-assert-checks-over-test-framework]]
