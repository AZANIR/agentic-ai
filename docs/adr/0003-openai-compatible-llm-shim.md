---
status: Accepted
owner: "Repository owner"
reviewers: []
updated_at: "2026-08-22"
feature_size: "n/a (foundational decision for the repository)"
ticket: "n/a"
---

# 0003 — Reach the LLM only through an OpenAI-compatible shim in shared/llm.py

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** repository owner

## Context

The canonical examples in this field are written against OpenAI (`openai.OpenAI()`, `gpt-4o`).
Repeat that literally and the reader needs a payment card at stage 1, before they understand what
it is for. At the same time an over-abstracted layer makes the code unrecognisable against those
examples and destroys the anchor of trust the lesson format is built on (spec §4).

## Decision drivers

- The reader must get through the whole course for free (map: Constraints).
- Lesson code has to stay recognisable against the canonical example (spec §4).
- Vendor lock-in in teaching material is harmful in itself: it teaches the wrong thing.
- One dependency beats four.

## Considered options

1. **The `openai` SDK with a substituted `base_url`** — one client covers OpenAI, Groq,
   OpenRouter, Ollama and LM Studio, because all of them implement an OpenAI-compatible HTTP
   interface.
2. **LiteLLM** — covers more providers, Anthropic included, but adds its own abstraction layer on
   top of the canonical code.
3. **Each vendor's own SDK with its own interface** — maximum fidelity per API, maximum code.
4. **OpenAI only** — the most faithful reproduction, the highest barrier to entry.

## Decision outcome

**Chosen:** Option 1. One dependency, five providers, and the call in lesson code looks almost
word for word like the canonical one — only where the client comes from changes. Option 2 wins on
coverage but adds a layer the reader has to understand at stage 1, which distracts from the agent
itself.

## Consequences

**Positive**
- A free start through Groq or a local Ollama — no card is needed anywhere in the course.
- Switching provider is two lines in `.env`, not a code change.
- Lesson code stays recognisable against the canonical example.

**Negative**
- **Anthropic is not OpenAI-compatible** — it would need its own adapter behind the same
  interface if it is ever wanted. A known gap, accepted deliberately.
- Providers differ in the details of tool calling (schema strictness, parallel calls). The shim
  has to normalise those differences, or the lesson breaks depending on `.env`.
- Ollama is slow on a weak CPU, and the reader may conclude that "agents are slow" when it is the
  model.

**Neutral**
- LiteLLM can be slotted in later **behind the same** `shared/llm.get_client()` interface — that
  is a replacement implementation, not an architectural change.

## Links

- Spec: [[../../planning/2026-08-22-agentic-ai-course-design.md]] §5.1, §7
- Architecture map: [[../architecture-map.md]] §Stack, §Conventions
- Related ADRs: [[0002-profile-switched-adapters]]
