# Tracker — s02-rag

> States: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | An embeddings adapter in the shared layer: hash / fastembed / openai | infra | Contributor | S | — | done |
| T2 | Splitting documents into fragments | domain | Contributor | S | — | done |
| T3 | The NovaShop knowledge base with access-level metadata | domain | Contributor | S | — | done |
| T4 | Index, cosine, top-k, threshold and the access filter | app | Contributor | M | T1, T2, T3 | done |
| T5 | Composing an answer with a source the system attaches | app | Contributor | S | T4 | done |
| T6 | The search tool for the stage 1 agent's registry | ports | Contributor | S | T4, T5 | done |
| T7 | The demo: search, threshold, chunking and the access filter side by side | ports | Contributor | M | T5, T6 | done |
| T8 | The stage checks following the coverage table | tests | Contributor | M | T4, T5, T6, T7 | done |
| T9 | DECISION.md — the "RAG or fine-tuning" checklist | docs | Contributor | S | — | done |
| T10 | The stage lesson: the canon, the bridge to NovaShop, the boundaries | docs | Contributor | M | T7, T8, T9 | done |
| T11 | Exercises, reference solutions and the checklist | docs | Contributor | S | T10 | done |
| T12 | The stage's terms into the glossary, the status into the curriculum | docs | Contributor | S | T10 | done |

**Total:** 12 tasks, ~8 person-days.

Parallel branches: T1, T2, T3 and T9 start at the same time. T5 and T6 come after T4.
T10 → T11 and T12 in parallel.
