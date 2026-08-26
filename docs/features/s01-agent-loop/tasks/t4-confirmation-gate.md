---
id: T4
title: "The confirmation gate on an irreversible action"
layer: "app"
deps: ["T3"]
acs: ["AC-04"]
files_hint: ["stages/s01_agent_loop/loop.py", "stages/s01_agent_loop/tools.py"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T4 — The confirmation gate on an irreversible action

## Why

The third and most dangerous failure mode from the source article. The mechanism is fixed in
[ADR-0002](../adr/0002-confirm-irreversible-action-by-second-run.md); the flow —
[sad §6, flow 2](../sad.md).

## What

The loop takes a confirmation flag. When the model asks for a tool carrying the irreversibility
flag and there is no confirmation, the function **is not called**; the step returns a description
of what would have happened and how to confirm it, and the run finishes. With confirmation the
tool executes the ordinary way. Confirmation is passed by a separate repeat run, not an
interactive prompt.

## Definition of Done

- [ ] Without confirmation the irreversible function is never called
- [ ] The run describes the consequence and the way to confirm it
- [ ] With confirmation the same action is performed
- [ ] The gate does not touch reversible tools
- [ ] The trace distinguishes "blocked by the gate" from "executed"
- [ ] lint clean

## Notes

Shares a lane with T3 (`loop.py`) — sequentially after it.

Blocked by: T3
