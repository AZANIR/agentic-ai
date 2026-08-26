---
id: T1
title: "A registry of three tools with schemas and an irreversibility flag"
layer: "app"
deps: []
acs: ["AC-01", "AC-04"]
files_hint: ["stages/s01_agent_loop/tools.py", "stages/s01_agent_loop/data/"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T1 — A registry of three tools with schemas and an irreversibility flag

## Why

The registry is the single source of truth about what the agent is allowed to do. The
irreversibility flag lives here, not as a list of names inside the loop — [ADR-0002](../adr/0002-confirm-irreversible-action-by-second-run.md).

## What

`tools.py`: three functions — `get_weather` (the article's canon), `get_order_status` (the bridge
to NovaShop), `initiate_return` (irreversible). For each one a JSON schema of its parameters in
the format that goes to the model, plus an irreversibility flag. NovaShop order fixtures in
`data/`. The registry is a plain `name → entry` dictionary, without decorators: a decorator would
hide the registration in exactly the place where the stage is showing the mechanics.

## Definition of Done

- [ ] The registry returns three entries; each has a function, a schema and a flag
- [ ] Exactly one tool is marked irreversible
- [ ] The schemas are usable in `tools=` with no conversion
- [ ] lint clean

## Notes

The schemas are written in English — see the open question in spec §8 about the language of tool
descriptions. A description has to be enough for the model to pick the right tool without hints
in the prompt.

Blocked by: —
