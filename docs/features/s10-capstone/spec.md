---
status: Draft
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "L"
---

# Spec — s10-capstone

> **Glossary:** [CONTEXT](../../../CONTEXT.md) (roles + domain objects), [GLOSSARY](../../../GLOSSARY.md) (course terms)
> **Reference module / docs / channels used:** `planning/2026-08-22-agentic-ai-course-design.md` §9 (s10) · `CURRICULUM.md` · `PLAYBOOK.md` · `docs/architecture-map.md` · `stages/s01_agent_loop/` … `stages/s09_frameworks/` as import sources · `deploy/` (the first deployment, stage 6) · source article #10 (Capstone)

## 1. Context

Nine stages built nine parts. Each one works, each has checks, each was written **for its own
demo**.

The final claim of the course comes from that same article:

> **The course taught not ten topics but the habit of making the same trade-offs in a system
> nobody has written a tutorial about yet.**

That claim is easy to write and hard to prove. The capstone proves it by **assembly**: it takes
nine parts, made at different times for different tasks, and builds one service out of them.

**But "assembling what is mature" is not what tells the capstone apart from stage 6.** Stage 6
**already** imports stages 1, 2, 3 and 5: you can see it in the first ten lines of its `app.py`.
Writing "the capstone imports what is mature" would describe something that happened four stages
ago.

The difference lies elsewhere, and it is measurable. Measured before the first line of code:

> **Stage 6 imports exactly one constant from stage 2 — and executes not a single line of it.**

`from stages.s02_rag.documents import PUBLIC` is an access level that travels on as an argument.
Retrieval, embeddings, the access filter, everything stage 2 exists for, **never** runs. The stage
is in the import list; the stage is absent from the work.

> **"Imports" is not the same as "uses".**

That is the capstone's question, and no tutorial has an answer to it, because tutorials do not have
nine preceding stages. Here it has an answer as a **number**: how many lines of each stage really
execute on one request.

**And it is measured with an instrument this very course built.** Stage 9 learned to count the
executed lines of somebody else's package in order to show the price of scaffolding. The capstone
points the same instrument at the stages themselves — and asks how many of the nine really work,
and how many are present only in an `import` line.

**Assembly costs lines.** Nine modules designed independently do not join for free: stage 2 and
stage 6 both have an `Answer` class, and they are **different** classes. Every such seam costs an
adapter, and those lines are the capstone's second number.

**The second claim is about justification.** The capstone's `ARCHITECTURE.md` justifies **every**
decision by citing a source stage. This is not a bibliography: the citation is checked. A decision
with no stage under it was either invented on the spot or belongs to a stage nobody has written
yet — and both cases have to be said out loud.

**What the capstone does not do.** It improves none of the nine parts. A part that would have to be
changed to fit stays unchanged, and the change goes into an **adapter** — and lands in the number.
Otherwise the capstone quietly rewrites the course to suit itself, and the claim "the parts were
mature" becomes unprovable.

**The second deploy.** Stage 6 deployed a service for the first time — and did it by building the
service from scratch. Here what gets deployed is the assembly, and the full wrap — access, limits,
budget, metrics, tracing, backups, CI — is taken **from where everything else comes from**: from a
source stage, with a citation.

Decided at interview depth `easy`: the decisions are already fixed in the course design
specification. The assumptions taken are at the end of §8.

### The vocabulary of this specification

Four words are used precisely and are not interchangeable:

- **Part** — a module of stages 1–9 that the capstone **imports**. It neither copies nor changes it.
- **Seam** — a place where two parts do not meet without an adapter: different names, different
  result shapes, different assumptions about the call.
- **Adapter** — capstone code that exists **only** for a seam. It adds no behaviour; if it does,
  it is already a part, and a part belongs in a stage.
- **Justification** — a row of `ARCHITECTURE.md` naming a decision and a **source stage**. With no
  source it is not a justification but a preference.

## 2. Goals

- The reader starts, with one command, a service assembled from the **real** parts of stages 1–9 —
  and can prove it rather than take it on faith.
- The reader sees the **price of assembly**: how many adapter lines were needed and which seam each
  of them closes.
- The reader sees **how many lines of each stage really execute** on one request — and which stages
  are present only in an `import` line.
