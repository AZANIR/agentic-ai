---
status: Accepted
owner: "Contributor"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "n/a (amends a repository-wide decision)"
ticket: "n/a"
---

# 0007 — numpy is a core dependency

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead
- **Amends:** ADR-0001 (per-stage dependency layout)

## Context

ADR-0001 keeps the core minimal: whatever stage 1 needs and nothing else, with heavier things in
per-stage extras. Stage 2 added `numpy` as `[s02]`.

But `numpy` is not imported by a stage. It is imported by `shared/embeddings.py` at module level,
and `shared/check.py` — the checks for the **core** — execute it. CI installs `[dev]` and has
neither `[s02]` nor any reason to.

The consequence was inevitable and silent until the first push: both matrix jobs failed with
`ModuleNotFoundError: No module named 'numpy'` **before the first check ran**. Locally everything
was green, because numpy is installed in the venv.

By the time the cause was named, stage 3 was pulling `numpy` transitively too — so the next push
would have produced three failed modules instead of two.

## Decision drivers

- A package the shared layer imports **unconditionally** is a core dependency, whatever the
  extras table says.
- "LangGraph is missing" and "numpy is missing" look identical in a traceback and mean opposite
  things.
- Stages 4, 6 and 9 will hit the same wall with their own heavy libraries.

## Considered options

1. **CI installs `[dev,s02]`.** One line, the extras table unchanged.
2. **`numpy` in the core.** One line, and the extras table becomes true.
3. **`check_all.py` counts a death on import as "not evaluated".** Durable, but on its own it
   hides the cause.

## Decision outcome

**Chosen:** Option 2 **plus** Option 3, in that order.

Option 1 treats the symptom: CI stops going red while the claim "the core is only stage 1"
remains untrue, and nobody notices until next time. The question is not where to install the
package but **whose it is**.

Option 3 alone is worse than either: if `check_all.py` had already been able to say "NOT
EVALUATED" for any missing package, a broken build would have read as "the stage was not checked"
and CI would have been green on the very bug that was reddening it.

So:

- `numpy` moves into the core; the `[s02]` and `[s08]` extras disappear — nothing was left in
  them.
- `check_all.py` gains a third state, but decides **optionality from `pyproject.toml`** rather
  than from the fact of absence. No `langgraph` — "NOT EVALUATED". No `numpy` — `FAIL`, exit 1.

## Consequences

**Positive**
- The core now describes what the core actually imports.
- Stages 4, 6 and 9 will not kill the run on a base install — and will not hide behind it either.
- The CI step "nothing may stay unverified here" stopped being blind: `check_all.py` used to
  swallow a green module's output along with its "NOT EVALUATED" lines, so the `grep` would have
  missed every time while the job stayed green.

**Negative**
- The core gained `numpy`. Accepted: everyone who reached stage 2 had it installed anyway, and
  the alternative is keeping an untruth in the table.
- "Green" now has two shades, and the reader has to look at the summary line. That is the price
  of honesty; the previous version had one shade and lied.

**What went into the PLAYBOOK**
A local environment is not CI. A package installed into the venv "somewhere along the way" makes
green something that does not run at all on a clean install. Simulating a clean CI — an import
blocker in `sys.meta_path` — costs twenty lines and catches the entire class.
