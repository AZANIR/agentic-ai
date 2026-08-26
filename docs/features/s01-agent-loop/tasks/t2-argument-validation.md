---
id: T2
title: "Validate tool arguments against the declared schema"
layer: "app"
deps: []
acs: ["AC-03"]
files_hint: ["stages/s01_agent_loop/validate.py"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T2 — Validate tool arguments against the declared schema

## Why

The line of trust: everything arriving from the model is unverified. Hand-written code rather
than a library — [ADR-0003](../adr/0003-hand-written-argument-validation-inside-the-stage.md).

## What

`validate.py`: a single function that takes a schema and arguments and returns either an all-clear
or an explanation of the mismatch. Three cases: a missing required field, an extra field, a wrong
type. **No type coercion is performed** — text where a number was declared is a rejection. Nested
objects and arrays are not supported; name that boundary in the docstring.

## Definition of Done

- [ ] Three kinds of mismatch produce a comprehensible explanation
- [ ] Valid arguments pass through unchanged
- [ ] A string instead of a number is a rejection, not a coercion
- [ ] The module is ≤ 60 lines of executable code (spec §6)
- [ ] lint clean

## Notes

Parallel with T1: they share no files, so they can be done at the same time.

Blocked by: —
