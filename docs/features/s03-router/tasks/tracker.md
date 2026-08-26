# Tracker — s03-router

> States: `todo` · `in_progress` · `blocked` · `review` · `done`.

| # | Task | Layer | Owner | Estimate | Blocked by | Status |
|---|---|---|---|---|---|---|
| T1 | The state schema as a declared contract | domain | Contributor | S | — | done |
| T2 | Three specialists with competence descriptions | domain | Contributor | S | T1 | done |
| T3 | The graph: supervisor, route, revision loop | app | Contributor | S | T1, T2 | done |
| T4 | Access rights survive the handoff — three checks | tests | Contributor | S | T3 | done |
| T5 | The "do you need a supervisor" checklist in code and prose | domain | Contributor | S | — | done |
| T6 | The same task on LangGraph | infra | Contributor | S | T3 | done |
| T7 | Demo: routes, limit, refusal, rights | ports | Contributor | S | T3, T5 | done |
| T8 | Checks up to full coverage of the table | tests | Contributor | S | T3, T5, T6, T7 | done |
| T9 | The lesson in Ukrainian and an English map | docs | Contributor | S | T7, T8 | done |
| T10 | Exercises, solutions, checklist | docs | Contributor | S | T8, T9 | done |
| T11 | Glossary and statuses | docs | Contributor | S | T9 | done |
