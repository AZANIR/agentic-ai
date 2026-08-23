# Stage 3 — Router: when one agent is not enough

> The full lesson is in Ukrainian: [README.md](README.md). This page is the map.
> Previous stage: [Stage 2 — RAG](../s02_rag/README.md) ·
> This stage's code is pinned at tag `stage-03`

## What it is

A supervisor whose tools are the agents from stages 1 and 2 — written by hand first, in 37
executable lines, and then again on LangGraph so the two can be compared. Seven routes are
compared and must match.

## Run it

```bash
python -m stages.s03_router.run             # demo: five scenes, offline, no key
python -m stages.s03_router.run --prompt    # plus the prompt the route is chosen by
python -m stages.s03_router.check           # 38 checks, 20 of them on failure modes
python -m stages.s03_router.decision        # the do-you-need-a-supervisor checklist
pip install -e ".[s03]"                     # optional: enables the LangGraph comparison
```

No API key. LangGraph is optional: without it the stage still completes, and the route
comparison prints that it was **not verified** rather than passing quietly.

## The five modules, in reading order

| File | What it owns |
|---|---|
| `state.py` | The state schema as a declared contract; three fields are immutable |
| `specialists.py` | Three narrow competences, each built from code that already exists |
| `graph.py` | Supervisor, route validation, revision loop with a counter — 49 lines |
| `langgraph_impl.py` | The same graph on LangGraph; imported only when installed |
| `decision.py` | The checklist, as code, so prose and behaviour cannot drift apart |

## The four decisions worth reading the ADRs for

**The hand-rolled graph comes before LangGraph** ([ADR 0001](../../docs/features/s03-router/adr/)).
A reader who meets the library first remembers it as magic. A reader who wrote the routing
first recognises `add_node` and `add_conditional_edges` as things they already built, and can
then ask what the dependency actually buys.

**The state schema is a declared contract, not a free dict** ([ADR 0002](../../docs/features/s03-router/adr/)).
When adding a field costs one line, nobody asks what the field actually costs — every node
that comes to depend on it, none of which will announce the dependency. `__slots__` makes the
contract free: reading or writing anything else is an error.

**The access level travels in the state** ([ADR 0003](../../docs/features/s03-router/adr/)).
Passing it at each handoff works until someone adds a fourth specialist and forgets the line.
Nothing may write that field, so a request claiming to come from a support operator has
nowhere to write.

**The model picks the route; the graph validates it** ([ADR 0004](../../docs/features/s03-router/adr/)).
A keyword rule would hide the whole point. The model may name a node that does not exist —
and eventually will — so the name is checked against the registry rather than used as given.

## Two events, two opposite reactions

```
a specialist raises          a fact about the world  ->  becomes a step result, the graph lives
a node reads a missing field a broken contract       ->  the run stops, naming the field
```

The warehouse can be down; the graph must survive that. A node reading an undeclared field
means the contract is broken, and continuing on an empty value is worse than stopping.

## What this stage deliberately does not prove

**Routing quality.** On the scripted fake the route is correct by construction. A real model
routes differently and sometimes worse — that is a quantity you measure, and measurement is
stage 8. The manual checklist with a real provider is the interesting part of this stage.

**That LangGraph is better or worse.** The comparison proves the result is the same. Judging
frameworks on one example would be judging nothing; that is stage 9.

## Where to break it

[`exercises.md`](exercises.md) — eight exercises, each with the measured result: which checks go
red and how many. Removing the revision limit is the one to start with; the second check it
turns red is more interesting than the first.
