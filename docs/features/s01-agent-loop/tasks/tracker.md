# Tracker — s01-agent-loop

> The status of every task in the epic. `implement` updates `done` as the commits land.
> States: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | A registry of three tools with schemas and an irreversibility flag | app | Contributor | S | — | done |
| T2 | Validate tool arguments against the declared schema | app | Contributor | S | — | done |
| T3 | The ReAct loop with tracing and a step limit | app | Contributor | M | T1, T2 | done |
| T4 | The confirmation gate on an irreversible action | app | Contributor | S | T3 | done |
| T5 | The demo: four scenarios in a row and a banner naming the source of answers | ports | Contributor | M | T3, T4 | done |
| T6 | Stage checks: happy paths and three failure modes | tests | Contributor | M | T3, T4 | done |
| T7 | The stage lesson: the article's canon, the bridge to NovaShop, "what to break" | docs | Contributor | M | T5, T6 | done |
| T8 | Exercises, reference solutions and the stage checklist | docs | Contributor | S | T7 | done |
| T9 | The stage's terms into the glossary, the stage's status into the curriculum | docs | Contributor | S | T7 | done |

**Total:** 9 tasks, ~6.5 person-days.

Parallel branches: T1 and T2 start at the same time (they share no files). T5 and T6 come after
T4, also in parallel. T8 and T9 come after T7, in parallel.
