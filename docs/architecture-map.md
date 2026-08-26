---
status: current
mode: brownfield
updated_at: "2026-08-25"
reflects_commit: "faa95f6"
language: "python >=3.11"
build_cmd: 'pip install -e ".[dev]"'
test_cmd: "python scripts/check_all.py"
lint_cmd: "ruff check ."
migration_tool: "custom: scripts/migrate.py + numbered .sql in migrations/"
frontend: "vanilla JS (the stage 7 live-mode page)"  # the only UI in the course; stages 6 and 10 are backend-service + cli
---

# Architecture map — Agentic AI (a teaching-and-production course)

> **A scan of the code that exists** (`mode: brownfield`). Up to stage 6 this map described the
> intended foundation — decisions made before the first line of code. It now describes a system
> that runs and deploys behind HTTPS. The section "State of the system after stage 10" names what
> of the up-front decisions turned out true, and what did not.
>
> **State:** the skeleton was materialised on 2026-08-22, and **all ten stages are finished**.
> The machine-readable keys below are commands that actually worked, not planned ones.
>
> Source of every decision:
> [`planning/2026-08-22-agentic-ai-course-design.md`](../planning/2026-08-22-agentic-ai-course-design.md).

## Stack

- **Language / runtime:** Python 3.11+ — spec §7
- **Packaging:** one installable package, `pyproject.toml` with per-stage extras
  (`[s03]`, `[s04]`, `[s09]`, `[voice]`, `[prod]`, `[dev]`) — spec §7. This is what lets stage 10
  **import** the mature modules of stages 1–9 rather than copy them.
- **Frameworks:** FastAPI + uvicorn (the service), mcp 2.0 (MCP servers), LangGraph / CrewAI /
  Google ADK (stage 9 only, behind extras), APScheduler (background jobs)
- **LLM access:** the `openai` SDK as the single client — through `base_url` it covers OpenAI,
  Groq, OpenRouter, Ollama and LM Studio
- **Build / test / lint:**
  - build — `pip install -e .[dev]`
  - test — `python scripts/check_all.py` (offline, no API key, deterministic)
  - lint — `ruff check .` (lint and format in one tool)

## C4 — the target system

```mermaid
C4Container
    title Target containers - Agentic AI course repo
    Person(learner, "Learner", "Reads lessons / runs stages / deploys")
    Person(enduser, "End user", "Talks to the deployed NovaShop agent")

    Container(stages, "stages", "Python packages s01..s10", "Ten self-contained lessons; s06 and s10 are deployable services")
    Container(shared, "shared", "Python package", "Profile-switched adapters: llm / embeddings / trace / stores")
    Container(api, "agent service", "FastAPI + uvicorn", "HTTP and WebSocket entry; auth, rate limit, budget guard, metrics")
    Container(mcp, "MCP servers", "mcp 2.0 over stdio", "NovaShop tools: orders / returns / catalog")
    Container(web, "test pages", "static html + js", "Chat page and microphone page for manual checks")
    Container(caddy, "Caddy", "reverse proxy", "Automatic HTTPS termination")

    ContainerDb(pg, "Postgres + pgvector", "PostgreSQL 16", "Orders / memory facts / document vectors")
    ContainerDb(redis, "Redis", "Redis 7", "Rate limits / budgets / short term cache")
    Container(obs, "Prometheus + Grafana", "metrics stack", "Is the system healthy")
    Container(lf, "Langfuse", "self hosted tracing", "Why the agent decided that")
    System_Ext(llm, "LLM provider", "Groq or OpenRouter or local Ollama")

    Rel(learner, stages, "runs locally and offline")
    Rel(enduser, caddy, "HTTPS and WSS")
    Rel(caddy, api, "reverse proxy")
    Rel(web, api, "fetch and websocket")
    Rel(api, shared, "imports adapters")
    Rel(stages, shared, "imports adapters")
    Rel(api, mcp, "list_tools and call_tool")
    Rel(shared, pg, "SQL and vector search")
    Rel(shared, redis, "counters")
    Rel(shared, llm, "chat completions")
    Rel(shared, lf, "spans")
    Rel(api, obs, "exposes /metrics")
```

## Module inventory

