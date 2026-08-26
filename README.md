# Agentic AI: From Zero to Production

A ten-stage hands-on course in building agentic systems. Not a survey — a repository where
every idea has to be **built, broken, and measured**, and where a claim that cannot be checked
by running something does not get made.

Every stage ships with [an article](docs/readme.md), and the numbers in it are recomputed
against the code at that stage's tag rather than typed by hand.

[Curriculum](CURRICULUM.md) · [Setup](SETUP.md) · [Glossary](GLOSSARY.md) · [Playbook](PLAYBOOK.md)

---

## What this is

Two things at once, out of one codebase:

- **A course.** Ten self-contained stages. Everything runs locally, offline, free and
  deterministically — no payment card is needed anywhere.
- **A deployable service.** The same code, at stages 6 and 10, goes out to a real VM behind
  HTTPS with Postgres, Redis, metrics, tracing and a budget breaker.

`APP_PROFILE` holds the difference: it switches adapters, not branches in the code
([ADR-0002](docs/adr/0002-profile-switched-adapters.md)). What you learn is literally what
later runs under load.

## Who it is for

You can write a Python function and run a script. You do not know what an embedding, a tool
call, a state graph, MCP, barge-in or LLM-as-judge is — which is exactly why this exists.

**The promise:** after every stage you have something working that you ran yourself, and you
can explain **in words** why it is built that way.

## How the course is shaped

```
Act I    · stages 1–5  · BUILD       each stage gives the agent one new capability
Act II   · stage  6    · JOIN        blocks 1–5 become one deployed service
Act III  · stages 7–9  · CHECK       latency, measurement, choosing a tool
Finale   · stage  10   · REASSEMBLE  cleanly, with every decision justified
```

Stages 7–9 add no features. They exist so you stop lying to yourself.

| # | Stage | What you build | Article |
|---|-------|----------------|---------|
| 1 | [Agent loop](stages/s01_agent_loop/README.md) | A ReAct loop from scratch, no framework | [#1](https://artstroy.net/articles/three_guards_every_agent_loop_needs) |
| 2 | [RAG](stages/s02_rag/README.md) | embed → cosine → top-k → an answer with a citation | [#2](https://artstroy.net/articles/your_rag_leak_test_is_green) |
| 3 | [Router](stages/s03_router/README.md) | Your own mini-graph, then LangGraph | [#3](https://artstroy.net/articles/the_bug_that_breaks_nothing) |
| 4 | [MCP](stages/s04_mcp/README.md) | A FastMCP server and client | [#4](https://artstroy.net/articles/the_tool_description_you_did_not_write) |
| 5 | [Memory](stages/s05_memory/README.md) | extract → store → retrieve, with semantic search | [#5](https://artstroy.net/articles/nothing_leaked_the_answer_disappeared) |
| 6 | [Platform](stages/s06_platform/README.md) | **First deploy:** FastAPI + HTTPS + metrics | [#6](https://artstroy.net/articles/the_bugs_only_deploying_finds) |
| 7 | [Voice](stages/s07_voice/README.md) | Batch against streaming, barge-in, measurement | [#7](https://artstroy.net/articles/your_streaming_benchmark_measures_two_things) |
| 8 | [Evaluation](stages/s08_eval/README.md) | Three levels of judgement over traces | [#8](https://artstroy.net/articles/the_detector_that_always_finds_it) |
| 9 | [Frameworks](stages/s09_frameworks/README.md) | One task, four implementations | [#9](https://artstroy.net/articles/less_code_is_half_an_argument) |
| 10 | [Capstone](stages/s10_capstone/README.md) | **Second deploy:** everything together, measured | [#10](https://artstroy.net/articles/your_import_list_is_not_proof) |

More detail in [CURRICULUM.md](CURRICULUM.md).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # the quotes matter — without them the shell eats the brackets
cp .env.example .env             # nothing in it needs changing
python scripts/check_all.py      # must be green, offline, with no keys
```

If that last line is green, you are ready. The long version: [SETUP.md](SETUP.md).

## Status

**All ten stages are finished.** The service deploys behind HTTPS, and stage 10's assembled
service is served by stage 6's application with no HTTP layer of its own.

| Component | State |
|---|---|
| `shared/` — config, LLM shim, FakeLLM, tracing | done, 19 checks |
| `scripts/check_all.py`, `scripts/migrate.py` | done |
| `deploy/docker-compose.yml` — Postgres+pgvector, Redis | done |
| CI (ruff + checks, no secrets) | done |
| Stage 1 — agent loop | **done**, 30 checks, passed an independent review |
| Stage 2 — RAG | **done**, 49 checks, 24 of them on failure modes |
| Stage 3 — router | **done**, 38 checks, 20 of them on failure modes |
| Stage 4 — MCP | **done**, 36 checks, 21 of them on failure modes |
| Stage 5 — memory | **done**, 42 checks, 27 of them on failure modes |
| Stage 6 — platform | **done**, 69 checks, 57 of them on failure modes; smoke against live HTTPS |
| Stage 7 — voice | **done**, 44 checks, 37 of them on failure modes; 1574 → 450 ms |
| Stage 8 — evaluation | **done**, 31 checks, 15 of them on failure modes; position bias 3 of 3, mirrored 0 of 3 |
| Stage 9 — frameworks | **done**, 28 checks, 12 of them on failure modes; baseline 37 lines against 54 + 1895 invisible |
| Stage 10 — capstone | **done**, 32 checks, 16 of them on failure modes; 6 parts execute and 3 are deliberately not wired, 173 executed stage lines against 12 adapter lines (7 %) |

## Where to look

| Document | About |
|---|---|
| [CURRICULUM.md](CURRICULUM.md) | The programme: each stage's goal, time, dependencies, status |
| [SETUP.md](SETUP.md) | Installation, choosing an LLM provider, the usual traps |
| [GLOSSARY.md](GLOSSARY.md) | Terms, one entry per idea the course actually uses |
| [CONVENTIONS.md](CONVENTIONS.md) | The repository's code rules |
| [PLAYBOOK.md](PLAYBOOK.md) | How a stage gets made: the pipeline, the review gate, lessons already paid for |
| [SECURITY.md](SECURITY.md) | The threat model of a public endpoint |
| [docs/architecture-map.md](docs/architecture-map.md) | Architecture: C4, modules, datastores |
| [docs/adr/](docs/adr/) | The decisions that shaped everything after them |
| [planning/](planning/) | The course design spec |

## Articles

Every stage has an article; all ten are listed in [`docs/readme.md`](docs/readme.md). Each links
back to the tag it describes, so a reader opens exactly the code being written about.

Their numbers are held honest by a script rather than by care: `scripts/article_check.py`
recomputes each claim at that tag and fails when the prose and the code have drifted apart.

## Language

Everything committed here is in English — lessons, specs, docstrings, check messages, commits.
The reasoning is the product, and reasoning nobody can read makes no argument. See
[ADR-0008](docs/adr/0008-english-is-the-only-language-in-the-repository.md).
