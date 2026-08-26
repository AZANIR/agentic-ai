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

Ukrainian is not forbidden; it is simply not what gets committed. Drafts, working notes and
everything under `sources/` stay in whatever language suits their author, which is one reason
`sources/` is gitignored.

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

## Alternatives considered

**Keep Ukrainian lessons and English `README.en.md` summaries.** Rejected: the summaries are
maps of 350–1300 words against lessons of 1200–2000. They tell a reader what a stage is about,
not what it teaches. The teaching text would remain unreadable to most of the audience.

**Translate only what a visitor sees first — the root documents.** Rejected for the same reason
that makes the migration necessary: the visitor follows a link into a stage, and that is where
the argument lives.

**Machine-translate everything in one pass.** Rejected. The prose carries the reasoning, and the
reasoning is the product; a translation that flattens "the detector that always finds it is not
a detector" into something merely grammatical loses what the sentence was for.
