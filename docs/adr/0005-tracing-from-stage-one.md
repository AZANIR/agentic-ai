---
status: Accepted
owner: "Repository owner"
reviewers: []
updated_at: "2026-08-22"
feature_size: "n/a (foundational decision for the repository)"
ticket: "n/a"
---

# 0005 — Write step traces from stage 1, into our own JSONL, with a Langfuse sink in production

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** repository owner

## Context

The usual confession from people who have built these systems is *"I'd instrument tracing before
the system got complex, not after"* — tracing gets added once three agents and three MCP wrappers
are already running, and then has to be stretched over a tangle. Stage 8 of this course
(evaluating agents) works **on top of traces**: without them it would have to rewrite every
earlier stage.

## Decision drivers

- That advice has to be followed rather than quoted — otherwise the course teaches what it does
  not do.
- Stage 8 reads trajectories, not just final answers (spec §9, s08).
- The reader should see a trace **at stage 1**, when nothing is deployed and nothing is running.
- Production mode needs a real tracing tool, not a file.

## Considered options

1. **A minimal tracer of our own in `shared/trace.py`** — JSONL to a file (profile `local`),
   Langfuse (profile `prod`), one write interface.
2. **Langfuse from stage 1** — a real tool immediately, no format of our own.
3. **Add tracing at stage 8**, when it is first needed.
4. **OpenTelemetry from stage 1** — the industry standard, exporters ready made.

## Decision outcome

**Chosen:** Option 1. Option 2 would make the reader bring up four containers to watch a
four-step ReAct loop — off-putting at exactly the stage that should be the easiest. Option 3 is
the very mistake practitioners regret, repeated deliberately. Option 4 imposes the
span/context-propagation model on a newcomer before they understand what an agent step is.

## Consequences

**Positive**
- Stage 8 rewrites none of the earlier stages — the data is already there.
- The reader sees a trace at stage 1 with nothing but Python and a text editor.
- The same `trace.step(...)` call works locally and in production; only the sink changes
  (ADR-0002).

**Negative**
- Our format has to be mapped onto Langfuse's model (trace → observation) — real work at stage 6,
  and the mapping may turn out imprecise for nested calls.
- One more hand-written component to maintain.

**Neutral**
- OpenTelemetry can be added as a **third sink** behind the same interface, if the repository is
  ever integrated into existing observability.
- The JSONL format is deliberately plain: one line, one step. Anything deeper than two levels of
  nesting would force a revision.

## Links

- Spec: [[../../planning/2026-08-22-agentic-ai-course-design.md]] §5.2, §8.3
- Architecture map: [[../architecture-map.md]] §Conventions, §Datastores
- Related ADRs: [[0002-profile-switched-adapters]], [[0006-assert-checks-over-test-framework]]
