# Architecture of the assembled service

Every decision here has a **source stage**, and the citation is **verified by code** (`arch.py`).
A bibliography nobody checks ages silently — in this repository that has already happened twice,
and both times it was review that found it, not the author.

What the check asserts: the source **exists**. What it does not assert: that the source contains
this particular decision — that would take understanding the text. The first already catches the
whole class of errors that has occurred here.

## Decisions and their sources

| Decision | Source |
|---|---|
| Three gatekeepers: access, rate limit, budget — before any model call | s06 |
| Key comparison is constant in time | s06 |
| A refusal costs zero model calls | s06 |
| Metrics are split by kind; counters are supplied from outside | s06 |
| A Plan → Act → Observe → Decide loop with a step limit | s01 |
| A confirmation gate on irreversible actions | s01 · ADR-0002 |
| Tool arguments are validated before the call | s01 |
| The access filter is applied BEFORE retrieval, not after | s02 |
| The similarity threshold is named; below it, a refusal rather than an invention | s02 |
| The index is built once, at service start | s02 |
| The supervisor picks the branch; the name is checked against a registry | s03 · ADR-0004 |
| The revision loop has a counter, and the counter lives in the state | s03 |
| A six-question checklist decides what reaches memory | s05 |
| A secret is checked BEFORE the request to remember | s05 |
| A corrupted memory line is named and skipped, not overwritten | s05 |
| The trace writes the run key from the first line | s09 · ADR-0008 |
| Executed lines are measured by tracing, not by package size | s09 · ADR-0003 |
| Warm-up before measuring: the import is not part of the price of a run | s09 |
| The evaluator reads traces and gives three independent verdicts | s08 · ADR-0003 |
| "Unscored" is a third state, separate from a failure | s08 · ADR-0006 |
| The denominator of the ratio is every case, not only the scored ones | s08 |
| Latency numbers are printed with their conditions, and the conditions come BEFORE the number | s07 |
| Retrieved text reaches the model behind a data-block fence | s02 |
| The HTTP layer of the assembled service is stage 6's application, not a second one of its own | s06 |
| One VM, self-hosted, no managed services | s06 |
| A backup of the database volume; it holds no secrets | s06 |

## The capstone's own decisions

Decisions without a source stage are allowed — but they stand apart and name the reason there is
no source. Otherwise "there is a source" and "there is no source" would merge into one.

| Decision | Why there is no source |
|---|---|
| The branch is picked by a crude word heuristic rather than by the model | Stage 6's classifier calls the model, and the branch is needed BEFORE that call: retrieval has to deliver context in time. This is a new constraint that stage 6 did not have |
| The service's answer is called `Reply`, not `Answer` | Two different `Answer` classes already exist in the course (stages 2 and 6). A third would turn confusion into an error for no reason at all |
| Retrieval runs on EVERY request, even when the branch will not use it | It gives every branch context on equal terms and makes stage 2's contribution measurable. The price is one extra retrieval per request; it is named here rather than hidden |

## What assembly revealed

An empty section here would be the most suspicious possible outcome: nine modules designed
independently do not join perfectly.

- **Stage 6 imports stage 2 and executes zero of its lines.** `from stages.s02_rag.documents
  import PUBLIC` is an access-level constant that travels on as an argument. Retrieval, embeddings
  and the access filter never run at all. This measurement became the capstone's thesis:
  "imports" is not the same as "uses".
- **Stage 5 demands a `Situation` it does not fill in itself.** The checklist takes the properties
  already set ("a human classifies"), so stage 6 wrote a private `_looks_like`. The capstone
  refused to write a third classifier of the same thing and imported **a private name from another
  stage** — that smells, and that is exactly why it stands here rather than silently in the code.
- **Two different `Answer` classes.** Stages 2 and 6 both gave that name to their result, and the
  meanings differ. Neither of them is wrong on its own; the error appears exactly when they stand
  side by side.
- **`Memory` takes a path, not a store.** The architecture map called this an imprecision back at
  stage 6, and at stage 10 it has not gone anywhere: the factory is still on the outside.
- **Stage 1 distinguishes two reasons for stopping, the service wants one.** `stopped_by_limit`
  and `blocked_tools` are separate fields, and stage 1 is right to distinguish them. The
  translation costs an adapter, and that is the correct price.
- **Stage 4 was not wired in.** MCP tools need a running server; the service takes stage 1's
  tools. This is not a defect of stage 4 — it is the boundary of a scenario in which everything
  must work offline.
- **Stage 9's instrument has a trap that the capstone caught with its own run.** `sys.settrace` is
  global **per thread**, so seven nested tracing contexts overwrote one another, and six stages out
  of seven silently reported zero. The symptom was quiet and plausible: the table printed, the
  numbers were whole. Fixed with a single pass that splits paths after the measurement.
- **Stage 9 "worked" with one line, and that line was the instrument itself.** It sat among the
  parts and produced a non-zero number until a run over empty work produced the same one: tracing
  being switched off in the `finally` of its own counter. "Measures" is not the same as "uses",
  and the distance is exactly the same as between "imports" and "uses".
- **The price of assembly was counted in a different unit from what it was compared against.**
  Adapters statically, from the code; stages dynamically, from execution. The numerator said "is
  in the code", the denominator said "runs", and the numbers looked comparable. That is the very
  substitution the whole stage is written against — inside the stage's own measurement.
- **Stage 2's data-block fence did not reach the capstone.** The retrieved document was glued to
  the question with a blank line, so foreign text went to the model with no boundary. Stage 2 has
  `OPEN_DATA`/`CLOSE_DATA` for this and **checks** them; the capstone bypassed `build_prompt` and
  reopened the gap stage 2 had closed.
- **Stages 6 and 10 agree by shape, not by name.** `Reply` deliberately is not called `Answer`,
  yet it satisfies stage 6's `create_app` contract completely — which is why the second deploy
  cost zero adapters. One field was missing (`retry_after`), and it turned up not in the design but
  on the very first request, which failed with `AttributeError`.

## Operational wrapping and where it came from

| Item | Source |
|---|---|
| Key authentication | s06 |
| A rate limit per owner, not per service | s06 |
| A budget guard before the spend, not after | s06 |
| Metrics by request kind and by spend | s06 |
| Step tracing with a run key | s09 |
| Reverse proxy, TLS, redirects | s06 |
| A backup of the database volume | s06 |
| CI with no secrets, offline | s06 |

## Deliberately not wired in

| Part | Reason |
|---|---|
| Voice (stage 7) | Adds no new conclusion, adds a dependency measured in gigabytes and makes the stage impassable offline |
| MCP tools (stage 4) | Need a running server; the offline scenario does not allow it |
| Frameworks (stage 9) | Stage 9 here is an **instrument**, not a way of orchestrating. It stood among the parts for a long time and produced exactly one line; `measure(lambda: None)` produced the same one — tracing being switched off in the `finally` of its own counter. The instrument was measuring itself |

Zero executed lines for these parts is a **decision**, not an error. That is exactly why they sit
in a separate list and are not counted as parts of the assembly. The list is reconciled with the
code: `assemble.NOT_WIRED` and this table must name the same stages, and an empty list reddens the
suite — otherwise "zero by decision" and "zero by oversight" become one thing again.