| Module | Path | Layers | Wired at | Responsibility |
|---|---|---|---|---|
| `shared` | `shared/` | adapters (ports+infra) | imported from `stages/*` | Profile-switched implementations: `llm`, `embeddings`, `trace`, `config`, `counters` (memory/Redis), `factstore` (file/Postgres), `check_runner` |
| `stages.s01_agent_loop` | `stages/s01_agent_loop/` | lesson | `run.py`, `check.py` | **Done.** The loop, argument validation, the confirmation gate; 30 checks |
| `stages.s02_rag` | `stages/s02_rag/` | lesson | `run.py`, `check.py` | **Done.** embed → cosine → top-k, the access filter BEFORE selection; 49 checks |
| `stages.s03_router` | `stages/s03_router/` | lesson | `run.py`, `check.py` | **Done.** A supervisor, the state schema as a contract, the revision loop; 38 checks |
| `stages.s04_mcp` | `stages/s04_mcp/` | lesson + server | `server.py`, `run.py` | **Done.** An MCP server, a stdio client, three failure phases; 36 checks |
| `stages.s05_memory` | `stages/s05_memory/` | lesson | `run.py`, `check.py` | **Done.** A window plus a summary, facts, four retrieval conditions; 42 checks |
| `stages.s06_platform` | `stages/s06_platform/` | **service** | `serve.py` (ASGI) | **Done.** Three guards, a classifier, health and metrics, the two-worker trap; 69 checks. Deployed locally behind HTTPS; trust in a public CA certificate is NOT EVALUATED |
| `stages.s07_voice` | `stages/s07_voice/` | lesson + service | `pipeline.py`, `ws.py` | **Done.** Batch against streaming, barge-in, WebSocket voice; 44 checks; 1574 → 450 ms |
| `stages.s08_eval` | `stages/s08_eval/` | lesson | `run.py`, `check.py` | **Done.** Three levels of evaluation over traces, "unscored" as a third state; 31 checks |
| `stages.s09_frameworks` | `stages/s09_frameworks/` | lesson ×4 | `via_langgraph.py`, `via_crewai.py`, `via_adk.py`, `baseline.py` | **Done.** One task contract, four implementations; the price of scaffolding is measured, not answer quality; 28 checks |
| `stages.s10_capstone` | `stages/s10_capstone/` | **service** | `service.py`, `serve.py`, `run.py` | **Done.** Nine stages assembled into one service; the assembly itself is measured — 173 executed stage lines against 12 adapter lines; 32 checks. Served by stage 6's application; the live HTTPS run is NOT EVALUATED |
| `scripts` | `scripts/` | tooling | CLI | `check_all.py`, `migrate.py`, `mutate.py`, `clean_install.py`, `docs_check.py`, `article_check.py` and three document validators |
| `deploy` | `deploy/` | infra | — | **Done.** `docker-compose.yml` (development) and `docker-compose.prod.yml` (five containers), `Dockerfile`, `Caddyfile`, `smoke.sh`, `RUNBOOK.md` |

## State of the system after stage 10

Up to stage 6 this map described **decisions** taken before the first line of code
(`mode: greenfield-bootstrap`). It now describes what works — and stage 10 supplied numbers in
place of impressions: all ten stages are closed, and six of them execute inside the assembled
service.

```
HTTPS → Caddy → uvicorn (N workers) → guards → intent → memory → s01/s03 → answer
                                        │        │        │
                                      Redis   FakeLLM  Postgres
                                                       (volume)
        planner (its own process) ─────────────────────┘
```

Stage 10 takes that same skeleton and measures it from the inside: 173 executed stage lines per
request against 12 adapter lines (7 %). Stages 4, 7 and 9 are not wired into the assembly — each
named with its reason, and zero for them is a decision rather than a defect.

**What of the up-front decisions turned out true:**

- Two profiles over one codebase — held across **all ten** stages with not one `if profile ==` in
  stage code.
- `shared/` as the single place where branching lives — held; stage 6 added two adapters
  (`counters`, `factstore`) and none of stages 1–5 changed.
