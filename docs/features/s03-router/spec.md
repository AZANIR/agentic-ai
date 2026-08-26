---
status: Draft
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
---

# Spec — s03-router

> **Glossary:** [CONTEXT](../../../CONTEXT.md) (roles + domain objects), [GLOSSARY](../../../GLOSSARY.md) (course terms)
> **Reference module / docs / channels used:** `planning/2026-08-22-agentic-ai-course-design.md` §9 (s03) · `CURRICULUM.md` · `PLAYBOOK.md` · stages 1–2 as the structural model and as the source of the specialists · source article #3 (Multi-Agent Router with LangGraph)

## 1. Context

After stages 1–2 the Learner has an agent with a loop, three safeguards and search over a
knowledge base. What follows is the temptation everybody goes through: give that agent more
tools. Then a few more. Every description goes into the same prompt, the registry grows, and at
some point the model starts choosing worse than it did with five tools.

The commonest reaction is to rewrite the prompt. It does not work, because the problem is not in
the prompt: one model holds one description of the task in its head, and the broader that
description, the blurrier the choice.

**A supervisor is that same agent, with agents for tools.** One sentence, and it is also the main
thing that should survive the stage. No new architecture appears: the same loop as stage 1, the
same registry — it is just that behind a tool's name stands another agent with its own narrow set
rather than a function.

The chosen approach: **our own mini-graph of ~60 lines first, then the same result on
LangGraph.** The order is deliberate. A reader who sees LangGraph first will remember it as
magic; a reader who wrote the routing themselves first will see recognisable parts in the library
and understand exactly what they are paying for.

The stage adds **two lessons that are not in the source article**, both from practice: the
asker's access level has to survive the handoff of a task to a specialist, and a revision loop
with no limit is a bill, not quality. Both become acceptance criteria of their own.

Adopted at interview depth `easy`: the decisions are pinned in the course design specification.
The assumptions taken are in §8.

## 2. Goals

- The reader can explain why one bloated agent loses to three narrow ones, and can name the
  boundary at which that starts.
- The reader sees the state schema as a **decision** rather than as a data structure, and
  understands why changing it later costs more than anything else in the graph.
- The reader has a working checklist for "when a supervisor is superfluous" — because in most
  cases it is exactly that.

## 3. Non-goals

- **We are not building a framework.** The mini-graph exists to show the mechanics and makes no
  claim to fitness. Comparing frameworks is stage 9, separately.
- **We are not making the agents more autonomous.** Specialists stay narrow; none of them gets
  the right to call another specialist directly.
- **We are not adding memory between requests.** The state lives for one run; memory is stage 5.
- **We are not moving specialists into processes or services.** Everything is in one process; the
  network appears at stage 4 (MCP) and at stage 6 (deployment).
- **We are not teaching LangGraph.** The library is here as a second implementation of the same
  task, so that there is something to compare our own code against — not as a subject of study.

## 4. User stories

### US-01: See routing with your own eyes

**As a** Learner
**I want** to see six different requests reach three different specialists
**So that** routing stops being a word and becomes a visible sequence of steps

### US-02: Understand why the state schema is the most expensive decision

**As a** Learner
**I want** to see what exactly lies in the state and who reads it
**So that** I can judge what it will cost to add a field to it six months from now

### US-03: See how the revision loop stops

**As a** Learner
**I want** to see a run in which a specialist did not satisfy the supervisor and the task went
back — until the limit fired
**So that** I build loops with a limit from the start, rather than after the bill

### US-04: See a request for which there is no specialist

**As a** Learner
**I want** to ask a question outside the competence of every specialist
**So that** I know the system will say so honestly rather than invent a route

### US-05: Confirm that access rights survive the handoff

**As a** Learner
**I want** to see the asker's access level arrive at the knowledge specialist unchanged
**So that** the handoff of a task does not become the place where access control quietly
disappears

### US-06: Get the same thing on LangGraph

**As a** Learner
**I want** to run the same task on LangGraph and compare the route
**So that** I can see that the library does the same thing, and understand what I am paying for
with the dependency

### US-07: Reach a decision on "is a supervisor needed here"

**As a** Learner
**I want** a checklist that gives one answer for a concrete situation
**So that** I do not build a graph of three agents where one agent with three tools is enough

### US-08: Check routing deterministically

**As a** Learner
**I want** to run the checks offline and with no key
**So that** I can break the code and see exactly what broke

## 5. Acceptance criteria

### AC-01 (US-01) — happy path

