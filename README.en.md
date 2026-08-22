# Agentic AI: From Zero to Production

A 10-stage hands-on course built from [the article series](docs/readme.md) by Sai Bhargav
Rallapalli. Not a retelling — a repository where every idea in the series has to be
**built, broken, and measured**.

> The lessons are written in Ukrainian. This page and each stage's `README.en.md` are the
> English map; the full teaching text lives in the Ukrainian `README.md` files.

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

Skeleton materialized; stages not written yet.

| Component | State |
|---|---|
| `shared/` — config, LLM shim, FakeLLM, tracing | done, 13 checks |
| `scripts/check_all.py`, `scripts/migrate.py` | done |
| `deploy/docker-compose.yml` — Postgres+pgvector, Redis | done |
| CI (ruff + checks, no secrets) | done |
| Stages 1–10 | not started |

## Sources

The original articles live in [`docs/`](docs/readme.md) with their URLs in each file's
frontmatter. The stages do **not** copy the article text — they restate the ideas and build
working code from them.

> Before publishing this repository, the full article texts in `docs/` should be replaced
> with links and original summaries — see §14 of the
> [design spec](planning/2026-08-22-agentic-ai-course-design.md).