- The reader sees five end-to-end scenarios on the fake: the right branch **and** the right final
  state.
- Every decision in `ARCHITECTURE.md` has a source stage, and the citation is **checked**.
- The operator has the full wrap — access, limits, budget, metrics, tracing, backups — and knows
  for every item which stage it came from.
- The reader sees the p50/p95 latency numbers with an honestly named limit on where they were
  measured.
- The Contributor has a list of what the assembly **revealed** about the previous nine stages.

## 3. Non-goals

- **We do not rewrite stages 1–9.** A part that does not fit stays unchanged; the price goes into
  an adapter and into the number.
- **We do not invent a new agent architecture.** The capstone assembles rather than invents: an own
  decision with no source stage is an exception to be named here, not the norm.
- **We add no new techniques.** No new kind of memory, routing or retrieval: if something is
  missing, that is a finding about the course, not a licence to write a tenth stage inside the
  tenth.
- **We do not do Kubernetes, autoscaling or multi-region.** Article 6 argues against them at this
  scale, and the capstone does not revisit that decision silently.
- **We do not measure answer quality.** That is stage 8, and the capstone **uses** it rather than
  repeating it.
- **We promise no production numbers.** The load run goes against a locally started service on a
  fake model; the limit is stated directly.

## 4. User stories

### US-01: the service in one command
**As** a Learner
**I want** to start the assembled service with one command and ask it a question
**So that** I see nine stages at work as one system rather than as nine demos

### US-02: really executes rather than merely imports
**As** a Contributor
**I want** to see how many lines of each stage execute on one request
**So that** I can tell a stage that works from a stage that is only mentioned in an `import` line

### US-03: the price of assembly as a number
**As** a Learner
**I want** to see how many adapter lines were needed and which seam each of them closes
**So that** I know what it costs to assemble independently designed parts

### US-04: every seam has a reason
**As** a Contributor
**I want** every adapter to name the seam it closes
**So that** I can tell a necessary adapter from a redundant layer

### US-05: five scenarios end to end
**As** a Learner
**I want** five different requests and, for each, a check of the branch **and** the final state
**So that** I see more than "something answered"

### US-06: justification with a source
**As** a Tech Lead
**I want** every decision to name the stage it came from
**So that** the architecture document is checkable rather than a list of preferences

### US-07: the full wrap and where it came from
**As** an Operator
**I want** access, limits, budget, metrics, tracing and backups — and to know the source of each
**So that** I understand what of this was thought through in a stage and what was hastily added here

### US-08: latency numbers with a named limit
**As** an Operator
**I want** a p50 and a p95 with a direct statement of where they were measured
**So that** I do not carry the numbers from a fake over to production

### US-09: the capstone evaluates itself
**As** a Learner
**I want** the stage 8 evaluator to read the capstone traces
**So that** I see the instrument built at stage 8 working on a system that did not exist back then

### US-10: what the assembly revealed about the course
**As** a Contributor
**I want** a list of what joined badly, and why
**So that** the capstone is an honest report on the course rather than a ceremonial finale

### US-11: a second deploy with no second HTTP layer

**As** an engineer bringing up the assembled service,
**I want** to serve it with the same application stage 6 uses,
**So that** "the capstone assembles rather than rewrites" stays true at the HTTP boundary too.

## 5. Acceptance criteria

### AC-01 (US-01) — happy path

**Given** the assembled service and a user request
**When** the Learner starts it with one command and asks a question
**Then** the service answers, and the answer shows **which parts** took part: the branch, the tools
used, whether memory was consulted, whether a guard fired

### AC-01c (US-01) — error

**Given** a request on which a part fails midway
**When** the service forms an answer
**Then** the request is counted in the metrics **exactly once** and in one bucket, and the answer
names those that already managed to do their work

### AC-02 (US-02) — domain invariant

**Given** the assembled service and one request
**When** the harness traces the executed lines, grouped by source stage
**Then** it names a number for **every** stage 1–9: how many of its lines **executed**.

This is the stage's main requirement, and it is not about imports. Stage 6 imports stage 2 and
executes zero of its lines; a list of imports does not show that, and a table of what executed
shows it at once

### AC-02c (US-02) — domain invariant

