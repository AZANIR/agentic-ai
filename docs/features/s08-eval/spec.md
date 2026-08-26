---
status: Draft
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
---

# Spec — s08-eval

> **Glossary:** [CONTEXT](../../../CONTEXT.md) (roles + domain objects), [GLOSSARY](../../../GLOSSARY.md) (the course's terms)
> **Reference module / docs / channels used:** `planning/2026-08-22-agentic-ai-course-design.md` §9 (s08) · `CURRICULUM.md` · `PLAYBOOK.md` · `shared/trace.py` as the data source that already exists · `docs/features/s06-platform/adr/0005` and `0008` (promises carried over to here) · the stage 6 service as a source of live traffic · source article #8 (Agent Evaluation)

## 1. Context

Seven stages built a system. The question "does it work" still has the same answer it had before
the first line of code: **"I ran it a few times, seems fine"**.

Stage 6 gave metrics: is the service alive, how long does it answer, what does it cost. Stage 7
gave latency numbers. Neither of them answers the other question:

> **Infrastructure tells you whether the system works. Evaluation tells you whether its decisions
> are good. These are different questions, and a service with flawless uptime can answer wrongly
> with great confidence.**

The stage's main thesis comes from that same article, and it is not about metrics:

> **What has to be evaluated is the path, not only the destination.**

An agent can call every tool correctly, retrieve the right documents, reason sensibly at every
step — and fail the task. Or it can stumble, call the wrong tool, wriggle out of it and give the
right answer. **If you look only at the last message, those two cases look identical.** One was a
lucky accident, the other was engineering.

The second thesis the article does not state, and it is specific to this repository:

> **A judge model is a measuring instrument, and instruments get calibrated.** An evaluator that
> declares the judge's verdict to be the truth has made exactly the mistake the whole stage warns
> against: it trusted a number without asking where it came from.

So the stage's proof is not "we assigned scores" but **a bias caught in the act**: swapping two
answers around changes the verdict, and the reader sees it in numbers of their own.

**Why this is possible offline.** The fake judge is biased **on purpose** — the same way the
mutations of stages 1–7 break a property on purpose. It does not prove that real judges are
biased (other people's research proves that, and the article cites it); it gives the detector
**something to detect**. With a real key the same detector runs against a real model and produces
the same report.

**Two promises carried over to here.** Stage 6 deferred a decision to this stage twice:
`adr/0005` — "stage 8 will say what it actually lacks in the trace"; `adr/0008` — "the
requirement on the trace store will be stated by whoever reads them". Both are kept here (§8, the
stage's ADR-0008 and ADR-0009), and they are kept **by measurement** rather than by guess.

Decided at interview depth `easy`: the decisions are fixed in the course's design specification.
The assumptions taken are at the end of §5.

### The vocabulary of this specification

Three words are used precisely and are not interchangeable:

- **Evaluator** — a harness component that delivers a level's verdict. Evaluators are either
  deterministic or they judge.
- **Check** — an `assert` function in `check.py` that proves a property of the harness. This is
  the `Stage check` from [CONTEXT.md](../../../CONTEXT.md).
- **Trajectory** — the maximal set of trace steps sharing a **run key**. Which key that is
  belongs to the source, not to the evaluator (§5, AC-11).

## 2. Goals

- With one command the reader gets a **report** in which "does it work" is numbers across three
  levels rather than an impression.
- The reader sees the difference between "arrived correctly" and "arrived by accident" on
  concrete cases.
- The reader can say when a judge model is justified and when it is an expensive replacement
  for `==`.
- The reader sees, **on data of their own**, how swapping two answers around changes the judge's
  verdict, and how a longer answer beats a shorter one with no gain in quality.
- The Operator understands the online evaluation scheme: cheap checks over all traffic, the judge
  over a limited fraction, and why it is arranged that way.
- The reader sees that "unscored" is a third state rather than a silent failure or a silent
  success.
- The repository gets a **measured** answer to the question of what the evaluator lacks in the
  trace.

## 3. Non-goals

- **We are not building an evaluation platform.** No web interface, no results database; the
  report is a file a human reads and compares with the previous one.
- **We are not measuring model quality.** The stage evaluates **the agent** — its decisions and
  its path — not which provider writes better text.
- **We are not doing significance statistics.** Twenty cases give no confidence intervals, and
  pretending otherwise is worse than not counting them at all. Hence the deterministic sampler
  too (ADR-0007): the verification margin is an exact number, not an interval.
- **We are not tracking drift over time.** Drift needs **stored history**, which the first item
  on this list rules out. The stage prints the numbers drift monitoring lacks (fractions by
  window) and stops there; comparing windows over time is stage 10.
- **We are not proving that real judges are biased.** The literature shows that; the stage
  provides **the detection instrument** and demonstrates it on a judge whose behaviour is known.
- **We are not rewriting stages 1–7.** The harness reads traces that are already being written.
  What the trace lacks is **named** (§8, the stage's ADR-0008) and fixed where the stages are
  being reassembled anyway — at stage 10.
- **We put no part of evaluation in the hot path.** Neither the judge nor the cheap checks:
  everything runs **out of band**, reading the trace after the response. The service whose
  latency stage 7 just spent a whole stage measuring does not get an unmeasured addend.

## 4. User stories

### US-01: a report from one command
**As** a Learner
**I want** to run the whole evaluation suite with one command and get a report
**So that** the question "does it work" has an answer in numbers rather than in impressions

### US-02: evaluation on top of existing traces
**As** a Learner
**I want** the harness to read the traces stages 1–7 already write
**So that** I see why tracing was added at the first stage and not at the eighth

### US-03: three levels, separately
**As** a Learner
**I want** to see e2e, trajectory and component as separate verdicts
**So that** "it broke" answers the question "where" and not only "whether"

### US-04: a deterministic evaluator versus a judge
**As** a Learner
**I want** every evaluator to declare explicitly whether it is deterministic or judges
**So that** I learn not to pay for a judge where a comparison is enough

### US-05: position bias on my own data
**As** a Learner
**I want** to swap two answers around and see that the verdict changed
**So that** I understand bias from my own run rather than from a retelling

### US-06: length bias on my own data
**As** a Learner
**I want** to see a longer answer beat a shorter one with no gain in quality
**So that** I know what the judge is actually scoring when it looks like it is scoring quality

### US-07: online evaluation and sampling
**As** an Operator
**I want** cheap checks over all traffic and the judge over a limited fraction
**So that** I have the numbers drift is later computed from, without paying to judge every
request

### US-08: the third state
**As** a Learner
**I want** an unavailable judge to yield "unscored" rather than "failed"
**So that** I can tell broken from unchecked

### US-09: break it and see what goes red
**As** a Contributor
**I want** to break the harness and see which check reacts
**So that** I know the checks have teeth and not merely the right verdict

### US-10: name what the trace lacks
**As** a Contributor
**I want** a **measured** list of what the evaluator lacks in the existing traces
**So that** the promise stage 6 deferred here twice is kept

## 5. Acceptance criteria

### AC-01 (US-01) — happy path

**Given** an evaluation case set and the traces generated from it
**When** the Learner starts evaluation with one command
**Then** they get a report in which every case carries a verdict for **each of the three levels**
and the evaluator's kind beside each verdict, with the summaries at the bottom. The report is
written to a file that a human reads and compares with the previous one

### AC-01b (US-01) — domain invariant

**Given** the written report
**When** a check **parses the file** and counts the rows again
**Then** its numbers agree with the summaries printed in the report. **Two independent sources**
are compared — the parsed file and the run's counters — because otherwise the equality is an
identity and misses the case that never made it into the report.

**The denominator is all cases**, not only the scored ones: a passed fraction computed over the
scored ones **grows** when the judge falls over

### AC-02 (US-02) — cross-context

**Given** the traces stages 1–7 wrote during their own runs
**When** the harness reads them
**Then** evaluation happens **without a single change in those stages**. A stage that had to be
instrumented for the sake of evaluation would prove that tracing was added too late

### AC-02b (US-02) — authorization

**Given** the trace file the harness is about to read
**When** the evaluation run has finished
**Then** that file is **byte-identical**: neither appended to nor rewritten. The evaluation run's
own trace is written to **a separate path**, given explicitly; by default the evaluator writes
nothing into the shared daily file — otherwise the second run would find the first run's trace
among its inputs and start evaluating the evaluator

### AC-03 (US-03) — happy path

**Given** two cases with **the same correct** answer: the first describes the direct path, the
second a redundant loop and a call to the wrong tool; both are **generated** from their own
descriptions through `shared.trace`, so the traces are real
**When** the harness evaluates them
**Then** their verdicts **differ**: e2e agrees, the trajectory does not. An evaluator for which
these two cases are the same does not tell engineering from a lucky accident

### AC-03b (US-03) — domain invariant

**Given** any case
**When** the Learner looks at its row in the report
**Then** the verdicts of the three levels are **independent**: a case can pass one level and fail
another, and the report shows both. A single combined score would hide exactly what having three
levels is for.

**The rule for assigning a defect to a level is one rule, and it is unambiguous:**

    e2e         about the LAST answer and nothing else
    trajectory  about the SEQUENCE of steps: order, count, redundant calls
    component   about ONE step and its own result: it errored, it refused, it came back empty

### AC-03c (US-03) — error

**Given** a run in which an individual step ended in an error or a refusal
**When** the harness reports a failure at the component level
**Then** it names **the step** — its kind and its ordinal — and not only the case. "The agent
answered badly" is the only information an evaluator without a component level gives, and it does
not say what to do about it

### AC-03d (US-03) — error

**Given** a trace that has **no steps at all** of the component's kind
**When** the harness evaluates the component level
**Then** its verdict is **unscored**, not "passed". A level that silently counts missing data as
a success shows a greener report the poorer the trace is

### AC-04 (US-04) — domain invariant

**Given** the list of the harness's evaluators
**When** the Learner looks at the report
**Then** beside every verdict stands **the evaluator's kind**: deterministic or judges.

The second half is **machine-checked**, not an understanding: the judge-call counter reads
**zero** for every deterministic evaluator, and the total number of calls in a run equals the
number of evaluators that judge. The judge is not called "just in case"

### AC-05 (US-05) — error

**Given** a pair of answers to the same task and a judge that works **pairwise**: it takes two
answers in a given order and returns one of three things — the first won, the second won, a tie
**When** the harness submits the same pair **twice** — in the order AB and in the order BA
**Then** it counts as a **flip** the case where the content that won in the first order is not
the content that won in the second (a tie is a value of its own, not the absence of a verdict),
and it reports this as **a bias finding**, not as a score.

The pairs are taken from **a separate list of pairs** belonging to the stage rather than from the
suite's cases: a bias finding is a property of **the judge**, and mixing it in with the agent's
quality would mean blaming the agent for the instrument's behaviour

### AC-05b (US-05) — domain invariant

**Given** a judge whose verdict does **not** depend on the order
**When** the harness runs the same detector on the same pairs
**Then** it reports **agreement**: zero flips. A detector that always finds bias cannot tell a
biased judge from an honest one and is therefore not a detector

### AC-06 (US-06) — error

**Given** a pair of answers to the same task: the short correct one, and **the same** correct one
padded with truthful but redundant text, and a judge that works **pointwise**: it gives each
answer a whole score on a declared scale
**When** the judge scores both
**Then** the harness shows **the difference of scores as a number** and counts **any strictly
positive** difference as a length bias finding.

No threshold is needed here and one would be a mistake: both answers are correct, the second
differs only by redundant text, so **any** preference for the longer one is a point for length

### AC-07 (US-07) — happy path

**Given** a recorded service trace
**When** online evaluation is turned on
**Then** the cheap deterministic checks run on **every request trajectory** in the trace, the
judge on a limited fraction, and **both numbers are named**. All of it happens **out of band**,
after the response: no evaluation step stands between the request and the response.

The limit is named outright: a request that never reached the tracer is not evaluated **at all**,
and the harness reports how many such requests there were if it can know that

### AC-07b (US-07) — authorization

**Given** a user request containing sensitive text
**When** it is selected into the sample
**Then** **the evaluation material** — the written report and the run's own trace — contains
neither the request text nor the text of the user's answer.

The answers used in the **bias demonstration** are not covered by that ban: the stage's author
wrote them as fixtures, they belong to no user, and without them the demonstration would lose the
thing it exists for

### AC-07c (US-07) — domain invariant

**Given** a declared sampling fraction and a stream of request identifiers
**When** the whole stream has passed through the sampler
**Then** the actual fraction **matches the declared one** within **±3 percentage points** on a
stream of two hundred identifiers or more — and the margin is named here, in the specification, rather than chosen by the harness.

The selection is **deterministic**: the same identifier always yields the same decision, and the
same stream the same fraction. Random selection would make the check flaky, and its tolerance
would have to be widened so far that it would stop telling 10 % from 1 %

### AC-08 (US-08) — error

**Given** a case for which the judge is unavailable
**When** the harness reports
**Then** its state is **unscored**, and that state is counted separately from passed and failed.

"Unavailable" is a closed list: no key configured, the provider refused on quota or rate, the
budget is exhausted, a timeout elapsed, the judge's answer is unparseable. Everything else is a
failure.

The mirror half: a run in which **everything** ended up unscored is not a success — the report
says so outright rather than showing empty green

### AC-09 (US-09) — error

**Given** a harness with a deliberately broken evaluation level
**When** the Learner runs the checks
**Then** the check that asserts **about that very level** goes red, and its message names what
exactly broke

### AC-10 (US-01) — domain invariant

**Given** the case set
**When** a check counts its composition
**Then** at least a third are **edge cases**, and edge-ness is derived from an **observable
property** of the case: a refusal is expected, arguments were rejected, a limit was exhausted, the
result was empty, or the tool was unknown. There is no self-declared label — otherwise the NFR is
satisfied by flipping a flag, and a set of twenty happy paths stays green.

The third is taken **rounding up**: on twenty cases that is seven, not six

### AC-11 (US-03) — cross-context

**Given** a trace of a stage 1 agent run and a trace of a stage 6 service run
**When** the harness extracts trajectories from both
**Then** it does so with **the same code**, receiving **the run key as a parameter**.

The source decides the key, not the evaluator: stage 1 groups by trace identifier, the stage 6
service by request identifier. The mirror half, without which the claim is empty: on the stage 6
trace there is **more than one** trajectory. A grouping that collapses the whole service file
into one trajectory formally "works" and computes its summaries over a single row

### AC-12 (US-10) — cross-context

**Given** the traces of every existing stage
**When** the harness tries to extract trajectories from them all one way
**Then** it **names as a number** what it lacks, and that list goes into the lesson.

Measured, not assumed: **the list is computed from the sources** rather than sitting in prose. A
number that describes what a measurement lacks must not itself be a guess — and the first draft of
this sentence was one: it counted stage 4's refusal phase as a run key and skipped stage 7. This
is the answer to the question stage 6 deferred here twice

## Test plan

Every criterion in §5 has at least one named test. The level is generalised; the concrete
functions live in `stages/s08_eval/check.py`, and no tool name is fixed here.

| AC | Test | Level | What it proves |
|---|---|---|---|
| AC-01 | `one case yields three verdicts and three evaluator kinds` | unit | Three levels side by side, the evaluator's kind beside each |
| AC-01b | `the written report parses back to the same totals` | unit | **FAILURE.** Two independent sources; the denominator is all cases |
| AC-02 | `stage traces are read exactly as the stages wrote them` | integration | Not one edit in stages 1–7 |
| AC-02b | `the input trace file is byte-identical after a run` | integration | **FAILURE.** The evaluator does not write into what it evaluates |
| AC-03 | `same answer, different paths, different verdicts` | unit | e2e agrees, the trajectory does not |
| AC-03b | `a case passes one level and fails another in the same row` | unit | The verdicts are independent; there is no combined score |
| AC-03c | `a failed step is named by its kind and ordinal` | unit | **FAILURE.** The step is named, not only the case |
| AC-03d | `a trace without steps of that kind is not evaluated` | unit | **FAILURE.** The third state instead of a silent "passed" |
| AC-04 | `deterministic evaluators call the judge zero times` | unit | A counter of calls, not an understanding |
| AC-05 | `swapping the order flips the winner` | unit | **FAILURE.** Position bias — a finding about the instrument |
| AC-05b | `a stable judge yields zero flips` | unit | The mirror half: a detector that always fires is not a detector |
| AC-06 | `padding a correct answer raises its score` | unit | **FAILURE.** Length bias as a number; there is no threshold and cannot be |
| AC-07 | `cheap checks cover every trajectory, the judge only a share` | integration | Both numbers named; all of it out of band |
| AC-07b | `neither request nor answer text reaches the report or the trace` | unit | **FAILURE.** Evaluation material with no user text |
| AC-07c | `the sampled share matches the declared one within the stated margin` | unit | The selection is deterministic; the margin comes from the spec, not the harness |
| AC-08 | `an unavailable judge yields not-evaluated, never a failure` | unit | **FAILURE.** A closed list of causes; wall-to-wall "unscored" is not a success |
| AC-09 | `a broken level reddens the check that asserts about that level` | unit | **FAILURE.** The mutation lands precisely, not just anywhere |
| AC-10 | `at least a third of the case set is edge by observation` | unit | Edge-ness is derived from an observable property, not from a label |
| AC-11 | `one grouping-key parameter serves both stage 1 and the stage 6 service` | integration | The mirror half: on the service there is more than one trajectory |
| AC-12 | `what the traces lack is counted, not assumed` | integration | Four different run fields, two stages with none at all |

**Integration test strategy.** The real dependency here is **the trace file**, not a database:
`TRACE_SINK=jsonl` is the only sink implementation (ADR-0009). Every integration test generates
its own trace into a temporary directory through the same `shared.trace` the stages use, and
cleans up after itself. The cleanup boundary is **per test**, not per suite: a shared file would
make the runs order-dependent. There is no fake store anywhere — a trace that went around
`shared.trace` would prove a property of a format the repository does not have.

**Data.** Cases are **generated from descriptions** (ADR-0005) rather than read from recorded
fixtures. The only things that stay fixtures are the bias demonstration's answers: they are input
to **the instrument**, not user data, and that is exactly why §6.1 exempts them from the ban on
text.

**Placement in CI.** The whole suite is fast and offline — it runs on every PR along with the
rest of `scripts/check_all.py`. The stage has no separate slow suite: a check that needs the
network is broken, not slow.

<!-- N/A: no NFR in §6 carries a throughput or under-load latency number; NFR-2 and NFR-2b are run-duration ceilings measured by an ordinary check -->

### What this plan deliberately does not prove

- **That a judge model judges correctly.** By default the judge is a fake with a **declared**
  bias. The stage's proof is about the detector and the instrument, not about the quality of a
  particular model; with a real key the same detector runs against a real model and produces the
  same report.
- **That the agent of the earlier stages is good.** Twenty cases are a teaching set, not a
  benchmark: they show **what to measure**, and deliberately give no confidence intervals (§3).
- **That sampling holds the fraction on a real deployment.** It is checked locally, in the same
  process; a real deployment stays `NOT EVALUATED` (§8, assumption 4).
- **That ±3 percentage points is the right margin for production.** It is the margin of **an
  exercise** on a stream of two hundred identifiers or more. The real one depends on the volume of
  traffic and the price of a judgement.
- **That the report is deterministic with a real judge.** NFR-6b lifts that requirement outright:
  with a key, the flakiness check becomes `NOT EVALUATED` rather than green.
- **That the list of "unavailable" causes is exhaustive forever.** It is closed **as of today**
  (AC-08); a new provider refusal will enter it by an edit, and until then it will read as a
  failure — deliberately loudly.

## 6. Non-functional requirements

| # | Requirement | Target | How it is measured |
|---|---|---|---|
| NFR-1 | The size of the **implementation** modules — `trajectory.py`, `cases.py`, `levels.py`, `judge.py`, `bias.py`, `report.py`, `online.py` (`run.py` and `check.py` do not count: the first is the demo, the second is the set of checks) | each ≤ 110 executable lines | AST count in a check |
| NFR-2 | Running **`python -m stages.s08_eval.check`** offline | ≤ 30 s with no key and no network | the `BUDGET_SECONDS` ceiling, read by `check_all` |
| NFR-2b | Running **`python -m stages.s08_eval.run`** offline | ≤ 10 s; measured by a check that starts the demo | the time measured in the e2e check |
| NFR-3 | Lesson length | ≤ 2500 words | a count in a check |
| NFR-4 | The fraction of checks covering failure modes | ≥ 1/3, rounding up | a prefix count in a check |
| NFR-5 | A run with no optional packages and no key | green or `NOT EVALUATED`; not a single red | `scripts/clean_install.py` |
| NFR-6 | Determinism of the report **offline, with the fake judge** | twenty runs give the same **verdicts and summaries** (not byte-identical files: identifiers and time are excluded from the comparison) | the flakiness check |
| NFR-6b | Determinism **with a real judge** | not required; with a key the flakiness check becomes `NOT EVALUATED` | the same check, a different branch |
| NFR-7 | The size of the case set | ≥ 20 cases, of which ≥ 1/3 are edge cases (rounding up) | a count in a check, by observable property |

## 6.1 Security and privacy

- **Evaluation reads, it does not write** into what it evaluates: the trace file is byte-identical
  (AC-02b).
- **Its own trace goes to a separate path.** The evaluator leaves the shared daily file alone by
  default: otherwise the next run evaluates the previous one.
- **The evaluation material** is the written report and the run's own trace. They carry neither
  the request text nor the text of the user's answer (AC-07b). The fixture answers of the bias
  demonstration were written by the stage's author — they are not user data.
- **No part of evaluation stands in the hot path** — neither the judge nor the cheap checks.
- **A provider key is not required** to pass the stage; without one, the judge yields the
  "unscored" state rather than an error.

### Abuse

| Scenario | What breaks | What the stage does |
|---|---|---|
| The evaluator reports an average score and hides the spread | "green" comes to mean "tolerable on average" | three levels separately, "unscored" as its own state |
| The judge scores its own style instead of quality | the score drifts from correctness towards similarity | the bias detector as part of the suite, not as an option |
| The set consists of happy paths | a high score that proves nothing | edge-ness derived from an observable property (AC-10) |
| Sampling is declared but never verified | the real fraction is a different one | deterministic selection and the ±3 pp margin in the spec (AC-07c) |
| An empty trace gives a green component level | the poorer the trace, the better the report | no steps → "unscored" (AC-03d) |
| The passed fraction is taken over the scored ones | it grows when the judge falls over | the denominator is all cases (AC-01b) |

## 7. KPIs

- The reader can name the three levels of evaluation and say what each one sees that the other
  two do not.
- After a run the reader names a number of **their own**: how many cases failed the trajectory
  while giving the right answer.
- The reader can state the "deterministic evaluator versus judge" rule in one sentence.
- The reader has seen a swap of answers change the verdict — on a run of their own.
- The reader can say why "unscored" is counted separately and why the denominator is all cases.
- The Contributor can name what the traces lack for evaluation, and where that gets fixed.

## 8. Open questions

- [ ] Should sampling be checked against a real deployment or against a local stage 6 service?
      Default now: locally, in the same process; a real deployment is `NOT EVALUATED`.
      — owner: Contributor, due: before the `stage-08` tag
- [ ] Is a separate machine-readable report format needed alongside the human one?
      Default now: one file a human reads; machine reading is stage 10, if it turns out to be
      needed. — owner: Contributor, due: stage 10
- [ ] Should the bias detector move into `shared/` so that stage 10 gets it ready-made?
      Default now: it stays in stage 8; moving it is a stage 10 decision, once the need is real.
      — owner: Contributor, due: stage 10
- [ ] A shared "run key" field in `shared/trace.py` instead of four different names — when?
      Default now: the requirement is **stated** here (AC-12, the stage's ADR-0008), and the
      change is made at stage 10, where the stages are being reassembled anyway: editing
      `shared/trace.py` touches all seven stages and would violate this stage's constraint.
      — owner: Contributor, due: stage 10

### Deferred after the review (2026-08-25)

Two independent reviews in a clean context produced sixteen MAJOR and eighteen MINOR findings.
Every MAJOR is closed; below is what was deliberately deferred, with an owner and a deadline.

- [ ] **Dead code in modules that have a line limit.** `Watch.within()` (`online.py`) implements
      AC-07c literally, but is called nowhere: the check counts `sampled()` on a synthetic stream.
      The same goes for `Trajectory.of_kind` outside `tools()`.
      Default now: it stays — `within()` now measures the **selected** rather than the scored, and
      an online reader needs it; wiring it into a check comes with the first real service.
      — owner: Contributor, due: stage 10
- [ ] **A long meaningless answer passes e2e by construction.** `PASS_SCORE = 2` and
      `CHARS_PER_POINT = 40` give a passing score for 80 characters of noise. No current case
      shows this (every passing one has ≥2 points on content), but nothing holds the ratio in
      place.
      Default now: it stays as **a demonstration of the stage's own thesis**; the assert "no case
      passes on the padding alone" comes when the twenty-second case appears.
      — owner: Contributor, due: stage 10
- [ ] **`EDGE_KINDS` and `BROKEN_KINDS` disagree about `specialist_failed`.** The case "routed to
      the wrong place, recovered" fails the component level and is not counted as an edge case.
      Default now: it stays — edge-ness describes the set's **input data**, brokenness describes
      the **result** of a run, and a matching pair of lists would be a coincidence.
      — owner: Contributor, due: stage 10
- [ ] **The online part does not bring up a real stage 6 service.** The checks read real traces
      from `traces/`, but no service starts in the same process.
      Default now: `NOT EVALUATED`, exactly as assumption 4 says. — owner: Contributor,
      due: stage 10

### Assumptions taken (depth `easy`)

Taken without a separate question, because they are fixed in the course's design specification:

1. **The three levels are exactly these** — e2e, trajectory, component — following the source
   article.
2. **The fake judge is biased on purpose.** It plays the part of a broken instrument the same way
   a mutation plays the part of broken code. The stage says so in its first line, not in a
   footnote.
3. **Twenty cases, not two hundred.** The stage is a teaching one; two hundred cases would give
   statistics and bury the lesson under the volume of data.
4. **Online sampling is verified locally.** There is no real VM; AC-07 is checked against the
   trace of a stage 6 service brought up in the same process.
5. **The report is one file for a human.** No database, no interface: the stage is about **what
   to measure**, not about where to display it.
6. **The judge has two protocols** — pairwise (for position bias) and pointwise (for length
   bias). One protocol does not cover both: the pairwise one has no score, the pointwise one has
   no order.
