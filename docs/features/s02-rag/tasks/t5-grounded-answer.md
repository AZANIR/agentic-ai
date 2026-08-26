---
id: T5
title: "Composing an answer with a source the system attaches"
layer: "app"
deps: ["T4"]
acs: ["AC-02", "AC-04"]
files_hint: ["stages/s02_rag/answer.py"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T5 — Composing an answer with a source the system attaches

## Why

Without a citation a grounded answer and a hallucination look the same. Who exactly cites is the subject of [ADR-0003](../adr/0003-system-attaches-the-source.md).

## What

`answer.py`: the fragments found go to the model **in a separate marked block, as data**, not as instructions. The source is attached to the answer by the system from the list of what was found — the model does not cite. Nothing found above the threshold → no answer is composed at all.

## Definition of Done

- [ ] Every answer issued carries a source from the list of what was found
- [ ] A source the model wrote into the text does not become the answer's source
- [ ] Nothing above the threshold — there is no answer, the threshold and the closest scores are named
- [ ] The retrieved text is passed to the model in a separate marked block
- [ ] lint clean

## Notes

The boundary is named outright in ADR-0003 and has to be in the lesson: the source is guaranteed to exist, but it does not guarantee that the answer follows from it.

Blocked by: T4
