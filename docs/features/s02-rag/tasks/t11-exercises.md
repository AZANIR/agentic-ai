---
id: T11
title: "Exercises, reference solutions and the checklist"
layer: "docs"
deps: ["T10"]
acs: ["AC-03", "AC-04", "AC-05"]
files_hint: ["stages/s02_rag/exercises.md", "stages/s02_rag/solutions/", "stages/s02_rag/CHECKLIST.md"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T11 — Exercises, reference solutions and the checklist

## Why

The reader has to turn the threshold and the chunking with their own hands. Completion criterion №5.

## What

`exercises.md`: change the threshold and see answers appear and disappear; change the fragment size; move the access filter AFTER the selection and see the permitted document disappear; add a document and find it. `solutions/` holds the references.

## Definition of Done

- [ ] Four exercises with an explicit expected result
- [ ] The "move the filter after the selection" exercise shows the permitted document disappearing
- [ ] Every reference runs
- [ ] The checklist has all three levels

## Notes

The exercise that moves the filter is the most valuable one: it reproduces a real bug.

Blocked by: T10
