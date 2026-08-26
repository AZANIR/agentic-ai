---
status: Draft
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-23"
feature_size: "S"
---

# Spec — s01-agent-loop

> **Glossary:** [CONTEXT](../../../CONTEXT.md) (roles + domain objects), [GLOSSARY](../../../GLOSSARY.md) (course terms)
> **Reference module / docs / channels used:** `planning/2026-08-22-agentic-ai-course-design.md` §5, §9 (s01), §11 · `docs/architecture-map.md` · `docs/adr/0002`, `0003`, `0005`, `0006`

## 1. Context

Someone who can write Python functions has heard the word "agent" hundreds of times and has
never once seen what it is made of. The explanations on offer collapse into two useless poles:
"it's ChatGPT that can browse" or "it's an autonomous reasoning loop with tool use and
persistent memory". The first explains nothing, the second explains nothing at greater length.
The reader is left with the feeling that there is magic inside.

This is the first stage of the course and it carries disproportionate weight: if the reader does
not see here that an agent is **an ordinary loop around ordinary functions**, they will take the
remaining nine stages as incantation. On top of that, the three guards this stage introduces
(the step limit, argument validation, confirmation of an irreversible action) are used by every
stage that follows — they have to be laid down here, or they will never appear at all.

The chosen approach: **build the loop from scratch, with no framework**, on a fake model client
that replays a pre-recorded script. The fake is not a simplification here but a precondition: it
is what makes checks on failure modes possible, and against a real model those checks cannot be
written, because a real model is not deterministic. The reader sees every line of the loop and
can break it.

Decided at interview depth `easy` — the product and architecture decisions are already fixed in
the course design specification and in six ADRs; a repeat interview would re-decide them with no
new information. The assumptions taken are collected in §8.

## 2. Goals

- The Learner runs a working agent themselves and can explain **in words** why the model does
  not execute functions on its own.
- The Learner holds the three guards not as theory but as code they have seen and broken: the
  step limit, argument validation, confirmation of an irreversible action.
- The next nine stages inherit a ready vocabulary and a ready run harness — none of them
  explains the loop again.

## 3. Non-goals

- **We do not teach frameworks.** LangGraph arrives at stage 3 — here it would hide exactly what
  has to be shown.
- **We do not make the agent useful.** The tools return fixtures; wiring up real services is
  stage 4 and later. Usefulness here would distract from the mechanics.
- **We do not touch memory between sessions.** This stage's agent forgets everything — and that
  is a deliberately visible flaw, the one stage 5 resolves.
- **We do not optimise.** Neither tokens nor latency. Measurement starts at stage 7, and doing it
  earlier would mean measuring something the reader does not yet understand.

## 4. User stories

### US-01: See an agent in action

**As a** Learner
**I want** to run the stage demo immediately after installing, with no sign-ups and no keys
**So that** I see the full cycle "task → tool choice → result → answer" with my own eyes

### US-02: Be sure the agent will not spin forever

**As a** Learner
**I want** to see what happens to an agent that cannot finish its task
**So that** I understand why the step limit is a guard, not a performance setting

### US-03: See what becomes of malformed arguments

**As a** Learner
**I want** to see what happens when the model asks for a tool with the wrong arguments
**So that** I understand why a check has to stand between the model's decision and the function call

### US-04: Stop the agent from doing something irreversible

**As a** Learner
**I want** to see that the agent does not perform an irreversible action on its own
**So that** I understand where the line of trust in an autonomous system runs

### US-05: Switch on a real model

**As a** Learner
**I want** to plug in a real provider without changing a single line of the stage's code
**So that** I can compare the behaviour of the fake and of a real model on the same loop

### US-06: Check my own change

**As a** Contributor
**I want** to check a change to the loop offline in seconds
**So that** I can edit the lesson and the code with no token spend and no dependence on the network

## 5. Acceptance criteria

### AC-01 (US-01) — happy path

**Given** the Learner has installed the package and has configured no model provider
**When** they run the stage's demo
**Then** the run finishes successfully with no network access and shows **four scenarios in a
row**: choosing between tools, a rejection over malformed arguments, a stop at the step limit,
the confirmation gate on an irreversible action. Its first line states that the answers come from
a fake. For every step the console prints the chosen tool with its arguments and the tool's
result, and at the end the final answer. The same steps are written into the trace — the console
for the Learner, the trace for stage 8; no step lands in only one of the two

### AC-02 (US-02) — domain invariant