**Given** the table of numbers in the lesson
**When** the run produces different numbers
**Then** the check reddens — the lesson's numbers come from the measurement, they are not typed in
by hand

### AC-02b (US-02) — error

**Given** a stage named in `ARCHITECTURE.md` as part of the assembly
**When** tracing shows **zero** executed lines for it
**Then** the check reddens and names the stage.

An import that executes nothing is an `import` line, not assembly. A stage may be declared
deliberately not wired in, but then it stands in a different list and does not count as a part

### AC-03 (US-03) — happy path

**Given** the assembled service
**When** the Learner runs the count of the price of assembly
**Then** they get **two numbers**: the adapter lines that had to be written, and the stage lines
that executed on this request — plus the ratio between them.

Both are counted **the same way** — as executable lines, with the same instrument used at stage 9

### AC-03b (US-03) — domain invariant

**Given** the list of adapters
**When** the check counts them
**Then** their sum is **smaller** than the sum of what was imported by at least a factor of five.

The number is not a performance target; it is the **limit of the genre**. A capstone whose adapters
weigh as much as its parts is no longer assembling — it is rewriting, and the stage's claim becomes
unprovable

### AC-04 (US-04) — domain invariant

**Given** any adapter
**When** the Contributor reads it
**Then** it names its **seam**: which two parts do not meet, and why.

The check asserts this mechanically: every adapter has a named seam, and every named seam mentions
at least two different parts

### AC-04b (US-04) — error

**Given** an adapter that adds behaviour beyond joining
**When** the check runs
**Then** it reddens: an adapter that **decides** something is a part, and a part belongs in a stage,
not in the capstone

### AC-05 (US-05) — happy path

**Given** a fake model and five different requests
**When** the harness runs them end to end
**Then** for each of them **both the branch and the final state** are checked: which part answered,
what is left in memory, what was written into the trace.

Checking the answer alone would have missed the case where the text is right and the state is not

### AC-05b (US-05) — error

**Given** a scenario in which a part fails
**When** the harness runs it
**Then** the service stays alive, and the answer names **what exactly** failed: a part failing is
not the system falling over, and that is the difference stage 4 already showed

### AC-06 (US-06) — cross-context

**Given** `ARCHITECTURE.md`
**When** the check parses it
**Then** **every** decision has a source stage, and every named stage **exists** in the repository.

A decision with no source is allowed, but only in the separate section "the capstone's own
decisions" — and each one there has a reason for why there is no source stage

### AC-06b (US-06) — error

**Given** a justification citing a stage or an ADR that does not exist
**When** the check runs
**Then** it reddens and names the dangling citation.

A bibliography nobody reconciles ages silently — and that is exactly how the documents of stages 6
and 8 went wrong, until they started being checked

### AC-07 (US-07) — authorization

**Given** a request with no credentials
**When** it reaches the service
**Then** it does not run, and the trace holds a trail of the refusal.

The same guard as at stage 6, and **the same code**: the capstone imports it rather than writing it
again

### AC-07b (US-07) — domain invariant

**Given** the list of the wrap: access, limits, budget, metrics, tracing, backups
**When** the Operator looks at `ARCHITECTURE.md`
**Then** a source stage is named for **every** item, and for anything added here — a reason for why
there is no stage

### AC-07c (US-07) — error

**Given** a daily spending limit and a service that charges before doing the work
**When** the limit is exhausted
**Then** the next request is refused by the budget guard; and if the charge is removed, the check
reddens, because the breaker would never fire again

### AC-08 (US-08) — happy path

**Given** a locally started service and a load run
**When** the Operator looks at the result
**Then** they see a p50 and a p95 **together with the conditions**: how many requests, which model,
which machine.

A number without its conditions is not a measurement; stage 7 showed that on voice latency

### AC-08b (US-08) — error

**Given** a missing load tool or a service that is not up
**When** the check runs
**Then** its state is **not evaluated** with a named reason, neither green nor red

### AC-09 (US-09) — cross-context

**Given** the traces the capstone writes
**When** the stage 8 evaluator reads them
**Then** it extracts **more than one** trajectory and gives three levels of verdict — with no change
to itself.

