---
id: T6
title: "The search tool for the stage 1 agent's registry"
layer: "ports"
deps: ["T4", "T5"]
acs: ["AC-09"]
files_hint: ["stages/s02_rag/tools.py"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T6 — The search tool for the stage 1 agent's registry

## Why

The bridge: stage 1's thesis is that a tool is an ordinary function with a schema. RAG puts that thesis to the test ([spec AC-09](../spec.md)).

## What

`tools.py`: a `Tool` of the same shape as at stage 1 — name, description, parameter schema, function. The asker's access level is **a parameter of the search**, not the caller's concern (ADR-0002). The loop and the registry of stage 1 are not edited.

## Definition of Done

- [ ] The stage 1 agent picks that tool itself on a policy question
- [ ] Not a single line in `stages/s01_agent_loop/loop.py` is changed
- [ ] The tool's description is enough for the model to pick it with no hint in the prompt
- [ ] Internal documents do not leak through this path either
- [ ] lint clean

## Notes

The "the loop is unchanged" check is a git diff against the `stage-01` tag.

Blocked by: T4, T5
