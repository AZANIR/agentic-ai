---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0008 — What the evaluator lacks in the trace: a measured answer

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

Stage 6 deferred a decision to this stage twice, and both times for the same reason:

> `adr/0005`: "Stage 8 builds evaluation **on traces** and will say what it actually lacks…
> Threading a tracer through on a guess means designing an interface for an imaginary consumer".

Now the consumer exists. The promise has come due.

The rule here is simple and cuts both ways: **the requirement is stated by whoever reads**, and it
is stated **from measurement**. An ADR that says "add tracing to stages 2 and 5" is no better than
the guess stage 6 rejected — until it says what exactly the evaluator cannot do without it.

## Measured

All seven stages were run with the trace going to a temporary file, and the trajectories were
extracted by one piece of code:

```
02_rag       trajectories   1   access, answer, chunking, search, threshold
03_router    trajectories   1   judge, llm_call, revision, revision_limit, route, specialist_failed
s01          trajectories   4   llm_call, run_limit, step_blocked, tool_call, tool_rejected
s04_mcp      trajectories   1   mcp_call
s05_memory   trajectories   1   memory
s06          trajectories  15   done, guard, intent, memory, received, remember
s07_voice    trajectories   1   first_audio, prefetch, speak, stt, think, total
```

Three conclusions, and not one of them is the one expected.

**1. What is missing is not steps. What is missing is the run key.**

Stages 2, 3, 4, 5 and 7 write **one** trajectory for the entire demo run: every scene inside a
single one. The evaluator sees one long run instead of six short ones and cannot attribute a
verdict to a scene.

The scene discriminator **is** in the data — but it is called something different every time:

| Stage | The field that says "which run this is" |
|---|---|
| 1 | `scenario` |
| 5 | `scene` |
| 6 | `trace_ref` |
| 2, 3, 4, 7 | **none** |

Three names for one thing and four gaps. This is the **only** thing keeping the evaluator from
working with every stage the same way.

**The first version of this table was wrong, and that is exactly why the list is now computed.**
It named four fields and two gaps: it counted stage 4's `phase` as a run key and skipped stage 7,
even though the measurement block above lists its steps — `first_audio`, `prefetch`, `speak`,
`stt`, `think`, `total` — and not one of them names a run.

Stage 4's `phase` is the phase of a **failure** (`startup`, `parse`), set by `describe_failure`;
on the happy path it is `None`. A field that appears only when something broke cannot tell runs
apart — it tells breakages apart.

The lesson is wider than the table: an ADR that names a number must also name **the way to get
it**. Here the way exists — `trajectory.survey_run_keys()` parses the tracer calls in the sources,
and the stage check compares its result against the lesson's prose. A number describing a lack of
measurement must not itself be a guess.

**2. The stage 6 service records decisions but not work.**

A request's trajectory is `received · guard · intent · memory · done · remember`. There is **not a
single** model call in the trace. The evaluator sees which branch was taken and what was taken
from memory, and does not see what the call cost, how many tokens it spent, or whether it happened
at all.

On these traces the component level is structurally blind to the model — and that is exactly why
AC-03d requires the **"unscored"** state rather than "passed": missing data is not a success.

**3. The steps of stages 2 and 5 **are** there — just not where they were looked for.**

Stage 6's `adr/0005` said that stages 2 and 5 "write not a single step into the trace". That is
true for the **service**: there memory is traced by the service itself (`memory`), and there is no
search at all, because that path has no RAG branch. In their **own** demos both stages trace in
detail: `search`, `threshold`, `chunking`, `grounded` for the second; `memory` with
`taken`/`skipped`/`retired` for the fifth.

So threading a tracer into stages 2 and 5 is **not needed**. Something else is.

## Decision

**The evaluator has exactly one requirement of the trace:**

> Every step must carry a **run key** — one field with one name, saying which trajectory it
> belongs to. Not `scenario`, not `phase`, not `scene`, not `trace_ref`, but one shared name set
> by `shared/trace.py` rather than by each stage to its own taste.

The second requirement is **optional, named as desirable**: the service ought to trace the model
call the way stage 1 does (`llm_call` with tokens). Without it the component level on the
service's traces stays in the "unscored" state — which is honest, but less useful.

**The change is not made here.** Editing `shared/trace.py` touches all seven stages and would
break this stage's constraint C-2. It belongs to stage 10, which reassembles the stages anyway.
The requirement is written down, measured and addressed; the question stands in §8 of the spec
with an owner and a due date.

## Consequences

**Good.** A promise given twice is kept with numbers. The next person to touch `shared/trace.py`
knows **what exactly** to add and **why** — rather than "evaluation needs something".

**The price.** Until stage 10 the evaluator works with four keys instead of one: `trajectory.py`
takes the key as a parameter (ADR-0001). That is not a workaround — it is the right shape while
the sources disagree, and it will stay useful when an eighth source appears.

**What is NOT decided.** Whether a shared vocabulary of step **kinds** is needed (`tool_call`
against `mcp_call`). The evaluator lives with that: the component level takes the list of kinds as
a parameter. If stage 10 finds that it gets in the way, it will have a measurement of its own;
inventing a vocabulary for an imagined need is the same mistake stage 6 warned against.

## Alternatives considered

**Thread `tracer=None` into stages 2 and 5.** Exactly what stage 6 deferred. Measured: **not
needed** — both stages trace in detail in their own demos, and the service has no branch of
theirs. The edit would add a parameter with no consumer.

**Live with four keys in silence.** It works and leaves the debt unannounced. Two promises would
fade out quietly — precisely what stage 6's `adr/0008` asked not to do: "A promise in the code
must either be kept or moved with the name of the new stage".

**Change `shared/trace.py` here.** Breaks C-2 and touches seven stages for the sake of an eighth.
Besides, a change with no consumer demanding it is designing for an imaginary consumer again, only
from the other side.