An instrument built at stage 8 works on a system that did not exist then. If it does not work, that
is a finding about stage 8, and it goes into §10

### AC-10 (US-10) — domain invariant

**Given** a finished assembly
**When** the Contributor reads `ARCHITECTURE.md`
**Then** it holds a section **"what assembly revealed"** listing what joined badly, and for every
item the stage it concerns.

An empty section here is the most suspicious possible outcome: nine modules designed independently
do not join perfectly, and a report saying otherwise is reporting on something other than the
assembly

### AC-11 (US-01) — cross-context

**Given** a profile with no API key
**When** the Learner starts the service and runs all five scenarios
**Then** everything works on the fake: no part needs either a network or a key.

The capstone is the last stage, and it is the easiest place to break a rule that has held for nine
stages

### AC-12 (US-10) — error

**Given** a harness with a deliberately broken adapter
**When** the Contributor runs the checks
**Then** the check that asserts **exactly that seam** reddens, and its message names which two parts
stopped meeting

### AC-13 (US-11) — domain invariant

**Given** the assembled service
**When** it has to be served over HTTP
**Then** the stage 6 application is used, and the capstone has **no** HTTP layer of its own — no
application constructor, no routes of its own

### AC-13b (US-11) — authorization

**Given** the stage 6 application around the assembled service
**When** a request with no key and a request with a key arrive
**Then** the first is refused by the stage 6 guard and the second gets an answer — **with no change
to the application**

### AC-13c (US-11) — error

**Given** the list in `deploy/smoke.sh` and a live domain
**When** a run against real HTTPS cannot be reproduced offline
**Then** the state is **not evaluated** with a named reason, not green

## Test plan

Every criterion of §5 has at least one named test. The level is generalised; the concrete functions
live in `stages/s10_capstone/check.py`.

| AC | Test | Level | What it proves |
|---|---|---|---|
| AC-01 | `one command answers and names the parts that took part` | integration | Branch, tools, memory, guard — all in the answer |
| AC-02 | `every named part executes a non-zero number of its own lines` | integration | "Imports" separated from "uses" |
| AC-02b | `a part with zero executed lines reddens and is named` | integration | **FAILURE.** An `import` line is not assembly |
| AC-03 | `the price of assembly is two numbers in one unit` | unit | Adapters against what executed |
| AC-03b | `adapters stay under a fifth of what executed` | unit | **FAILURE.** The limit of the genre: above it, this is rewriting |
| AC-04 | `every adapter names the seam it closes` | unit | Two different parts in every seam |
| AC-04b | `an adapter that decides is refused` | unit | **FAILURE.** Whatever decides is a part |
| AC-05 | `five scenarios check the branch and the final state` | e2e | Not "something answered", but the trail left behind is right |
| AC-05b | `a failing part leaves the service alive and named` | e2e | **FAILURE.** A part failing ≠ the system falling over |
| AC-06 | `every decision cites a stage that exists` | contract | The citation is reconciled with the repository |
| AC-06b | `a dangling citation reddens and is named` | contract | **FAILURE.** A bibliography with no reconciliation ages silently |
| AC-07 | `a request without credentials is refused by the imported guard` | integration | **FAILURE.** The same code, not rewritten |
| AC-07b | `every wrap item names its source stage` | contract | Access, limits, budget, metrics, trace, backup |
| AC-08 | `latency numbers are printed with their conditions` | load | A number without its conditions is not a measurement |
| AC-08b | `a missing load tool yields not-evaluated, never a failure` | load | **FAILURE.** The third state with a named reason |
| AC-09 | `the stage 8 evaluator judges the capstone unchanged` | cross-context | The instrument works on a system that did not exist then |
| AC-10 | `the assembly report is not empty` | contract | An empty section is the most suspicious outcome |
| AC-11 | `all five scenarios run with no key and no network` | integration | **FAILURE.** The rule of nine stages is not broken by the tenth |
| AC-12 | `a broken adapter reddens the check about that seam` | unit | **FAILURE.** The mutation lands precisely |

**Integration test strategy.** The real dependency here is **the stages themselves**, and they are
not ephemeral: they are in the repository. So there is no faked stage anywhere: an adapter checked
against a mock of a part would prove a property of the mock. State is supplied from outside —
counters, storage, the tracer — exactly as the stage 6 service does it, so an integration test needs
neither containers nor a network. Traces are written into a temporary directory and cleaned up
**per test**.