**Given** a model that behaves so that at every step it asks for a tool again and never gives a
final answer
**When** the Learner runs the agent
**Then** the run stops exactly at the configured step limit, states that it stopped because of
the limit, and **does not return an invented final answer**.
A step = one iteration of the loop: one call to the model plus running every tool it asked for in
that response — asking for three tools at once is still one step

### AC-03 (US-03) — error

**Given** the model asks for a tool with arguments that do not match that tool's declared
schema — a missing required field, an extra field, or a wrong type
**When** the run reaches that step
**Then** the tool **is not executed**, the run records a rejection explaining exactly what does
not match, returns that explanation to the model as the step result, and continues — the run does
not die with a technical error.
No type coercion is performed: text where a number was declared is a rejection, not an invitation
to guess. Silent coercion hides the model's mistake in exactly the place you need to see it

### AC-03b (US-03) — error

**Given** a step that argument validation has just rejected
**When** the run carries on
**Then** the explanation of the rejection goes back **to the model as the step result** rather
than killing the run or staying only in a log. The model gets a chance to correct itself —
otherwise validation turns into a silent truncation in which the user only sees a shorter answer.

**Why this is a criterion of its own.** AC-03 states that the action did not happen. That is half
of it: a run that silently stopped satisfies it too. The other half — that the rejection
**reached the model** — does not follow from it and needs a check of its own.
### AC-04 (US-04) — authorization

**Given** a tool marked irreversible, and the Learner has given no confirmation
**When** the agent decides to call that tool
**Then** the action **is not performed**; the run shows exactly what would have happened and
states how to confirm it. Confirmation happens as **a separate repeat run**, not as an
interactive console prompt — interactive input is not reproducible in a check and reads
end-of-stream in CI. Only in a confirmed run is the tool executed

### AC-04b (US-04) — happy path

**Given** the same irreversible tool and a run **with** confirmation
**When** the agent reaches that step
**Then** the tool **is executed**, and its result lands in the run.

**Why this is a criterion of its own.** A gate that lets nothing through satisfies AC-04 in full
and is broken all the same. The mirror half — that what is permitted does get through — does not
follow from the first and does not appear on its own. The same lesson repeated at stages 2, 3
and 5.
### AC-05 (US-05) — cross-context

**Given** the Learner has filled in a real provider's details in the environment file — state
owned by the shared configuration layer, not by the stage
**When** they run the same demo command
**Then** the run goes to that provider and its first line names the provider and the model. The
loop, the tool set and the output format stay unchanged; the text of the answer is different, of
course — that difference is the whole point of switching on a real provider. No stage code was
edited

### AC-06 (US-06) — happy path

**Given** the Contributor has changed the loop's code and has configured no provider
**When** they run the stage checks
**Then** the run finishes with no network access, lists every check performed together with what
it is for, and among them are **at least three on failure modes** — the step limit, malformed
arguments and an irreversible action

### AC-06b (US-06) — error

**Given** the Contributor has broken the loop's code
**When** they run the stage checks
**Then** the run finishes marked as failed, names which check failed, and shows the place in the
code — a silent success is impossible

## 6. Non-functional requirements

| Aspect | Target | Measurement |
|---|---|---|
| Stage check duration | ≤ 2 s | the check summary output |
| Demo run duration with no provider | ≤ 1 s | manual measurement, recorded in the lesson |
| Network calls under profile `local` | exactly 0 | the check passes offline with no provider |
| Lesson reading time | ≤ 25 min | ≤ 2500 words at 100 words/min |
| Size of the loop module | ≤ 120 lines | executable code, excluding docstrings, comments and blank lines |
| Size of the validation module | ≤ 60 lines | the same measure; validation is a separate module beside the loop |
| Steps to the first green run | ≤ 5 commands | the sequence in SETUP |

## 6.1 Security / privacy

- **Data classification:** public. Teaching material and fixtures; no real data at all.
- **Personal data touched:** none. The fixtures contain invented NovaShop order identifiers with
  no names, addresses or contact details.
- **AuthZ/AuthN impact:** the stage introduces **the line of trust in an autonomous system** —
  the confirmation gate for an irreversible tool (AC-04) and argument validation before execution
  (AC-03). Both mechanisms carry over into every following stage; weakening them later would mean
  weakening every stage at once.
- **Abuse cases:**
  - **The agent performs an irreversible action after misreading the task:** the action is not
    performed without an explicit human confirmation (AC-04).
  - **The model passes a tool arguments it does not expect:** the tool never gets control; the
    mismatch is explained and returned to the model (AC-03).
  - **A run never finishes and burns tokens:** it stops at the step limit (AC-02).
  - **The reader spends money by accident while believing they are offline:** the first line
    names the source of the answers (AC-01, AC-05).
  - **A provider key ends up in the repository:** keys live only in the environment file, which
    is excluded from version control; there are no keys in the code, the fixtures or the lesson.
