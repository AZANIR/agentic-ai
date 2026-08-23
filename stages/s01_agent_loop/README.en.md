# Stage 1 — The agent loop

> The full lesson is in Ukrainian: [README.md](README.md). This page is the map.
> Idea source: [What is an AI Agent?](https://blog.gopenai.com/what-is-an-ai-agent-the-simplest-explanation-youll-find-e7b176a31c44)

## What it is

A ReAct loop written from scratch — no agent framework — plus the three guards every later
stage inherits: a step limit, argument validation, and a confirmation gate for irreversible
tools.

## Run it

```bash
python -m stages.s01_agent_loop.run      # demo: four scenarios, offline, no key
python -m stages.s01_agent_loop.run --confirm   # same run, irreversible action allowed
python -m stages.s01_agent_loop.check    # 30 checks, 15 of them on failure modes
```

No API key, no network. The first line of the demo tells you where the answers come from.

## The four modules, in reading order

| File | Responsibility |
|---|---|
| [`tools.py`](tools.py) | What the agent is allowed to do: three tools, their schemas, the irreversible flag |
| [`validate.py`](validate.py) | The trust boundary — arguments are checked before any function runs |
| [`loop.py`](loop.py) | The loop itself, plus the step limit |
| [`gate.py`](gate.py) | The confirmation gate — screens the whole step, never a single call |
| [`run.py`](run.py) | The demo: four scenarios, one per acceptance criterion |

## What you'll be able to do

- Explain, in words, why a language model never executes a function itself.
- Recognise this same loop inside any agent framework you open next.
- Name three ways an agent breaks, and point at the code that stops each one.

## The one sentence that matters

**The model does not call functions. It asks for them.** Your code decides whether to comply —
and that gap is where the three guards live.

## Known limits (do not carry these to production)

- Validation handles flat objects with scalar types only; nested objects and arrays are out of
  scope. Use a schema library in production.
- The agent has no memory between runs. That gap is stage 5's subject.
- Green checks measure the logic *around* the model, not the quality of its answers. Answer
  quality is stage 8.

Time: 2–3 hours. Cost: nothing.
