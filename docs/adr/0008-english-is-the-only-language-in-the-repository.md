---
status: Accepted
owner: "Repository owner"
reviewers: []
updated_at: "2026-08-26"
feature_size: "n/a (repository-wide decision)"
ticket: "n/a"
---

# 0008 — English is the only language in the repository

- **Status:** Accepted
- **Date:** 2026-08-26
- **Deciders:** repository owner

## Context

The course was written in Ukrainian prose over English code: lessons, specs, ADRs, docstrings,
comments and reader-facing check messages were all Ukrainian, and `CONVENTIONS.md` recorded that
as a rule. That worked while the repository was a personal workbook.

It stops working the moment the repository is published alongside the articles. A reader who
arrives from an English article and finds a Ukrainian lesson cannot use the repository at all —
and the lesson prose is not decoration here, it is the teaching material. The code without it is
a set of exercises with the explanation removed.

There is a second, sharper reason. This repository's whole argument is that a claim must be
checkable by running something. That argument is made **in prose**, and prose nobody can read
makes no argument.

## Decision

**Everything committed to this repository is written in English** — lessons, READMEs, glossary,
specs, ADRs, review records, docstrings, explanatory comments, reader-facing messages including
check failures, and commit messages.

Ukrainian is not forbidden; it is simply not what gets committed. Drafts and working notes
stay in whatever language suits their author — nothing outside version control is bound by this
rule.

The failure-mode marker in check docstrings changes with everything else: `ВІДМОВА ·` becomes
`FAILURE ·`. It is read by `shared/check_runner.py`, by every stage's own coverage check and by
`scripts/article_check.py`, so it is renamed everywhere in one move rather than per stage.

## Consequences

**The migration touches files belonging to already-tagged stages.** Constraint C-1 forbids
editing a finished stage without a recorded decision, and stage 6 enforces it by asserting that
nothing under `stages/s05_memory` has changed since tag `stage-05`. That check fired on this
migration, correctly: this is exactly the kind of cross-cutting change the constraint exists to
surface.

The check is therefore not weakened but made precise. It now allows a changed file **only when
that file is listed against an ADR that exists**, and it still fails on an unlisted change. A
recorded decision passes; a silent edit does not.

**No behaviour changes.** The migration rewrites text, never logic. Every stage's checks pass
unchanged, and the mutation counts pinned in each `mutations.json` stay valid because they
depend on code, not on the language of its comments.

**A half-translated repository is worse than either whole**, because a reader cannot tell which
half is current. The migration is therefore a single tracked piece of work with a defined order:
rules first, then the code-level marker, then the root documents, then the stage lessons, then
the SDD artefacts under `docs/features/`, then docstrings and comments. Until it finishes,
`CONVENTIONS.md` is the statement of intent and this ADR is the record.

**The lessons are English; not every line inside them is, and that is deliberate.** The order
above puts the stage lessons ahead of docstrings and comments, and it held — every lesson's
argument reads in English. What stays Ukrainian inside them is not untranslated prose but quoted
program output. When a lesson prints `траєкторія 13 8 0 62%` it is showing what the reader will
see on their own terminal, and `stages/s03_router/decision.py` defines `ONE_AGENT = "ОДИН АГЕНТ"`
as a constant. Translating a transcript ahead of the code it quotes would make the lesson wrong in
the one way this repository cannot tolerate: the reader runs the command and gets something else.

That makes the last pass a single atomic piece of work rather than two — 7162 Ukrainian lines
across 116 Python files, together with the roughly 150 transcript lines in 28 markdown files that
quote them, and the knowledge-base fixtures under `stages/s02_rag/data/kb/` that checks assert
against by content. Splitting it in either direction opens a window in which the lessons lie.

## Alternatives considered

**Keep the Ukrainian lessons and let the existing `README.en.md` summaries carry English
readers.** Rejected: those summaries are maps of 350–1300 words against lessons of 1200–2000.
They tell a reader what a stage is about, not what it teaches, so the teaching text would stay
unreadable to most of the audience. Once each lesson is English, the summary has nothing left
to do — the `.en` files are therefore deleted rather than maintained in parallel, starting with
the root one in this migration's first pass.

**Translate only what a visitor sees first — the root documents.** Rejected for the same reason
that makes the migration necessary: the visitor follows a link into a stage, and that is where
the argument lives.

**Machine-translate everything in one pass.** Rejected. The prose carries the reasoning, and the
reasoning is the product; a translation that flattens "the detector that always finds it is not
a detector" into something merely grammatical loses what the sentence was for.
