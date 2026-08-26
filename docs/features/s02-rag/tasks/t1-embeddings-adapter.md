---
id: T1
title: "An embeddings adapter in the shared layer: hash / fastembed / openai"
layer: "infra"
deps: []
acs: ["AC-06"]
files_hint: ["shared/embeddings.py"]
owner: "Contributor"
estimate: "S"
status: "todo"
---

# T1 — An embeddings adapter in the shared layer: hash / fastembed / openai

## Why

The embedder is a profile-dependent adapter just like the LLM client ([repository ADR 0002](../../../adr/0002-profile-switched-adapters.md)). The teaching default is a hash over words ([ADR-0001](../adr/0001-word-hash-embedder-as-the-teaching-default.md)).

## What

`shared/embeddings.py`: `get_embedder()` on the same model as `get_client()`. The hash over words is deterministic, stdlib plus NumPy, with no network. `fastembed` and `openai` sit behind the same interface and are switched on by configuration. Plus a line for the shared sources banner, so that a second banner does not appear beside the stage 1 one.

## Definition of Done

- [ ] The hash embedder is deterministic: the same text gives the same vector across processes
- [ ] The vectors are normalised — the cosine reduces to a dot product
- [ ] With a faked environment the factory returns a real embedder and names it
- [ ] With no configuration it makes no network call at all
- [ ] `python -m shared.check` stays green
- [ ] lint clean

## Notes

Ukrainian morphology: "повернення" and "повернень" are different words to this embedder. That is lesson material, not a bug — but pin the behaviour down with a check.

Blocked by: —
