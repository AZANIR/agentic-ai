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
python -m stages.s10_capstone.run      # eight scenes, no key, no network
python -m stages.s10_capstone.check    # 32 checks, 16 of them on failure modes
uvicorn stages.s10_capstone.serve:app  # the second deploy — with no HTTP code of its own
python scripts/mutate.py s10 --expect
```

## The numbers

| What | How much |
|---|---|
| Parts that execute | 6 |
| Deliberately not wired | 3 |
| Stage lines executed per run | 173 |
| Adapter lines that executed | 12 |
| Adapter lines written | 16 |
| Seams named | 6 |
| Scenarios | 6 |
| Checks | 32 |

Three stages execute zero lines **by decision**, each with its reason: MCP tools (stage 4) need
a running server, voice (stage 7) needs gigabytes of weights, and stage 9 turned out to be an
**instrument**, not a part. Zero for a **declared** part reddens the suite by name.

## Two measurement defects the stage found in itself

**Stage 9 "worked" with exactly one line, and that line was the instrument.** It sat among the
parts and reported a non-zero number until a run over empty work reported the same one: it was
`sys.settrace(previous)` in the counter's own `finally`. The instrument was measuring itself.
"Measures" is not "uses" — the same distinction as "imports" versus "uses".

**The price of assembly was counted in a different unit from what it was compared against.**
Adapters statically, from the code; stages dynamically, from execution. The numerator said "is
in the code", the denominator said "runs", and the two printed side by side looked comparable.
Both are executed lines now, and the gap — 16 written against 12 executed — is informative in
itself: `build_search` runs at startup, not per request.

## The rules that made it a capstone rather than a rewrite

- **A mismatch goes into an adapter, never into a part.** A part you had to change disproves
  "the parts were mature", and the change touches that stage's lesson, checks, tag and article.
  The need for the change goes into the **report**, naming the stage.
- **An adapter never decides.** The check catches both forms — `if` and `a if c else b`; only an
  empty-value guard is exempt, and narrowly: `if not <name>:` with a single `return`.
- **Every decision cites a source stage, and the citation is verified by code.** `arch.py` parses
  `ARCHITECTURE.md` and asserts the stage and the named ADR exist. A row the parser cannot read
  is a defect, not silence — it used to vanish from the check along with the dangling citation
  inside it.
- **Found text reaches the model behind stage 2's data fence.** The first draft glued the
  document to the question with a blank line, reopening a gap stage 2 had closed.

## The second deploy costs no adapter at all

`serve.py` builds no application. It takes stage 6's `create_app` and substitutes the assembled
`Capstone`. `Reply` is deliberately **not** named `Answer`, yet it satisfies that application's
contract completely: stages 6 and 10 agree on **shape, not name**. One field was missing —
`retry_after` — and it surfaced not in design but on the first request that raised
`AttributeError`.

The live HTTPS run stays `NOT EVALUATED`: it needs a real machine, and green there would be
green for the unverified.

## What it deliberately does not prove

- That the executed-line count generalizes beyond this request and this thread.
- That the citation check knows a source *contains* the decision — only that it exists.
- That "an adapter never decides" holds beyond the two branch forms it recognizes.
- That six scenarios are coverage. They show assembly; the case set lives in stage 8.
- That the latency numbers hold anywhere else: 20 requests, a fake model, one machine.

## Where to look

| File | Lines | What it holds |
|---|---|---|
| [`seams.py`](seams.py) | 46 | Six seams and the adapters that close them — the price, kept visible |
| [`assemble.py`](assemble.py) | 60 | Executed-line measurement, grouped by stage |
| [`service.py`](service.py) | 71 | The assembled service — no loop, no search, no memory of its own |
| [`scenarios.py`](scenarios.py) | 64 | Six scenarios checking branch, parts, tools and final state |
| [`arch.py`](arch.py) | 74 | The parser that makes `ARCHITECTURE.md` executable |
| [`latency.py`](latency.py) | 21 | Latency, with conditions as data — printed before the number |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | — | Decisions with sources, the capstone's own, and what assembly revealed |
