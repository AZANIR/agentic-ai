---
status: Accepted
owner: "Repository owner"
reviewers: []
updated_at: "2026-08-22"
feature_size: "n/a (foundational decision for the repository)"
ticket: "n/a"
---

# 0001 — Keep every stage in one installable Python package with per-stage extras

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** repository owner

## Context

The repository holds ten teaching stages and two deployable services (stages 6 and 10). Stage 10
has to **import** the mature modules of stages 1–9 rather than copy them — that is the lesson
about the difference between teaching code and production code. At the same time, some stages
pull heavy dependencies (LangGraph, CrewAI, Google ADK, `faster-whisper`) that a reader who has
only reached stage 2 should not have to install.

## Decision drivers

- Stages have to be self-contained: a reader can start at stage 5 without doing 1–4 (spec §5.4).
- Stage 10 imports rather than duplicates (spec §5.4).
- Heavy dependencies must not be installed for everyone (map: Constraints — the reader should
  neither pay nor wait).
- One way to run every stage: `python -m stages.sNN_slug.run`.

## Considered options

1. **One package plus optional-dependencies per stage** — `pip install -e .[s09]` installs only
   what is needed.
2. **A separate `requirements.txt` in each stage directory** — more obvious to a newcomer, but
   imports between stages do not work without hand-edited `sys.path`, and stage 10 is forced to
   copy code.
3. **A monorepo of several independent packages** — correct engineering, but every stage has to
   be installed separately; the barrier to entry rises with no teaching benefit.

## Decision outcome

**Chosen:** Option 1. Only it gives both working imports between stages (the condition for stage
10) and selective installation of heavy dependencies. Option 2 looks simpler right up until the
capstone, where it forces copying — precisely the mistake the course argues against.

## Consequences

**Positive**
- `python -m stages.s01_agent_loop.run` works identically for every stage.
- Stage 10 does `from stages.s03_router import ...`, with no path hacks.
- The reader installs only what they need: `pip install -e .[s09]` for stage 9.

**Negative**
- The reader meets extras syntax immediately — slightly more than `pip install -r`. Mitigated by
  `SETUP.md` giving a ready command per stage.
- `pyproject.toml` becomes a central file that changes almost every stage.

**Neutral**
- Moving to `uv` or `poetry` later changes nothing structural — only the install tool.
- With more stages the extras multiply; at around twenty it becomes worth moving to dependency
  groups.

## Links

- Spec: [[../../planning/2026-08-22-agentic-ai-course-design.md]] §5.4, §7
- Architecture map: [[../architecture-map.md]] §Stack
- Related ADRs: [[0002-profile-switched-adapters]]