**Given** six NovaShop requests: two about orders, two about the shop's rules, two about
totalling sums
**When** the Learner runs the demo
**Then** every request reaches its **expected** specialist, and each one's route is visible in
the console as a sequence of nodes; no request is handled by two specialists at once

### AC-02 (US-02) — domain invariant

**Given** any run of the graph
**When** it has finished — successfully, on the limit, or with a refusal
**Then** the state holds the handoff counter, the full list of visited nodes and the finish
reason; **no node reads a field that is absent from the state schema**, and every handoff is
recorded

### AC-03 (US-03) — error

**Given** a specialist whose answer does not satisfy the supervisor, and a revision limit
**When** the Learner runs that scenario
**Then** the run finishes **on the limit** rather than looping forever; the result is marked
unfinished, the number of revisions spent is named, and a partial answer is not passed off as a
finished one

### AC-04 (US-04) — error

**Given** a request that belongs to no specialist
**When** the supervisor considers it
**Then** the run finishes with an honest refusal listing the available competences; **no
specialist is called**, and no invented node name appears in the answer

### AC-05 (US-05) — authorization

**Given** an asker with a shopper's access level, and a request whose closest document is an
internal one
**When** the supervisor hands the task to the knowledge specialist
**Then** the access level arrives at the search **unchanged**, and the internal document does not
end up in the answer — neither through the specialist nor through the text the supervisor
assembles at the end

> The mirror half of this property is a criterion of its own, AC-05b. Deliberately split: a leak
> test stays green when the rights have been lost and the result set has gone empty.

### AC-02b (US-02) — error

**Given** a node that reads a field absent from the state schema
**When** the graph reaches that node
**Then** the run fails with the field named and the node named — rather than getting an empty
value and carrying on with it. The state schema is a contract, not a hint

### AC-05b (US-05) — authorization

**Given** the same shopper asker and the same question as in AC-05
**When** the supervisor hands the task to the knowledge specialist
**Then** **the permitted answer does arrive** at the asker: the handoff does not turn "has the
rights" into "nothing found". Checked separately from AC-05, because losing rights and leaking
rights are different events, and a test for one says nothing about the other

### AC-05c (US-05) — authorization

**Given** a request whose text claims the asker is a support operator
**When** the supervisor considers it
**Then** the access level stays the one the graph was called with; no node raises it, and
internal documents do not become available through the wording of a request

### AC-06 (US-06) — cross-context

**Given** the same six requests
**When** the Learner runs them on the LangGraph implementation
**Then** each one's route **matches** the route of our own graph; a divergence, if there is one,
is named in the lesson with a number rather than hidden. If LangGraph is not installed, the
criterion is marked **not passed, not passed-by-default**: the difference between "it matched"
and "we did not look" has to be visible

### AC-07 (US-07) — happy path

**Given** the "do you need a supervisor" checklist and a set of described situations
**When** the Learner works through the checklist for each of them
**Then** for every situation the checklist gives an unambiguous answer, stops at the first rule
that fired, and **no rule is left without a situation that turns it on**

### AC-08 (US-08) — happy path

**Given** a machine with no API key and no network
**When** the Learner runs the stage's checks
**Then** all are green, at least a third of them on failure modes, and the output says that the
fake is what is running

### AC-08b (US-08) — error

**Given** a specialist that raised an exception mid-work
**When** the graph reaches it
**Then** the run does not fall over: the node is named, the error lands in the state and in the
trace, the supervisor receives it as the result of a step and decides what to do next itself

## 6. Non-functional requirements

| # | Requirement | Target | How we measure |
|---|---|---|---|
| NFR-1 | Size of our own graph | ≤ 80 executable lines | line count in a check |
| NFR-2 | Lesson time | ≤ 30 min of reading, ≤ 2500 words | `wc -w` in the reconciliation check |
| NFR-3 | Check run | ≤ 5 s, offline, no key | measurement in the `check_all` output |
| NFR-4 | Share of failure modes | ≥ 1/3 of the stage's checks | a counter in a check |
| NFR-5 | LangGraph optional | the stage's checks are green **without** LangGraph installed | a CI run without the `[s03]` extra |

NFR-5 is not a convenience but a requirement of the course: the reader must be able to complete
the stage having installed nothing, and only then see the library.

## 6.1 Security / privacy

**A handoff is the place where access rights disappear most quietly.** A specialist receives a
task, not an asker; if the access level is not passed explicitly, the specialist will take the
default. In the best case that is "nothing found" for someone who was allowed to see it; in the
worst case, the reverse.

Therefore the access level:

