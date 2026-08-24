# Stage 5 — Memory: why storing everything makes the answer worse

The lesson itself is in Ukrainian ([`README.md`](README.md)). This page is the map: what the
stage claims, which file holds what, and where to break it.

## What it is

A model call has no state. You send messages, you get a reply; the next call knows nothing
about the previous one. **Everything that looks like memory is something a program put into
the context before the call.** Memory is a system around the model, not a property of it.

Two mechanisms people keep conflating:

| | Short-term | Long-term |
|---|---|---|
| Question | what was said **in this conversation** | what is worth knowing **always** |
| Lifetime | one run | survives the session |
| Mechanism | window + summary of what fell out | extract → store → retrieve |

## Run it

```bash
python -m stages.s05_memory.run           # six scenes; watch scene 3
python -m stages.s05_memory.run --prompt  # how facts enter the prompt
python -m stages.s05_memory.check         # 42 checks, 27 of them on failure modes
python scripts/mutate.py s05 --expect     # break it on purpose, nine exercises
```

Works offline with no API key: extraction and summarising run against a scripted fake.

## The six modules, in reading order

| File | What it holds | Lines |
|---|---|---|
| `facts.py` | the record, and the four conditions that make it eligible | 56 |
| `short_term.py` | the window; the summary accumulates instead of being rewritten | 37 / 50 |
| `retrieval.py` | two implementations behind one interface; each declares its own threshold | 35 |
| `long_term.py` | store, retrieve, contradictions, the owner filter | 79 / 90 |
| `extraction.py` | the only place that calls a model; an empty list is a normal answer | 11 |
| `decision.py` | the what-to-remember checklist; the order is the content | 22 |

## One sentence

> **Showing that a fact was stored is easy. Showing that an irrelevant fact did NOT arrive is
> the actual work.**

Bad memory does not crash. It puts four facts into the context instead of one, the model sees
more noise, and the answer gets slightly worse — then slightly worse again. There is no error
anywhere; there is degradation, which the field calls *context rot*.

The context limit is on tokens. There is no limit on nonsense — you are the limit.

## Four conditions, and the order of one of them

A fact reaches the context only if all four hold:

```
owner      the fact belongs to whoever is asking
status     the fact has not been replaced by a newer one
expiry     the fact has not gone stale
threshold  the fact is relevant enough, and the count is capped
```

The owner filter runs **before** top-k selection. Put it after and someone else's fact takes
a slot, gets removed, and **the owner's own fact — the one that should have arrived —
disappears**. Nothing leaked; the answer vanished. Hence two checks, not one: theirs did not
arrive, **and** mine did. That second half never appears on its own — this is the third stage
running where a review found a check with the right verdict and too weak a claim.

## What this stage does not prove

- **A file, not a database.** One record per line, readable by eye. Stage 6 swaps the store
  behind the same interface, which is why that interface is narrow here.
- **Single process.** Two concurrent writers lose data. Locking belongs to the store.
- **Contradiction by topic, not by content.** Comparing content is inference and costs a
  model call; the topic gives a predictable rule for free. Two facts under different topics
  that contradict each other are invisible to this mechanism, and that is stated, not hidden.
- **Owner is a field, not authentication.** Who `olena` is, the caller decides.
- **Retrieval is linear.** Every fact is read on every question. Fine for hundreds, wrong for
  millions; optimisation lives in stage 8.
- **The default embedder is not semantic.** `hash-words` is word-based too, so on the
  synonym question it scores 0.00 exactly like word overlap. What the second implementation
  does demonstrate is that **the scales differ** — 0.50 against 0.52 on the same fact — which
  is why the threshold belongs to the retrieval and not to the store. Real synonym matching
  needs `EMBEDDINGS_PROVIDER=fastembed` or `openai`.
- **A fact can still reach the context by restating the question.** Union normalisation stops
  it from outranking a genuine answer (0.43 against 0.50), not from passing the threshold.
  Pretending otherwise would be a claim about relevance the mechanism cannot make.

## Where to break it

Nine mutations in `mutations.json`, each pinned to the number of checks it must turn red. The
two worth your time leave the code **working and wrong**: the owner filter moved after top-k
(the answer quietly disappears) and the summary rewritten instead of accumulated (no error at
all — the text stays coherent and gradually stops being true).

Walkthrough in [`exercises.md`](exercises.md), written in Ukrainian.
