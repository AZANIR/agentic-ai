---
id: T10
title: "The stage lesson: the canon, the bridge to NovaShop, the boundaries"
layer: "docs"
deps: ["T7", "T8", "T9"]
acs: ["AC-01", "AC-02"]
files_hint: ["stages/s02_rag/README.md", "stages/s02_rag/README.md"]
owner: "Contributor"
estimate: "M"
status: "todo"
---

# T10 — The stage lesson: the canon, the bridge to NovaShop, the boundaries

## Why

Code without a lesson teaches nothing. The structure — [CONVENTIONS.md](../../../../CONVENTIONS.md).

## What

`README.md`: what you will be able to do → the canon (embed → cosine → top-k) → the bridge to NovaShop → three boundaries, named outright. Mandatory: the synonym gap as **expected** behaviour rather than a breakage; why the source is attached by the system; why the filter stands before the selection. `README.md` is one screen.

## Definition of Done

- [ ] The lesson is ≤ 2500 words (spec §6)
- [ ] The reading order of the modules is stated explicitly
- [ ] The synonym gap is named as an expected boundary, with a number
- [ ] It says that the source guarantees existence, not correspondence (ADR-0003)
- [ ] The difference between filtering before and after the selection is shown as a table
- [ ] All links resolve

## Notes

The stage's most likely wrong impression: "RAG does not work". The lesson has to remove it at the start, not at the end.

Blocked by: T7, T8, T9
