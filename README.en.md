# Agentic AI: From Zero to Production

A 10-stage hands-on course in building agentic systems. Not a survey — a repository where
every idea has to be **built, broken, and measured**, and where a claim that cannot be checked
by running something does not get made.

Every stage ships with [an article](docs/readme.md), and the numbers in it are recomputed
against the code at that stage's tag rather than typed by hand.

[Українською](README.md) · [Curriculum](CURRICULUM.md) · [Setup](SETUP.md) · [Glossary](GLOSSARY.md)

---

## What it is

Two things at once, from one codebase:

- **A course.** Ten self-contained stages. Everything runs locally, offline, free, and
  deterministically — no payment card needed anywhere.
- **A deployable service.** The same code, at stages 6 and 10, goes onto a real VM behind
  HTTPS with Postgres, Redis, metrics, tracing, and a spend guard.

`APP_PROFILE` switches adapters, not code branches
([ADR-0002](docs/adr/0002-profile-switched-adapters.md)). So what you learn is literally
what later takes traffic.

## Who it's for

You can write a Python function and run a script. You don't know what an embedding, a tool
call, a state graph, MCP, barge-in, or LLM-as-judge is — which is the point.

**The promise:** after each stage you have something working that you ran yourself, and you
can explain **in words** why it is built that way.

## Structure

```
Act I   · stages 1–5  · BUILD    each stage adds one capability
Act II  · stage  6    · WIRE     the blocks become one deployed service
Act III · stages 7–9  · CHECK    latency, measurement, tool choice
Finale  · stage  10   · REWRITE  cleanly, justifying every decision
```

Stages 7–9 add no features. They exist so you stop lying to yourself.

| # | Stage | What you build |
|---|---|---|
| 1 | Agent loop | A ReAct loop from scratch, no framework |
| 2 | RAG | embed → cosine → top-k → cited answer |
| 3 | Router | Your own mini-graph, then LangGraph |
| 4 | MCP | A FastMCP server and client |
| 5 | Memory | extract → store → retrieve, semantic search |
| 6 | Platform | **First deploy:** FastAPI + HTTPS + metrics |
| 7 | Voice | Batch vs streaming, barge-in, measurement |
| 8 | Evaluation | Three-level evaluation over traces |
| 9 | Frameworks | One task, three frameworks |
| 10 | Capstone | **Second deploy:** everything together, under load |

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # quotes matter — the shell eats bare brackets
cp .env.example .env             # nothing to edit
python scripts/check_all.py      # green, offline, no keys
```

## Status

All ten stages complete; each passed an independent two-reviewer gate.

| Component | State |
|---|---|
| `shared/` — config, LLM shim, FakeLLM, tracing | done, 19 checks |
| `scripts/check_all.py`, `scripts/migrate.py` | done |
| `deploy/docker-compose.yml` — Postgres+pgvector, Redis | done |
| CI (ruff + checks, no secrets) | done |
| Stage 1 — agent loop | **done**, 30 checks, 15 on failure modes |
| Stage 2 — RAG | **done**, 49 checks, 24 on failure modes |
| Stage 3 — router | **done**, 38 checks, 20 on failure modes |
| Stage 4 — MCP | **done**, 36 checks, 21 on failure modes |
| Stage 5 — memory | **done**, 42 checks, 27 on failure modes |
| Stage 6 — platform | **done**, 69 checks, 57 on failure modes; smoke against live HTTPS |
| Stage 7 — voice | **done**, 44 checks, 37 on failure modes; 1574 -> 450 ms |
| Stage 8 — evaluation | **done**, 31 checks, 15 on failure modes; position bias 3 of 3, mirrored 0 of 3 |
| Stage 9 — frameworks | **done**, 28 checks, 12 on failure modes; baseline 37 lines against 54 + 1895 invisible |
| Stage 10 — capstone | **done**, 32 checks, 16 on failure modes; 6 parts execute and 3 are deliberately not wired, 173 executed stage lines against 12 adapter lines (7 %) |

## Articles

Each stage has a written article; they are listed in [`docs/readme.md`](docs/readme.md). Every
article links back to the tag it describes, so the code a reader opens is the code the article
is about.

Their numbers are kept honest by a script rather than by care: `scripts/article_check.py`
recomputes each claimed figure at that tag and fails when the prose and the code disagree.
