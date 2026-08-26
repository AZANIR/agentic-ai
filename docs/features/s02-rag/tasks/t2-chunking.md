---
id: T2
title: "Splitting documents into fragments"
layer: "domain"
deps: []
acs: ["AC-03"]
files_hint: ["stages/s02_rag/chunk.py"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T2 — Splitting documents into fragments

## Why

The fragment size changes the search result — that is a decision, not a technical detail ([spec AC-03](../spec.md)).

## What

`chunk.py`: splitting text into fragments of a given size with overlap, keeping a reference to the source document and to the position. Splitting by size, not by structure: splitting by headings is an exercise, not an implementation ([sad §11](../sad.md)).

## Definition of Done

- [ ] The fragments cover the whole text with no loss
- [ ] Every fragment carries the name of its source document and its position
- [ ] A document shorter than the fragment size gives exactly one fragment
- [ ] An empty document gives zero fragments and raises no exception
- [ ] The module is ≤ 50 lines of executable code (spec §6)
- [ ] lint clean

## Notes

Parallel with T1: they share no files.

Blocked by: —
