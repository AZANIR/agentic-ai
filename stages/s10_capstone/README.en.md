# Stage 10 — Capstone: what it costs to assemble what was built apart

The lesson itself is in Ukrainian ([`README.md`](README.md)). This page is the map.

## What it is

Nine stages built nine parts. Each one works, each has checks, each was written for its own
demo. Here they become one service — and **the assembly itself is what gets measured**.

The first thesis died on contact with the code. Stage 6 already imports four stages; writing
"the capstone imports the mature parts" would describe something that happened four stages ago.

But the same line carries the real thesis. From stage 2, stage 6 imports **one name** — `PUBLIC`,
an access-level constant that travels on as an argument. Search, embeddings, the access filter —
everything stage 2 exists for — **never run**.

> **"Imports" is not the same as "uses."** And the import list hides the difference.

## Run it

```bash
python -m stages.s10_capstone.run     # seven scenes, no key, no network
python -m stages.s10_capstone.check   # 24 checks, 11 of them on failure modes
python scripts/mutate.py s10 --expect
```

## The numbers

| What | How much |
|---|---|
| Parts that execute / declared | 7 / 7 |
| Stage lines executed per run | 166 |
| Adapter lines | 19 (11 %) |
| Seams named | 6 |
| Decisions with a source / capstone's own | 24 / 3 |
| Checks / on failure modes | 24 / 11 |

Two stages execute zero lines **by decision**: MCP tools (stage 4) need a running server, voice
(stage 7) needs gigabytes of weights. Both sit in a separate list with their reason. Zero for a
**declared** part reddens the suite by name.

## The measurement

The instrument comes from stage 9 — executed-line tracing — rather than being written again: two
definitions of "executed" would make the two stages' numbers incomparable. Its limits are
inherited with it: the number describes **this request** and **this thread**.

One trap was caught by the capstone's own run. The first draft opened a tracing context per
stage and measured zero for six of seven: `sys.settrace` is global **per thread**, so each
context overwrote the previous one. The symptom was quiet and plausible — the table printed,
the numbers were whole integers, and only the last stage was non-zero.

## The rules that made it a capstone rather than a rewrite

- **A mismatch goes into an adapter, never into a part.** A part you had to change disproves
  "the parts were mature", and the change touches that stage's lesson, checks, tag and article.
  The need for the change goes into the **report**, naming the stage.
- **An adapter never decides.** Whatever decides is a part, and a part belongs in a stage — with
  a lesson and checks. The check catches the coarse cases: branching inside an adapter reddens.
- **Every decision cites a source stage, and the citation is verified by code.** `arch.py` parses
  `ARCHITECTURE.md` and asserts the stage exists and the named ADR exists. Twice in this
  repository a plausible document pointed nowhere and aged silently.

## What it deliberately does not prove

- That the executed-line count generalizes beyond this request and this thread.
- That the citation check knows a source *contains* the decision — only that it exists.
- That "an adapter never decides" is enforced beyond the shape of a branch.
- That five scenarios are coverage. They show assembly; the case set lives in stage 8.
- That the latency numbers hold anywhere else: 20 requests, a fake model, one machine.

## Where to look

| File | What it holds |
|---|---|
| [`seams.py`](seams.py) | Six seams and the adapters that close them — the price, kept visible |
| [`assemble.py`](assemble.py) | Executed-line measurement, grouped by stage |
| [`service.py`](service.py) | The assembled service — no loop, no search, no memory of its own |
| [`scenarios.py`](scenarios.py) | Five scenarios checking branch, parts and final state |
| [`arch.py`](arch.py) | The parser that makes `ARCHITECTURE.md` executable |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 24 decisions with sources, 3 of the capstone's own, and what assembly revealed |
