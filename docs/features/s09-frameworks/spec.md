---
status: Draft
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
---

# Spec — s09-frameworks

> **Glossary:** [CONTEXT](../../../CONTEXT.md) (roles + domain objects), [GLOSSARY](../../../GLOSSARY.md) (the course's terms)
> **Reference module / docs / channels used:** `planning/2026-08-22-agentic-ai-course-design.md` §9 (s09) · `CURRICULUM.md` · `PLAYBOOK.md` · `stages/s03_router/` (a mini-graph of our own and a LangGraph one are already written) · `stages/s08_eval/` (the evaluator that will read this stage's traces) · `shared/llm.py` as the single provider boundary · source article #9 (Frameworks)

## 1. Context

Eight stages built a system **by hand**: the agent loop, retrieval, the router, tools, memory,
the service, voice, evaluation. Not once did the question most people start with come up:

> **"Which framework should I take?"**

That is not an accident, it is the design of the course. The question is asked **ninth** rather
than first, because it can only be answered once you have something to compare against.

The stage's main thesis comes from that same article:

> **A framework is scaffolding, not architecture.**

Scaffolding speeds up construction and says nothing about what you are building. Chosen before
the shape of the building is known, it **becomes** the shape — and that is exactly what happens
when the framework is the first decision.

The second thesis, and this one is operational:

> **Explicit coordination costs lines. Implicit coordination costs understanding.**

In LangGraph you draw the edges yourself: more code, and every transition is visible. In CrewAI
the agents delegate to one another based on role descriptions: less code, and the question "why
did this step run" stops having a cheap answer. Both trade-offs are legitimate; choosing between
them is choosing **a constraint**, not a taste.

**The stage's proof is numbers of your own, not a retelling.** The article makes a claim about
the ratio of code to control. The stage lets the reader measure the same thing on their own
machine — and your numbers will either confirm the claim or they will not. Either outcome is a
result; a stage that can only confirm is measuring nothing.

**Why the comparison is easy to make dishonest.** Three implementations of "the same task" are
comparable only when the task is fixed identically: the same input, the same model, the same set
of tools, the same stopping condition. Otherwise what is measured is **the author's fluency** in
each framework, not the frameworks. That is the stage's chief methodological risk, and it is
closed by a task contract shared by every implementation (§5, AC-02).

**The fourth column — no framework.** The thesis "scaffolding, not architecture" can only be
tested against a baseline with no scaffolding at all. Without it the comparison answers the
question "which framework is better" rather than the stage's question — "is a framework needed
here".

The baseline is written **here and from scratch**, and its size is the stage's first conclusion.
The temptation to take the stage 3 graph is strong and wrong: there it is a supervisor router
with routing and a revision loop, and here it is two sequential steps. Fitting one to the other
would mean comparing a task with a different task — that is, making exactly the mistake AC-02
warns against.

Decided at interview depth `easy`: the decisions are fixed in the course's design specification.
The assumptions taken are at the end of §8.

### The vocabulary of this specification

Four words are used precisely and are not interchangeable:

- **Implementation** — one way of carrying out the task contract. There are four: the baseline
  with no framework and three framework ones.
- **Task contract** — what is shared by every implementation: the input, the set of tools, the
  model, the stopping condition, the shape of the result. It is **executable**, not descriptive.
- **My line** — an executable line the implementation's author wrote and has to maintain. The
  framework's lines are not mine (§5, AC-03b).
- **Coordination** — whatever decides which step runs next. Explicit when that is visible in my
  code; implicit when the framework decides it from descriptions.

## 2. Goals

- With one command the reader gets a **comparison table with numbers of their own**, not a
  retelling of somebody else's comparison.
- The reader sees the same task carried out four ways and can point a finger at **exactly where**
  coordination lives in each.
- The reader can say how many lines they **really** wrote in each variant — and how many lines
  work invisibly on their behalf.
- The reader sees how many tokens each framework spends **of its own**, on top of what the author
  asked for.
- The reader can state the rule of choice as **constraint → tool** rather than as "the winner".
- The Contributor has a smoke test that catches a framework's API break **early**, not on the
  reader's run.
- The stage passes with no key at all; ADK without credentials is **skipped**, not failed.

## 3. Non-goals

- **We do not declare a winner.** An aggregate score would need weights, and weights are a hidden
  opinion about whose constraint matters more. The same ban as at stage 8.
- **We do not measure framework performance.** Latency here is decided by the model, not by the
  scaffolding; measuring it on a fake would mean measuring our own fake.
- **We do not teach any framework.** The implementations are deliberately **minimal**: exactly
  enough to carry out the contract. The stage is about choosing, not about mastery.
- **We do not compare ecosystems.** The number of integrations, stars and blog posts is not a
  property of the code, and this stage cannot measure it.
- **We do not rewrite stages 1–8.** Stage 3 remains the source of **the pattern** — it already
  shows what explicit coordination by hand looks like — but its code is not carried over here: if
  a stage had to be changed for the comparison's sake, it is the comparison that changes, not the
  stage.
- **We do not build production implementations.** None of the four has retries, a cache or
  circuit breakers: added trimmings would make the numbers incomparable, and the numbers are the
  stage's proof.

## 4. User stories

### US-01: a comparison from one command
**As** a Learner
**I want** to run every implementation with one command and get a table
**So that** I have **my own** numbers instead of somebody else's claim

### US-02: an honest comparison
**As** a Learner
**I want** every implementation to carry out **literally** the same task
**So that** a difference in the numbers means a difference between frameworks, not in my fluency

### US-03: the lines I actually write
**As** a Learner
**I want** to see how many lines I wrote, separately from what works invisibly
**So that** "less code" stops being an argument missing its other half

### US-04: the tokens a framework adds of its own
**As** an Operator
**I want** to see how many tokens each implementation spends above my request
**So that** I know the price of convenience before the bill arrives

### US-05: a baseline with no framework
**As** a Learner
**I want** to see a variant with **no** framework in the same table
**So that** I can answer "is one needed here", not only "which one"

### US-06: explicit versus implicit coordination
**As** a Learner
**I want** to ask each implementation, on one input, **why** this step ran
**So that** I feel the difference between explicit and implicit coordination as a price rather
than as a description

### US-07: ADK behind a flag
**As** a Contributor
**I want** the stage to pass without Google credentials
**So that** the absence of somebody else's key yields "not evaluated" rather than a red run

### US-08: an API break is visible early
**As** a Contributor
**I want** a smoke test of every implementation in the check suite
**So that** a framework's major version change breaks the run on my machine, not the reader's

### US-09: choosing by constraint
**As** a Learner
**I want** a recommendation in the form "constraint → tool"
**So that** I can choose for a task that is not in this table

### US-10: break it and see what goes red
**As** a Contributor
**I want** to break the implementations and see which check reacts
**So that** I know the smoke test has teeth and not merely a green verdict

## 5. Acceptance criteria

### AC-01 (US-01) — happy path

**Given** four implementations of the task contract
**When** the Learner starts the comparison with one command
**Then** they get a table naming, for **every** implementation: my lines, invisible lines, request
tokens, tokens above the request, the kind of coordination and the way to answer "why this step".
The table is written to a file a human reads and compares with the previous one

### AC-01b (US-01) — domain invariant

**Given** the written comparison table
**When** a check **parses the file** and counts again
**Then** its numbers agree with what the run produces. **Two independent sources** are compared —
the parsed file and the run's counters — because otherwise the equality is an identity and misses
the implementation that never made it into the table.

**There is no aggregate score** in the table and there cannot be: weights on constraints are an
opinion, not a measurement

### AC-02 (US-02) — domain invariant

**Given** the task contract: the input, the set of tools, the model, the stopping condition, the
shape of the result
**When** any of the four implementations runs
**Then** all five elements of the contract are **identical** for it, and that is proved by
**executing** a shared contract check rather than by reading the code.

An implementation that gives a different result on the same input is not another implementation
of the same task — it is a different task, and comparing them means measuring the author's fluency

### AC-02b (US-02) — error

**Given** an implementation that deviated from the contract — it called a different tool, stopped
on a different condition, or returned a different shape
**When** the harness builds the comparison
**Then** that implementation **does not enter the table** as a row with numbers; instead, the
element of the contract it violated is named.

Including such a row silently is worse than leaving it out: it produces a number that looks
comparable and is not

### AC-03 (US-03) — domain invariant

**Given** the four implementations
**When** the harness counts "my lines"
**Then** it counts them **the same way for all of them** — executable lines, excluding imports
and docstrings — and names invisible lines **separately**: how much framework code executes
during the run.

One number without the other turns "less code" into an argument missing its other half: the code
did not go away, it moved somewhere you cannot see it and cannot fix it

### AC-03b (US-03) — error

**Given** an implementation that imports a framework
**When** the harness counts my lines
**Then** the framework's own lines are **not included** in that number, and a check asserts it. A
counter that counts somebody else's package as mine gives the baseline an unearned advantage

### AC-04 (US-04) — happy path

**Given** a run of any implementation
**When** the harness counts tokens
**Then** it counts them **at the provider boundary** — where the request goes to the model — and
not inside the implementation's code, and it shows **two** numbers: what the author asked for and
what actually went out.

The difference between them is the price of the scaffolding: the framework's system prompts, its
role descriptions, its repeated resubmissions of the history

### AC-04b (US-04) — domain invariant

**Given** the overhead counter
**When** the harness feeds it a request carrying text the contract never specified — and,
separately, a baseline request that sends exactly the contract's texts
**Then** in the first case the overhead is **strictly positive**, in the second it **equals zero**.

The instrument is proved at **both ends**, not by hoping some framework will misbehave. Which
implementation adds how much is a **measurement** that goes into the table, not a property the
harness demands in advance.

The difference here is expected to be **unlike in kind**: an orchestrator that only decides the
order of nodes does not touch the request and adds zero tokens, paying in lines; a framework that
assembles prompts from role descriptions pays in tokens and saves lines. Both outcomes are
legitimate, and they are exactly what makes the conclusion "constraint → tool" rather than "the
winner"

### AC-04c (US-04) — cross-context

**Given** an offline run with the fake model
**When** the comparison is repeated twenty times
**Then** every number in the table is **the same**. Flickering numbers cannot be compared with
yesterday's, and comparing with yesterday's is the only reason to write them down

### AC-05 (US-05) — domain invariant

**Given** the comparison table
**When** the Learner reads it
**Then** it contains a row with **no framework at all**, obtained through the same task contract.

Without that row the table answers the question "which framework", while the stage asks a
different one: "is one needed here". The baseline is not a control group for form's sake, it is
the only way to see the price of the scaffolding

### AC-06 (US-06) — happy path

**Given** one and the same input
**When** the Learner asks each implementation **why** a particular step ran
**Then** each of them gives an answer, and the harness names **where** it came from: from my code,
from the trace, or from the framework's logs

### AC-06b (US-06) — error

**Given** an implementation with **implicit** coordination
**When** the step that ran was not the one the author expected
**Then** the harness shows this on a concrete input and names the price of the answer: how many
places have to be read to learn the reason.

This is the measurement of the difference between explicit and implicit coordination. The claim
"implicit is cheaper" without that number is half the truth, and it is exactly the half you pay
for later

### AC-07 (US-07) — authorization

**Given** a machine with no Google credentials
**When** the Learner runs the stage's checks
**Then** the ADK implementation yields the **not evaluated** state, the run stays green, and the
table carries that same state rather than an empty cell or a zero

### AC-07b (US-07) — error

**Given** the ADK flag turned on explicitly and the credentials **missing**
**When** the Learner starts the comparison
**Then** the harness says so **outright and immediately**, naming what is missing, rather than
silently showing a table of three rows.

A flag somebody was asked to turn on, which then silently did nothing, is worse than no flag at
all

### AC-08 (US-08) — error

**Given** an installed framework whose public API has changed
**When** the Contributor runs the check suite
**Then** **the smoke test of that very implementation** goes red, and its message names the call
that no longer exists. If the package is not installed, the state is **not evaluated**, not red

### AC-09 (US-09) — domain invariant

**Given** the comparison table
**When** the Learner looks in it for a recommendation
**Then** they find **no aggregate score** and no word "best". In their place is a list in the form
"if your constraint is this — take that", where every line cites the **column of the table** the
conclusion was drawn from

### AC-09b (US-09) — cross-context

**Given** a task that is not in the table
**When** the Learner applies the rule of choice
**Then** the rule gives an answer by leaning on the **measured** columns rather than on the names
of frameworks. A recommendation that cannot be applied outside this table is a retelling, not a
rule

### AC-10 (US-10) — error

**Given** a harness with a deliberately broken implementation
**When** the Contributor runs the checks
**Then** the check that asserts **about that very implementation** goes red, and its message names
what exactly broke

### AC-11 (US-02) — authorization

**Given** a machine with no API key at all
**When** the Learner starts the comparison
**Then** **none** of the four implementations reaches the network: all of them take their client
through the shared provider boundary, and a check asserts this by execution rather than by
reading the imports.

A framework that goes to the network with a client of its own, around that boundary, makes the
stage impassable offline — and does it silently

### AC-12 (US-04) — cross-context

**Given** the traces each of the four implementations writes
**When** the stage 8 evaluator extracts trajectories from them
**Then** it gets **more than one** trajectory per run, because the stage marks the run with a key
from its first line.

Stage 8 named as a number what the traces of stages 1–7 lack: three different fields across seven
stages, and four stages with no key at all. This is the first stage written **after** that
measurement — and it either uses it, or the measurement was not needed

## Test plan

Every criterion in §5 has at least one named test. The level is generalised; the concrete
functions live in `stages/s09_frameworks/check.py`.

| AC | Test | Level | What it proves |
|---|---|---|---|
| AC-01 | `one command yields a row per implementation` | integration | Four rows, six columns, the file is written |
| AC-01b | `the written table parses back to the same numbers` | unit | **FAILURE.** Two independent sources; no aggregate score |
| AC-02 | `all implementations honour the same task contract` | contract | The contract is executed, not read |
| AC-02b | `an implementation that breaks the contract gets no numbers` | contract | **FAILURE.** The violated element is named, the row carries no numbers |
| AC-03 | `my lines and invisible lines are two separate numbers` | unit | One number without the other is half an argument |
| AC-03b | `framework lines never count as mine` | unit | **FAILURE.** The baseline gets no unearned advantage |
| AC-04 | `tokens are counted at the provider boundary, both numbers` | integration | What the author asked for / what actually went out |
| AC-04b | `the overhead counter is proven at both ends` | unit | Strictly positive on somebody else's text, zero on the contract's own |
| AC-04c | `twenty offline runs give the same table` | unit | **FAILURE.** Flickering numbers cannot be compared with yesterday's |
| AC-05 | `exactly one row carries no framework` | unit | The question is "is one needed", not "which one" |
| AC-06 | `each implementation answers why a step ran, and names the source` | integration | From my code, from the trace, or from the framework's logs |
| AC-06b | `implicit coordination names the price of that answer` | integration | **FAILURE.** A number instead of the claim "cheaper" |
| AC-07 | `a missing package yields not-evaluated, never a failure` | integration | The third state has a row of its own in the table |
| AC-07b | `the flag on without credentials fails loudly` | integration | **FAILURE.** A silent flag is worse than no flag |
| AC-08 | `a changed framework API reddens that implementation's smoke` | contract | **FAILURE.** The call that no longer exists is named |
| AC-09 | `the table carries no aggregate score and no winner` | unit | Weights on constraints are an opinion, not a measurement |
| AC-09b | `every rule of choice cites a column of the table` | unit | The rule is applicable outside this table |
| AC-10 | `a broken implementation reddens the check that asserts about it` | unit | **FAILURE.** The mutation lands precisely |
| AC-11 | `no implementation reaches the network without a key` | integration | **FAILURE.** Proved by execution, not by reading the imports |
| AC-12 | `the stage 8 evaluator extracts more than one trajectory` | cross-context | A run key from the first line — a measured requirement put to use |

**Integration test strategy.** The real dependency here is **the framework package**, and it is
ephemeral in a different way from a container: it may simply not be there. Every integration test
starts with the question "is it installed", and the answer "no" gives `NOT EVALUATED` rather than
a skip or a green. There is no fake framework anywhere: an implementation on a LangGraph mock
would prove a property of the mock. Traces are written into a temporary directory and cleaned up
**per test**.

**Data.** The task's input is one and the same string for all four, fixed in the contract. The
model's answers come from a `FakeLLM` scenario shared by every implementation: different
scenarios would make the token counts incommensurable before the framework added anything at all.

**Placement in CI.** The whole suite is fast and offline — it runs on every PR along with the rest
of `scripts/check_all.py`. The job with extras additionally has the frameworks installed, so no
`NOT EVALUATED` there stays unjustified.

<!-- N/A: no NFR in §6 carries a throughput or under-load latency number; NFR-2 and NFR-2b are run-duration ceilings measured by an ordinary check -->

### What this plan deliberately does not prove

- **That one framework is better than another.** The plan measures six columns and does not weigh
  them. The conclusion takes the form "constraint → tool" (ADR-0005), and no test asserts an
  advantage.
- **That these numbers carry over to another task.** Invisible lines and tokens were measured on
  **this** input. Another task will execute other lines — that is a property of the measurement,
  named outright (ADR-0003).
- **That the fake model's numbers equal a real one's.** What is proved are **ratios**, not
  absolute values; with a real key both numbers change, not one of them.
- **That the CrewAI and ADK implementations work.** Both are written and **have never once been
  run**: CrewAI with the required API does not install on this interpreter, and ADK is turned off
  by the flag. Their rows stay `NOT EVALUATED`, and this is the stage's weakest point — named
  rather than hidden.
- **That CrewAI's token overhead is non-zero.** That is the stage's expectation, not a
  measurement, and all the prose about it uses the conditional. It is checked on Python ≤ 3.13.
- **That the AC-06b event is observable here.** "The step that ran was not the one the author
  expected" requires an implementation with **implicit** coordination that has actually been run,
  and there is none on this interpreter. What stays measured is the price of the answer — the "prose places", read
  from the source; the event itself is reproduced on Python ≤ 3.13.
- **That the frameworks will not break on the next version.** The smoke test catches a break
  **after** the upgrade, it does not predict it. Pinning by a minor bound narrows the window but
  does not close it.
- **That my implementation on a framework is the best one possible.** The contract makes the
  implementations equally **on-task**, not equally skilful. A clumsy LangGraph will give an honest
  number for a clumsy LangGraph (ADR-0001).

## 6. Non-functional requirements

| # | Requirement | Target | How it is measured |
|---|---|---|---|
| NFR-1 | The size of the **implementation** modules (`contract.py`, `baseline.py`, `counters.py`, `compare.py` and one module per framework; `run.py` and `check.py` do not count) | each ≤ 110 executable lines | AST count in a check |
| NFR-2 | Running **`python -m stages.s09_frameworks.check`** offline | ≤ 30 s with no key and no network | the `BUDGET_SECONDS` ceiling, read by `check_all` |
| NFR-2b | Running **`python -m stages.s09_frameworks.run`** offline | ≤ 10 s; measured by a check that starts the demo | the time measured in the e2e check |
| NFR-3 | Lesson length | ≤ 2500 words | a count in a check |
| NFR-4 | The fraction of checks covering failure modes | ≥ 1/3, rounding up | a prefix count in a check |
| NFR-5 | A run with no optional packages and no key | green or `NOT EVALUATED`; not a single red | `scripts/clean_install.py` |
| NFR-6 | Determinism of the table **offline** | twenty runs give the same numbers (not byte-identical files: time is excluded from the comparison) | the flakiness check |
| NFR-7 | Completeness of the comparison | ≥ 4 implementations, exactly one of them **without** a framework | a count in a check |
| NFR-8 | Framework versions are **pinned by an upper bound**, as in `s04` and `s06` | the next major version does not arrive silently; an API break is caught by this stage's smoke test | a check verifying the upper bound in `pyproject.toml` |

## 6.1 Security and privacy

- **No key is needed** to pass the stage. Without one, all four implementations run on the fake
  model, and the numbers stay comparable with each other.
- **Google credentials reach neither the table, nor the trace, nor the demo output.** Missing
  credentials yield the "not evaluated" state naming what is missing — with none of the
  environment's contents.
- **The token counter stores no request text.** It counts at the provider boundary and writes
  numbers down; the framework prompts it sees never reach the comparison material.
- **No implementation creates a provider client of its own** — all of them take it through the
  shared boundary (AC-11). A framework that goes around it makes both the offline run and the
  token accounting impossible.
- **The network is needed neither for the run nor for the checks.** Framework packages are
  optional; their absence yields "not evaluated".

### Abuse

| Scenario | What breaks | What the stage does |
|---|---|---|
| The comparison declares a winner | choice is replaced by fashion | no aggregate score; a rule in the form "constraint → tool" (AC-09) |
| The implementations carry out different tasks | the table measures the author's fluency | a task contract, shared and **executable** (AC-02) |
| "Less code" without its other half | the code moved somewhere you cannot see it | my lines and invisible lines are two columns (AC-03) |
| Tokens are counted inside the implementation's code | the framework's overhead is invisible | a counter at the provider boundary (AC-04) |
| ADK silently drops out of the table | three rows look like all of them | the flag on without credentials is a loud refusal (AC-07b) |
| A framework goes to the network with a client of its own | the stage is impassable offline, the token accounting is incomplete | a check by execution, not by reading the imports (AC-11) |

## 7. KPIs

- The reader can name exactly where coordination lives in each of the four implementations.
- After a run the reader names a number of **their own**: how many tokens the framework added of
  its own.
- The reader can say how many lines they wrote and how many work invisibly on their behalf.
- The reader states the rule of choice as "constraint → tool" and applies it to a task that is not
  in the table.
- The reader can say why a baseline with no framework stands in the same table.
- The Contributor can name which framework call will break first on a version change.

## 8. Open questions

- [ ] Should a fifth implementation be added (a bare provider call with no coordination at all,
      for instance)? Default now: no — four are enough to show both ends of the scale; a fifth
      would add a column without a new conclusion.
      — owner: Contributor, due: before the `stage-09` tag
- [ ] Should run time be measured alongside tokens? Default now: no — on a fake model, time
      measures the fake rather than the framework (§3). Return to the question only with a real
      key. — owner: Contributor, due: stage 10
- [ ] Should the token counter move into `shared/` so that stage 10 gets it ready-made?
      Default now: it stays in stage 9; moving it is a stage 10 decision, once the need is real.
      — owner: Contributor, due: stage 10
- [ ] Should "invisible lines" be fixed as a number or as an order of magnitude? Default now: as a
      number, with the counting method named outright and its limit named outright — it depends on
      how much framework code **executed**, not on how much of it is installed.
      — owner: Contributor, due: before the `stage-09` tag

### Deferred after the review (2026-08-25)

Two independent reviews in a clean context produced sixteen MAJOR and nineteen MINOR findings.
Every MAJOR is closed; below is what was deliberately deferred, with an owner and a deadline.

- [ ] **`sys.settrace` does not see other threads.** An implementation that does its work in a
      separate thread would silently give zero invisible lines. The nearest candidate is ADK,
      whose synchronous runner is a wrapper around an asynchronous one.
      Default now: the limit is named in the `executed_lines` docstring, and the check
      `row.invisible > 0` catches a zero on any implementation that actually ran.
      — owner: Contributor, due: stage 10
- [ ] **The warm-up doubles the runs, and the determinism check multiplies that by twenty.**
      Today that is 2 s against a ceiling of 30; on Python ≤ 3.13 forty `crew.kickoff()` calls
      will be added.
      Default now: it stays — a warm-up done once per module would make the check
      order-dependent. — owner: Contributor, due: stage 10
- [ ] **The demo's `≤ 10 s` ceiling is a constant, not derived from anything measured.**
      Default now: it stays as a budget against sprawl rather than as a performance target (the
      same role `BUDGET_SECONDS` plays). — owner: Contributor, due: stage 10
- [ ] **The CrewAI and ADK implementations have never been run.** The first has no usable version
      for this interpreter, the second is turned off by the flag.
      Default now: `NOT EVALUATED` with a named cause; all the prose about them is in the
      conditional. — owner: Contributor, due: stage 10

### Assumptions taken (depth `easy`)

Taken without a separate question, because they are fixed in the course's design specification:

1. **The task is research → writer**, as in the source article: one step gathers the material, the
   second writes the answer from it. Two steps are enough to make coordination visible.
2. **The three frameworks are exactly these** — LangGraph, CrewAI, Google ADK — per the course's
   design spec.
3. **ADK behind a flag.** It needs somebody else's credentials, so the default is off, and the
   "not evaluated" state is a full row of the table.
4. **The implementations are minimal.** Exactly enough code to carry out the contract: added
   trimmings would make the numbers incomparable.
5. **The baseline is written from scratch and is deliberately minimal.** The stage 3 graph is not
   carried over: there it is a supervisor router, here two sequential steps, and fitting one to
   the other would violate the task contract. Its size is the table's first number, not an
   implementation detail.
6. **The model is a fake by default.** A real key only changes the numbers; the stage's
   conclusions are about ratios, not about absolute values.