- **Security review:** N/A — public teaching material with no personal data and no network
  surface. The review becomes mandatory at stage 6, where a public endpoint appears.

## 7. Metrics / KPIs

- **Checks on failure modes in the stage** — baseline: 0, target: ≥ 3 by the time the stage closes.
- **Time from cloning the repository to a green stage check** — baseline: unknown, measured on a
  clean machine following SETUP; target: ≤ 10 min.
- **Glossary coverage of the lesson's terms** — baseline: unknown (the lesson is not written),
  target: 100% — every term first used in the lesson has a definition in the glossary.
  Measured by reconciling the lesson's highlighted terms against the glossary list before the
  stage closes.
  (A counter of "we now have N terms" would be a target the author meets simply by writing the
  glossary.)
- **Share of run steps that reached the trace** — baseline: 0, target: 100% — every model call and
  every tool call leaves a record (the condition for stage 8 to work).

## 8. Open questions

- [ ] What to do when the configured model does not support tool calling (some local models do
  not)? Default now: detect the missing support and say so clearly, naming the models the stage
  was verified against — instead of producing an incomprehensible failure inside the loop.
  — owner: Contributor, due: before `sdd:implement`
- [ ] Which language to write the agent's system prompt and the tool descriptions in — English or
  Ukrainian? Default now: English. That is how they are written in the source articles and in the
  wild, and weak models make noticeably fewer mistakes on English tool descriptions; the
  explanation of that choice goes into the lesson. — owner: Contributor, due: before
  `sdd:implement`

### Deferred after the review (2026-08-23)

- [ ] The `SDD-AC` trailers in the commits point at the wrong commits: the gate is claimed by a
  commit that touches only the checks. Default now: leave as is — the history is published, and
  rewriting it for the sake of trailers costs more than it is worth. — owner: Contributor,
  due: before stage 2
- [ ] In the stage's code "ADR-0002/0003" read as repository ADRs, although they mean the stage's
  own. Default now: write "stage ADR NNNN" in stage code. — owner: Contributor, due: before stage 2
- [ ] SAD §6 does not contain `tool_unknown`, `tool_error`, `run_limit`; there is no flow for
  US-05 and US-06. Default now: update at the brownfield re-survey of the map after stage 2, when
  it becomes clear which conventions genuinely repeat. — owner: Contributor, due: after stage 2
- [ ] The ≤2 s check budget rests on a cold `import openai` (~1 s out of 1.4 s). A decision is
  needed on whether to measure the threshold without the cold SDK import. Default now: leave the
  threshold as is and revisit it if it starts failing in CI. — owner: Contributor, due: before
  stage 6

### Closed in clarify (2026-08-23)