- A fake provider by default — held right up to deployment, where `auto_reply` had to be added
  (a service has no script) along with `ALLOW_FAKE_LLM` (stage 6's ADR-0009).
- Stages being self-contained — survived the assembly: the capstone changed **no** part, and
  every mismatch went into an adapter (stage 10's ADR-0004).

**What turned out inaccurate:**

- "Stage 5's interface is narrow, the store will swap out" — half true: the method set really is
  narrow, but `Memory` takes a path rather than a store. The factory stays outside (stage 6's
  ADR-0004), and at stage 10 it is still there.
- The `frontend` field here promised a vanilla page at stages 6–7. Stage 6 turned out to be a
  `backend-service` with no UI; the page arrived at stage 7 and remained the course's only UI.
- The Langfuse trace sink was promised "at stage 6". It moved to stage 8 with a reason (stage 6's
  ADR-0008): the requirements for a trace store are stated by whoever reads the traces.
- "The capstone imports the mature parts of stages 1–9" — a thesis stage 10 refuted by its own
  measurement. Stage 6 **already** imported four stages, and from stage 2 it imports one constant
  and executes zero of its lines. "Imports" is not the same as "uses".

## Conventions (the rules every new stage follows)

Since stage 1 the conventions have **real examples in the code**, and those are what is cited
here.

- **Module naming:** `stages/sNN_slug/`, run with `python -m stages.sNN_slug.run` — example:
  `stages/s01_agent_loop/run.py`. The `s` prefix is mandatory: a Python package name cannot start
  with a digit.
- **Switching environments:** always through `APP_PROFILE=local|prod` plus adapters in `shared/`,
  never through branching in code — spec §5.1, ADR-0002.
- **LLM access:** only `shared/llm.get_client()`; no direct `openai.OpenAI()` in stage code —
  example: `stages/s01_agent_loop/run.py:85`, ADR-0003.
- **Tracing:** every agent step writes through `shared/trace`; tracing is present from stage 1
  rather than added at stage 8 — example: `stages/s01_agent_loop/loop.py:87`, ADR-0005.
- **Checks:** every stage has a `check.py` of bare `assert` statements running offline against
  `shared/fake_llm`; **at least one check always covers a failure mode** — example:
  `stages/s01_agent_loop/check.py`, ADR-0006.
- **Errors:** one response envelope from the service, `{"error": {"code", "message"}}`; limits
  and budget return `429` / `402`, not `500` — spec §8.2.
- **IDs:** external identifiers are prefixed ULID-like strings (`ord_`, `ses_`, `trc_`),
  generated by the application rather than the database.
- **Persistence:** Postgres 16 with `pgvector` as the only store (no separate vector service);
  Redis for counters and a TTL cache only — ADR-0004.
- **Migrations:** numbered `migrations/NNNN_name.up.sql` / `.down.sql`, applied by
  `scripts/migrate.py`; Alembic once the schema starts changing often — spec §7.
- **Secrets:** only `.env`, outside git; `.env.example` / `.env.prod.example` as templates —
  spec §8.2.
- **Language:** everything committed is English — prose, docstrings, comments, check messages,
  commits — ADR-0008.
- **Commits:** no mention of AI assistants in any form (repository rule).

## Datastores

| Store | Engine | Accessed via | Notes |
|---|---|---|---|
| Main database | PostgreSQL 16 + `pgvector` | `shared/stores/` | NovaShop orders, memory facts, document vectors. In profile `local` replaced by an in-memory implementation of the same interface |
| Counters | Redis 7 | `shared/stores/` | Token-bucket rate limits, budget counters, TTL cache. In `local`, an in-process dict |
| Traces | JSONL in `traces/` (local) → Langfuse (prod) | `shared/trace.py` | The same write, two sinks |

## Frontend / UI foundation

A minimal frontend, deliberately. Two static pages with no build step and no framework — they
exist so you can **knock on the service by hand**, not as a product.

- **Component library / design system:** none, and none planned. Two pages do not justify a
  design system; adding React for them would be exactly the excess this course argues against.
- **Design tokens:** a few CSS variables in each page's `<style>`
- **Styling approach:** vanilla CSS in the file itself, no build
- **Shared primitives:** none
- **State / data fetching:** `fetch` and `WebSocket` directly
- **Closest UI precedent:** `deploy/web/chat.html` (text chat) and `deploy/web/mic.html`
  (microphone, stage 7)

**Rule for the future:** if there are ever more than three pages, or a real UI appears, that is a
separate decision with its own ADR — not a framework added quietly.

## Where things live / closest precedents

- **A new teaching stage** → `stages/sNN_slug/`, modelled on `stages/s01_agent_loop/`
  (README.md + exercises.md + solutions/ + CHECKLIST.md + code + check.py).
- **A new adapter** (provider, store, trace sink) → `shared/`, with both implementations
  (`local` and `prod`) behind one interface; never `if PROFILE == ...` in stage code.
- **A new agent tool** → an MCP tool in `stages/s04_mcp/server.py`; fewer tools with clean
  payloads rather than a map of every endpoint.
- **New infrastructure** → `deploy/`, updating `deploy/RUNBOOK.md` with it.

## Constraints & known tech debt

- **The reader must not have to pay to take the course.** `check_all.py` makes no network calls
  at all. Any decision requiring an API key for a basic check breaks the foundation.
- **One VM, ≥4 GB RAM.** The full stack (app + pg + redis + caddy + prometheus + grafana +
  langfuse) does not fit in 2 GB, so `docker compose` has three profiles (`core` /
  `observability` / `full`).
- **One uvicorn worker by default**, because of APScheduler. Not an oversight but a reproduction
  of a real trap; stage 6 shows the problem and moves the scheduler into its own process.
- **Local Whisper on CPU is slow.** That is the substance of lesson 7, not a bug — but the README
  has to carry honest expected numbers.
- **There are no articles in this repository at all.** They are written straight into the blog
  repository, and their `claims.json` files live there too. Checking them against the code is
  automated: `scripts/article_check.py` reads the blog and recomputes every claim at the tag the
  article names.
- **LangGraph / CrewAI / ADK break between releases, and they are _not_ pinned** —
  `pyproject.toml` gives ranges. That is deliberate (a pinned teaching repository rots quietly),
  and it has a price that was actually paid: the executed-line count for LangGraph differs
  between Python versions, so the number in the stage 9 lesson carries the interpreter it was
  measured on, and the check reports `NOT EVALUATED` when the environment differs.

## Reconciliation with the authored architecture doc

There is no authored `docs/architecture.md`. The document this map is reconciled against is
[`planning/2026-08-22-agentic-ai-course-design.md`](../planning/2026-08-22-agentic-ai-course-design.md)
— the **source of truth** for every decision below. The map contradicts it nowhere; it restates
those decisions in the form the downstream SDD skills read.
