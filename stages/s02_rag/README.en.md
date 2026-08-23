# Stage 2 — RAG: grounding an agent in your own documents

> The full lesson is in Ukrainian: [README.md](README.md). This page is the map.
> Previous stage: [Stage 1 — The agent loop](../s01_agent_loop/README.md) ·
> This stage's code is pinned at tag `stage-02`

## What it is

Retrieval built from scratch — chunking, embeddings, cosine similarity, a relevance
threshold, top-k, and an access filter — wired into the stage 1 agent as one more tool.
The loop itself does not change by a single line, and a check asserts that against the
`stage-01` tag.

## Run it

```bash
python -m stages.s02_rag.run             # demo: five scenes, offline, no key
python -m stages.s02_rag.run --prompt    # same, plus the prompt that goes to the model
python -m stages.s02_rag.check           # 29 checks, 9 of them on failure modes
python -m stages.s02_rag.decision        # the RAG-vs-fine-tuning checklist, as code
```

No API key, no network: embeddings are computed locally by default. The first line of the
demo tells you what is actually running.

## The six modules, in reading order

| File | What it owns |
|---|---|
| `shared/embeddings.py` | Adapter: `hash` (default, offline, deterministic) / `fastembed` / `openai` |
| `chunk.py` | Splitting a document into fragments, with overlap |
| `documents.py` | Reading the knowledge base, its metadata and access level |
| `store.py` | Index, cosine, threshold, top-k, access filter |
| `answer.py` | Assembling the answer; the source is attached by the system |
| `tools.py` | The bridge: search as a stage 1 tool |

## The three decisions worth reading the ADRs for

**A word-hash embedder is the teaching default** ([ADR 0001](../../docs/features/s02-rag/adr/)).
It is deliberately weak, and weak in a specific useful way: a literal question finds the
document at 0.503, the same question in synonyms finds nothing at all. A good teaching
embedder must fail visibly, or the reader never learns why anyone upgrades.

**The access filter runs before top-k selection, not after** ([ADR 0002](../../docs/features/s02-rag/adr/)).
Put it after, and the internal document takes a slot in the results, gets removed, and the
shopper is told "nothing found" for a question that had an answer. Nothing leaked; the
answer vanished. A leak test stays green through this — which is why there is a second,
mirror check that the permitted document is still there.

**The system attaches the source, the model never cites** ([ADR 0003](../../docs/features/s02-rag/adr/)).
A model asked to cite will occasionally name a document that was never retrieved, and an
invented reference looks exactly like a real one. Sources here are taken from the retrieved
list, so referring to a document that does not exist is not technically reachable.

## What this stage deliberately does not prove

**A source is guaranteed to exist, not to be what the answer followed from.** The model got
the fragment and may have answered past it. The demo shows this directly: in scene 4 the
sources include a shipping document that crossed the threshold on a returns question.
Measuring whether the answer follows from its source is stage 8's job, and pretending stage 2
closes it would be worse than an honest gap.

## Where to break it

[`exercises.md`](exercises.md) — eight exercises, each with the measured result: which checks
go red, how many, and why. The first one is the important one.
