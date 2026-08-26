---
id: T3
title: "The ReAct loop with tracing and a step limit"
layer: "app"
deps: ["T1", "T2"]
acs: ["AC-01", "AC-02", "AC-03"]
files_hint: ["stages/s01_agent_loop/loop.py"]
owner: "Contributor"
estimate: "M"
status: "todo"
---

# T3 — The ReAct loop with tracing and a step limit

## Why

The heart of the stage: turning the model's decision into a function call. The flow —
[sad §6, flow 1](../sad.md).

## What

`loop.py`: the cycle "call the model → decision → validation → execution → observation". The step
limit is read from configuration, not hard-coded. A step = one iteration, however many tools the
model asked for in one response. A validation rejection is **the step's result**, returned to the
model, not an exception. Every step is written into the trace through the shared tracer.

## Definition of Done

- [ ] Happy path: the model picks a tool, gets a result, gives an answer
- [ ] A fake that always asks for a tool stops exactly at the limit
- [ ] A stop at the limit returns no invented answer and states the reason
- [ ] Malformed arguments never reach the function; the explanation goes to the model, the loop
      continues
- [ ] The trace contains run_start, an llm_call per step and run_end
- [ ] The module is ≤ 120 lines of executable code (spec §6)
- [ ] lint clean

## Notes

Shares a lane with T4: both tasks edit `loop.py`, so they run one after the other.

Blocked by: T1, T2
