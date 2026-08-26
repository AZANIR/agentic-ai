---
id: T6
title: "Stage checks: happy paths and three failure modes"
layer: "tests"
deps: ["T3", "T4"]
acs: ["AC-02", "AC-03", "AC-04", "AC-05", "AC-06", "AC-06b"]
files_hint: ["stages/s01_agent_loop/check.py"]
owner: "Contributor"
estimate: "M"
status: "todo"
---

# T6 — Stage checks: happy paths and three failure modes

## Why

Carries out the coverage table from `## Test plan` in [spec.md](../spec.md). The format of the
checks — [repository ADR 0006](../../../adr/0006-assert-checks-over-test-framework.md).

## What

`check.py`: nine checks following the coverage table. Bare `assert`, a one-line docstring, the
prefix `FAILURE ·` on failure-mode checks. Checks that write a trace write into a temporary
directory. The fake model's scripts live in the text of the check, not in a fixture: the script
*is* the specification of the model's expected behaviour.

## Definition of Done

- [ ] Nine checks match the nine rows of the coverage table
- [ ] At least three are marked as failure modes
- [ ] The run is offline, with no API key and no network
- [ ] The working trace file is not polluted
- [ ] A deliberately broken loop gives a non-zero exit code naming the check
- [ ] The run is ≤ 2 s (measured in the output, with no assert)
- [ ] lint clean

## Notes

We deliberately put no assert on wall-clock — see §"The durations" in the test plan.

Blocked by: T3, T4
