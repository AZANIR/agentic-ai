---
id: T8
title: "The stage checks following the coverage table"
layer: "tests"
deps: ["T4", "T5", "T6", "T7"]
acs: ["AC-01", "AC-02", "AC-03", "AC-04", "AC-05", "AC-06", "AC-08", "AC-09", "AC-08b"]
files_hint: ["stages/s02_rag/check.py"]
owner: "Contributor"
estimate: "M"
status: "todo"
---

# T8 — The stage checks following the coverage table

## Why

Carries out `## Test plan` from [spec.md](../spec.md).

## What

`check.py`: thirteen checks following the coverage table, ≥6 on failure modes. Checks with a trace write into a temporary directory. The "literal versus synonyms" control set lives in the text of the check, next to the statement about the gap.

## Definition of Done

- [ ] Thirteen checks match the thirteen rows of the coverage table
- [ ] ≥ 6 are marked as failure modes
- [ ] The run is offline, with no key, ≤ 2 s
- [ ] AC-05b is present as a row of its own: the permitted document did not disappear from the results
- [ ] The working trace file is not polluted
- [ ] lint clean

## Notes

AC-05b is not a duplicate of AC-05. Without it a filter applied after the selection would pass everything.

Blocked by: T4, T5, T6, T7