**Data.** The five requests are pinned in `scenarios.py` together with the expected branch and the
expected final state. The model's answers come from a `FakeLLM` script, one per request: here,
unlike at stage 9, there is only one implementation, and a shared script is not needed.

**Placement in CI.** The whole suite is fast and offline — on every PR together with the rest of
`scripts/check_all.py`. The load run is **not** in CI: it needs a running service and yields a
machine-dependent number; there it stays `NOT EVALUATED`.

<!-- N/A: no NFR in §6 carries a throughput number; NFR-2 and NFR-2b are ceilings on run duration measured by an ordinary check, and the p50/p95 of AC-08 is not a requirement with a target -->

### What this plan deliberately does not prove

- **That the assembled service is better than the stage 6 service.** The capstone measures
  **assembly**, not answer quality: the latter is stage 8, which is used here rather than repeated.
- **That the latency numbers carry over to production.** The run is local, the model is fake, the
  machine is the author's. The conditions are printed next to the number, and a real deployment
  stays `NOT EVALUATED`.
- **That executed lines describe a stage in general.** They describe **this request** and **this
  thread**: both limits are inherited from the stage 9 instrument along with it.
- **That an adapter really "does not decide".** The check catches the crude cases — a branch inside
  an adapter — and relies on the named seam for the rest. "Does not decide" remains a property of
  intent, and that is named in ADR-0003.
- **That a justification is true in substance.** The check asserts that the source stage **exists**,
  not that it contains this particular decision. The second is impossible without understanding the
  text; the first already catches the whole class of errors that has occurred in this repository.
- **That five scenarios are coverage.** There are five, not fifty: the capstone shows assembly,
  while the case set lives at stage 8.

| AC-13 | `the http layer is stage 6 and not a second one` | unit | The capstone has no HTTP layer of its own |
| AC-13b | `the assembled service answers over http unchanged` | e2e | A foreign application refuses without a key and answers with one |
| AC-13c | `the live deploy stays not evaluated` | contract | A live deployment is the third state, not green |
| AC-01c | `one request is counted once and in one bucket` | integration | A part failing does not also add a success to the metrics |
| AC-02c | `the lesson numbers come from the run` | unit | The lesson's numbers are reconciled with the measurement, not typed by hand |
| AC-07c | `the budget guard has a witness` | integration | An exhausted limit stops the request; with no charge that reddens |

## 6. Non-functional requirements

| # | Requirement | Target | How it is measured |
|---|---|---|---|
| NFR-1 | Size of the **capstone** modules (`assemble.py`, `seams.py`, `service.py`, `scenarios.py`, `arch.py`, `latency.py`) | each ≤ 110 executable lines | an AST count in the check |
| NFR-2 | Running **`python -m stages.s10_capstone.check`** offline | ≤ 30 s with no key and no network | the `BUDGET_SECONDS` ceiling that `check_all` reads |
| NFR-2b | Running **`python -m stages.s10_capstone.run`** offline | ≤ 15 s; measured by a check that starts the demo | the measured time in the e2e check |
| NFR-3 | Length of the lesson | ≤ 2500 words | a word count in the check |
| NFR-4 | Share of checks on failure modes | ≥ 1/3, rounded up | a prefix count in the check |
| NFR-5 | A run with no optional packages and no key | green or `NOT EVALUATED`; nothing red | `scripts/clean_install.py` |
| NFR-6 | Determinism of the scenarios offline | twenty runs give the same branches and the same final states | a flakiness check |
| NFR-7 | Price of assembly | adapters ≤ 1/5 of what was imported | a count in the check, AC-03b |
| NFR-8 | Completeness of the justifications | 100 % of decisions have a source stage or stand in the own-decisions section | `ARCHITECTURE.md` parsed by the check |
| NFR-9 | Parts that **execute** on a request | ≥ 6 of nine give a non-zero line count | tracing of executed lines in the check |
| NFR-10 | Warm-up before the measurement | the work runs twice; lines that happen once per process do not enter the price of one request | a call counter in the check |

## 6.1 Security and privacy

