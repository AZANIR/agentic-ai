---
id: T5
title: "The demo: four scenarios in a row and a banner naming the source of answers"
layer: "ports"
deps: ["T3", "T4"]
acs: ["AC-01", "AC-05"]
files_hint: ["stages/s01_agent_loop/run.py"]
owner: "Contributor"
estimate: "M"
status: "todo"
---

# T5 — The demo: four scenarios in a row and a banner naming the source of answers

## Why

The only thing the Learner runs first. Every acceptance criterion has to be visible in the
output — [spec AC-01](../spec.md).

## What

`run.py`: four scenarios in a row — choosing between tools, a validation rejection, a stop at the
limit, the confirmation gate. Each with its own fake-model script. The first line is the banner
from the shared layer: a fake or a real provider. When a provider is configured, the same
scenarios go to it with no code edits.

## Definition of Done

- [ ] A run with no key finishes successfully, with no network calls
- [ ] All four scenarios are visible in the output, each one labelled
- [ ] Every step shows the tool, its arguments and the result
- [ ] The first line is the banner naming the source of the answers
- [ ] With a provider configured the banner changes, the structure of the output does not
- [ ] A run with no provider is ≤ 1 s (measured in the output, with no assert)
- [ ] lint clean

## Notes

Half of AC-05 is checked offline (the client factory), the other half by a manual checklist in the
lesson. Name that boundary outright; see "What this plan deliberately does not prove".

Blocked by: T3, T4
