---
id: T4
title: "Index, cosine, top-k, threshold and the access filter"
layer: "app"
deps: ["T1", "T2", "T3"]
acs: ["AC-01", "AC-04", "AC-05", "AC-08b"]
files_hint: ["stages/s02_rag/store.py"]
owner: "Contributor"
estimate: "M"
status: "todo"
---

# T4 — Index, cosine, top-k, threshold and the access filter

## Why

The heart of the stage. The order of the operations here is the subject of [ADR-0002](../adr/0002-filter-by-access-level-before-top-k.md), not an implementation detail.

## What

`store.py`: indexing fragments, cosine closeness, the top-k selection, the relevance threshold from configuration. **The access-level filter is applied BEFORE the top-k selection.** Broken documents are named and skipped, the base stays usable. The search writes the scores and how many were filtered out into the trace.

## Definition of Done

- [ ] A literal question gives top-1 = the returns document, with visible scores
- [ ] A question in synonyms does not find it — the gap is pinned down by a check
- [ ] Nothing above the threshold — it returns empty plus the closest scores and the threshold itself
- [ ] The internal document does not reach a shopper's results
- [ ] **The permitted document does not disappear from the results** — proving the filter stands before the selection
- [ ] The empty and the too-short document are named, the rest of the base is searchable
- [ ] Three consecutive runs give an identical order
- [ ] The module is ≤ 80 lines of executable code (spec §6)
- [ ] lint clean

## Notes

The 80-line limit is tight: the module holds the cosine, the top-k, the threshold and the filter. If it is exceeded, the filter moves out into its own module, like the gate at stage 1 — do not inflate the limit ([sad §11](../sad.md)).

Blocked by: T1, T2, T3