- **No key is needed** to pass the stage: every scenario runs on the fake.
- **Retrieved text travels into the model behind the stage 2 fence** (`OPEN_DATA`/`CLOSE_DATA`): it
  is foreign text, and the boundary between it and the model's instructions must not depend on what
  is written inside it.
- **The guards are imported**, not rewritten. Access, the rate limit and the budget come from
  stage 6 together with their own checks; the capstone weakens none of them.
- **Traces do not carry the text of the user's request** wherever it can be left out: the capstone
  inherits the stage 8 rule that evaluation material is numbers and decisions.
- **A backup contains no secrets**: it holds data, not the environment, and the `RUNBOOK` says so
  directly.
- **A public endpoint has a budget breaker before the first deployment**, not after: a rule adopted
  back in the course design specification.

### Abuse

| Scenario | What breaks | What the stage does |
|---|---|---|
| A stage is named a part and does not execute | a list of imports passes presence off as work | tracing of executed lines; a zero reddens with the stage's name (AC-02b) |
| An adapter quietly adds behaviour | new logic lives outside a stage, with no lesson and no checks | an adapter that decides is a part (AC-04b) |
| A justification cites nowhere | the document ages silently | every citation is reconciled with the repository (AC-06b) |
| The "what it revealed" section is empty | the assembly report reports on no assembly | an empty section is named the most suspicious outcome (AC-10) |
| Numbers from the fake are passed off as production | the operator plans capacity from an invention | p50/p95 are printed together with their conditions (AC-08) |
| The last stage weakens the offline rule | nine stages held, the tenth broke it | every scenario runs with no key and no network (AC-11) |

## 7. KPIs

- The reader can name three seams between the parts and say why each one appeared.
- After a run, the reader states **their own** number: how many adapter lines against how many
  imported.
- The reader can open `ARCHITECTURE.md`, pick any decision and walk from it to the source stage.
- The reader has seen the stage 8 evaluator pass a verdict on a system that did not exist at
  stage 8.
- The reader can say what the assembly revealed as bad — and why that is normal.
- The Operator can name where every item of the wrap came from.

## 8. Open questions

- [x] Should voice (stage 7) be wired into the assembly? **No** — it stands in the list of parts
      deliberately not wired in, together with a reason; wiring it in adds no new conclusion and
      adds a dependency of gigabytes. Closed before the `stage-10` tag. — owner: Contributor
- [x] Should the load test run in CI? **No** — it needs a running machine and yields a number that
      depends on it. In CI it stays `NOT EVALUATED` (AC-08b, AC-13c), while the local p50/p95 are
      printed by scene 8 of the demo together with their conditions. Closed before the `stage-10`
      tag. — owner: Contributor
- [ ] Should the adapters be moved into `shared/`, in case anyone else needs them?
      Default now: no — an adapter exists for a particular seam, and moving it would make it a part
      with no stage. — owner: Contributor, due: after the course
- [x] Should p50/p95 be pinned in the prose of the lesson? **Yes, together with the conditions, and
      the conditions come before the number** — the order is asserted by a check (AC-08). The
      locality is stated directly. Closed before the `stage-10` tag. — owner: Contributor
- [x] Should the capstone have an HTTP layer of its own? **No** — `serve.py` takes stage 6's
      `create_app` and substitutes the assembled service into it (AC-13). The question arose during
      review: four documents promised a "second deploy" that did not exist, and no AC asked about
      it. — owner: Contributor

### Assumptions taken (depth `easy`)

Adopted without a separate question, because they are fixed in the course design specification:

1. **The domain is NovaShop**, the same as in every stage: support for an online shop.
2. **The model is a fake by default.** A real key only changes the text of the answers.
3. **One VM, self-hosted**, with no managed services — a stage 6 decision, not revisited.
4. **Assembly goes "top down"**: the service calls the parts, the parts know nothing of the service.
   The reverse direction would require changing the parts.
5. **Five scenarios, not fifty.** The capstone shows assembly, not coverage; the full case set lives
   at stage 8.
6. **`ARCHITECTURE.md` is in English**, like `RUNBOOK` and `COMPARISON` and like everything else
   committed here — a repository read by people who do not share one language is read in English or
   not at all (ADR-0008).