| # | What was open | Decision |
|---|---|---|
| 1 | The mechanism for confirming an irreversible action | A separate repeat run, not an interactive prompt — AC-04 |
| 2 | How many tools to give the stage | Three: `get_weather` (the article's canon), `get_order_status` (the bridge to NovaShop), `initiate_return` (irreversible). Four demo scenarios — AC-01 |
| 3 | Where argument validation lives | In the stage's code, as a separate module beside the loop. Lifting it into the shared layer becomes an exercise at stage 3 — §6 |

### Assumptions taken (depth `easy`)

Not re-asked; taken from the course design specification and recorded here for an explicit veto:

1. Feature size **S**, route **quick** — per the size matrix: 2–5 commits, ~a week, no new module
   and no migrations.
2. The through-line domain is NovaShop; the article's canonical example (weather) stays as an
   anchor of trust.
3. The loop is built on a fake client; a real provider is optional and changes no code.
4. Checks are bare `assert` with no test framework (ADR-0006).
5. Tracing is present from this stage rather than added at stage 8 (ADR-0005).

### Sharpened in clarify without asking (low stakes, a veto is welcome)

| § | What was ambiguous | What it became |
|---|---|---|
| AC-01 | it did not say what the demo runs and where it prints | four scenarios; every step goes both to the console and to the trace |
| AC-02 | what "a step" means when one response holds several tools | a step = one iteration of the loop, however many tools it contains |
| AC-03 | whether argument types are coerced | no: text instead of a number is a rejection |
| AC-05 | "the rest of the behaviour is unchanged" is literally unverifiable | the loop, the tools and the format are unchanged; the text of the answer differs |
| §6 | "core size" with no way to measure it | executable code excluding docstrings; the loop and validation are measured separately |

---

## Test plan

Size S + route `quick` → the plan lives here, there is no separate file.

**The levels that are possible here at all.** The stage owns no external dependency: no database,
no queue, no network. So `integration` and `contract` are empty **by construction** rather than by
oversight — writing them would be an imitation of coverage. That leaves `unit` and `e2e`.

### Criteria coverage

| AC | Test | Level | What exactly it proves |
|---|---|---|---|
| AC-01 | `demo runs four scenarios offline` | e2e | The demo works through four scenarios in a row, the banner names the fake, there are no network calls, the trace is written |
| AC-02 | `step limit stops a runaway loop` | unit | **FAILURE.** A fake that always asks for a tool stops exactly at the limit; no final answer is invented |
| AC-03 | `invalid arguments never reach the tool` | unit | **FAILURE.** A missing field, an extra field, a wrong type — the tool gets control in none of the three cases |
| AC-03b | `rejection is returned to the model as a step result` | unit | **FAILURE.** A validation rejection is not an exception: the explanation goes to the model, the loop continues |
| AC-04 | `irreversible tool needs an explicit confirmation` | unit | **FAILURE.** Without confirmation the irreversible tool is not executed; the run describes the consequence |
| AC-04b | `confirmed run executes the irreversible tool` | unit | The other side of the gate: with confirmation the tool does execute — the gate is not sealed shut |
| AC-05 | `configured provider yields a real client and a naming banner` | unit | With a faked environment the factory returns a real client with the given base URL, and the banner names the provider. **We do not touch the network** — see below |
| AC-06 | `stage checks run offline and cover three failure modes` | e2e | The check run is offline, the listing carries purposes, ≥3 are marked as failures |
| AC-06b | `a broken check makes the check run fail loudly` | e2e | A deliberately failing check gives a non-zero exit code, the check's name, an `AssertionError` and the place in the code |

Every failure and authorization criterion has **a row of its own**, not folded into a happy path.

### What this plan deliberately does not prove

**AC-05 is only half covered, and that is on purpose.** The check proves that the factory
**chooses** a real client and names it correctly. It does not prove that a call to the provider
actually happens — that would need the network and a key, and both would destroy the checks' main
property: offline and deterministic.

The second half is closed by **a manual checklist in the lesson**: configure Groq, run the same
demo, confirm that the banner changed and the loop did not. The lesson has to state that boundary
outright. A check that pretends to cover more than it covers is worse than one that is honestly
incomplete.

### Why not mutating production code

The first implementation of AC-06b mutated `loop.py` (switching off the gate), ran the checks in a
subprocess and restored the file. The proof is convincing, but the price is high: **2.25 s**
against the 2 s threshold in §6, a write into the source during an ordinary run, and the risk of
leaving the file broken if the process is killed between the write and the restore.

Replaced by a check of **the harness itself**: it is fed a deliberately failing function, and we
assert that the exit code is 1, that the check is named, that an `AssertionError` is shown and the
place in the code with it. The same statement, 0 s, no write into the source.

The mutation proof of the gate itself was performed **by hand** during T4 and recorded in the
commit message: with the `irreversible` branch switched off exactly one check goes red — the one
asserting the tool is unreachable — while the checks for the confirmed path and for reversible
tools stay green. That is a one-off guarantee in the history, not a daily tax on every run.

### Integration strategy

<!-- N/A: the stage owns no external dependency. There is nothing to spin an ephemeral container
     up for — the first real dependency is Postgres at stage 6. -->

**Test data.** The NovaShop fixtures (orders with invented identifiers) live in `data/`. The fake
model's scripts are right in the text of the check: the script *is* the specification of the
model's expected behaviour, so hiding it in a fixture would mean hiding the substance.

**Cleanup.** Every check that writes a trace writes into a temporary directory and leaves the
working trace file untouched. There is no shared state between checks — execution order does not
affect the result.

### Load

<!-- N/A: no NFR sets a throughput or a p95. The numeric NFRs in §6 are durations of a single run,
     and they are covered by the measurements below, not by a load test. -->

### The durations from §6 — measured, but not asserted

The harness prints the duration of every module; the thresholds (`≤ 2 s` for the checks, `≤ 1 s`
for the demo) are recorded in §6 and reconciled by eye.

We deliberately put no `assert` on wall-clock: it would fail on a slow runner, on a laptop in
power-saving mode and during the first run with a cold import — that is, it would go red where
nothing is broken. A test that lies sometimes is worse than one that is absent: after the third
false failure people start ignoring it, and then it catches nothing at all.

### Placement in CI

Every check runs on every PR: together they take seconds and need neither secrets nor the network.
There is no separate slow suite at this stage.