- **is a field of the state schema**, not an argument somebody passes at call time;
- **does not appear in any tool's description**, meaning the model can neither name it nor change
  it;
- is checked **in both directions** — the forbidden thing did not arrive and the permitted thing
  did (the lesson of stage 2).

**Abuse case:** a request worded so that the supervisor decides the asker is an operator. This
must have no effect at all: the access level comes from the graph call, not from the text of the
request, and no node has the right to raise it.

## 7. Metrics / KPIs

| # | Indicator | Target |
|---|---|---|
| QG-1 | Requests from AC-01 that reached the right specialist | 6 out of 6 |
| QG-2 | Runs that finished with no explicit finish reason | 0 |
| QG-3 | Route divergence between our own graph and LangGraph | 0 requests, or named with a number |
| QG-4 | Checks on failure modes | ≥ 1/3 of the total |

## 8. Open questions

There are no open questions blocking implementation.

### Assumptions taken (depth `easy`)

Adopted without a separate request, on the basis of the course design specification. Each one can
be rejected in a single line, at which point it becomes a question of its own.

| # | Assumption | Grounds |
|---|---|---|
| 1 | Three specialists: orders, knowledge, totals | The minimum at which the difference between routes is visible; any fewer and routing degenerates |
| 2 | The orders specialist is the stage 1 agent, the knowledge specialist is the stage 2 search | The stage has to show that a supervisor is assembled from what is already written, not from something new |
| 3 | Routing by a model's decision, not by regular expressions | A regular expression hides the very thing the stage exists for; determinism comes from the fake |
| 4 | The revision limit is configurable, with a small default | The same pattern as the step limit at stage 1 |
| 5 | LangGraph is a separate `[s03]` extra, not a base dependency | NFR-5: the stage can be completed without installing it |
| 6 | The "do you need a supervisor" checklist lives in code, like stage 2's `decision.py` | Prose and code must not drift apart silently |

## Test plan

Size S + route `quick` → the plan lives here.

**Levels.** The stage owns no external dependency: the specialists are local, the model is faked.
`integration` and `contract` are empty **by construction**. That leaves `unit` and `e2e`.

### Criteria coverage

| AC | Test | Level | What it proves |
|---|---|---|---|
| AC-01 | `six queries reach their expected specialists` | e2e | Six requests, six expected routes, visible in the trace |
| AC-02 | `state carries the handoff counter and the visited path` | unit | The state carries the counter, the path and the finish reason |
| AC-02b | `no node reads a field absent from the state schema` | unit | **FAILURE.** A node reading an unknown field fails by name rather than silently yielding `None` |
| AC-03 | `revision loop stops at the limit` | unit | **FAILURE.** The limit fired, the revisions are counted, the result is marked unfinished |
| AC-04 | `query with no specialist is refused honestly` | unit | **FAILURE.** No specialist was called; the node name is not invented |
| AC-05 | `access level survives the handoff` | unit | **FAILURE.** The internal document did not reach the shopper |
| AC-05b | `permitted answer also survives the handoff` | unit | **FAILURE.** The mirror case: the handoff did not turn "has the rights" into "not found" |
| AC-05c | `request text cannot raise the access level` | unit | **FAILURE.** The abuse case from §6.1: the access level comes from the call, not from the text |
| AC-06 | `langgraph route matches the hand-rolled one` | e2e | The same six requests, the same routes; skipped if LangGraph is not installed |
| AC-07 | `supervisor checklist answers every situation` | unit | Every situation has one answer; every rule has a situation |
| AC-08 | `checks run offline and cover failure modes` | e2e | An offline run; the share of failure modes ≥ 1/3 |
| AC-08b | `a specialist that raises does not kill the graph` | unit | **FAILURE.** The node is named, the error is in the state and in the trace |

Every failure and authorization criterion has **a row of its own**.

### What this plan deliberately does not prove

**AC-01 proves that the route is right on a faked model.** A real model routes differently and
sometimes worse; that is a subject for measurement, which is to say for stage 8. The manual
checklist against a real provider is in the lesson.

**AC-06 does not prove that LangGraph is better or worse.** It proves that the result is the
same. Comparing frameworks is stage 9, and doing it here would mean comparing on a single
example.

**AC-05b is the most important row in the table**, and it is here from the experience of stage 2.
Without it, a handoff that lost the access level and narrowed the result set to empty would pass
every check: there really is no leak — the answer has simply disappeared.

### Integration strategy

`<!-- N/A: the stage owns no external dependency; the specialists and the model are local -->`

### Load

`<!-- N/A: no NFR carries a throughput number -->`
