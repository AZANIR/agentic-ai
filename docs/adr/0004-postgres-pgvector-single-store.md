---
status: Accepted
owner: "Repository owner"
reviewers: []
updated_at: "2026-08-22"
feature_size: "n/a (foundational decision for the repository)"
ticket: "n/a"
---

# 0004 — Keep relational data and vectors in one Postgres with pgvector

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** repository owner

## Context

The course needs two kinds of persistence: relational (NovaShop orders, user memory facts,
sessions) and vector (the RAG documents from stage 2, the semantic memory from stage 5). The
target deployment is **one VM with about 4 GB of RAM**, which also has to hold the application,
Redis, Caddy and optionally Prometheus, Grafana and Langfuse.

## Decision drivers

- One VM with a hard memory ceiling (map: Constraints).
- The platform stage already assumes Postgres — adding another service without need contradicts
  its own "boring on purpose" thesis.
- Every additional service is another backup, another process to monitor and another way for the
  deployment to fail on the reader at stage 6.
- The course's data volumes are tiny: dozens of documents, hundreds of facts.

## Considered options

1. **Postgres 16 plus the `pgvector` extension** — one database for both jobs.
2. **Postgres plus a dedicated vector service** (Qdrant or Chroma) — faster vector search,
   specialised features.
3. **SQLite plus FAISS in a file** — zero services, but unfit for concurrent access from several
   processes, and stage 6 deliberately starts two workers.

## Decision outcome

**Chosen:** Option 1. At the course's volumes the speed difference between `pgvector` and Qdrant
is imperceptible, while the difference in operational cost — one service against two — is
apparent on the very first deployment. Option 3 is ruled out by stage 6: demonstrating the
multi-worker trap requires a store that behaves correctly across processes.

## Consequences

**Positive**
- One backup, one connection string, one service in `docker compose`.
- Transactional integrity between a memory fact and its vector — they are in the same database.
- The `core` profile fits into about 2 GB of RAM.

**Negative**
- `pgvector` loses to specialised stores at millions of vectors. Irrelevant for the course, but
  the reader has to know the boundary — it is written into the stage 2 lesson.
- The Postgres image needs the extension (`pgvector/pgvector:pg16`), so not the plain official
  image.

**Neutral**
- Moving vectors into a separate service later needs **no change to stage code** — the
  `shared/stores/vector` interface stays, only the implementation changes (ADR-0002).

## Links

- Spec: [[../../planning/2026-08-22-agentic-ai-course-design.md]] §7, §8.1
- Architecture map: [[../architecture-map.md]] §Datastores
- Related ADRs: [[0002-profile-switched-adapters]]
