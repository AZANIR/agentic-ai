---
id: T7
title: "The demo: search, threshold, chunking and the access filter side by side"
layer: "ports"
deps: ["T5", "T6"]
acs: ["AC-01", "AC-03", "AC-04", "AC-05"]
files_hint: ["stages/s02_rag/run.py"]
owner: "Contributor"
estimate: "M"
status: "todo"
---

# T7 — The demo: search, threshold, chunking and the access filter side by side

## Why

Every criterion has to be visible in the output — just as at stage 1.

## What

`run.py`: scenarios in a row — a literal question against a synonym one, two chunkings side by side, a question outside the base, a shopper's question next to the internal document. The sources banner is shared with stage 1: one line about the model and the embedder.

## Definition of Done

- [ ] A run with no key succeeds, with no network calls
- [ ] The "literal versus synonyms" gap is visible in numbers
- [ ] The two chunkings are shown side by side; the demo does not judge which is better
- [ ] A question outside the base gives "no answer" with the threshold and the closest scores
- [ ] The access filter is visible: the internal document is absent from the results
- [ ] Indexing ≤ 0.5 s, a query ≤ 50 ms, the run ≤ 1 s — measured in the output
- [ ] lint clean

## Notes

The measurements are printed; we put no assert on wall-clock (spec, §The durations).

Blocked by: T5, T6
