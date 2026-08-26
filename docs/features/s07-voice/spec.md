---
status: Draft
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
---

# Spec — s07-voice

> **Glossary:** [CONTEXT](../../../CONTEXT.md) (roles + domain objects), [GLOSSARY](../../../GLOSSARY.md) (course terms)
> **Reference module / docs / channels used:** `planning/2026-08-22-agentic-ai-course-design.md` §9 (s07) · `CURRICULUM.md` · `PLAYBOOK.md` · stage 6 as the service that takes the request · source article #7 (Voice Agents)

## 1. Context

Stage 6 delivered a service that answers. It answers **slowly** — and nobody minds while the
answer is read with eyes.

Voice changes one thing: now the person on the other end is **waiting in silence**.

> **In text, latency is an inconvenience. In voice, latency is a pause in the conversation, and
> a person reads a pause as "they did not hear me" or "it is broken".**

Hence the stage's main thesis, and it is not about sound:

> **You can only optimise what you have measured. That is why the pipeline is built twice:
> batch, to get the number before, and streaming, to get the number after.**

One pipeline without the other proves nothing. "Streaming is faster" is not a result but a
well-known phrase; the result is two numbers taken from the same data with one command.

**Why not streaming straight away.** The batch pipeline is written in an hour, works, and gives
the baseline. A Learner who saw 1500 ms and then 400 ms understands the **price** of streaming's
complexity. A Learner handed streaming straight away takes it for the norm and has no idea what
it costs.

Settled at interview depth `easy`: the decisions are fixed in the course design specification.
The assumptions taken are at the end of §5.

## 2. Goals

- The Learner gets **two numbers** from the same data: time-to-first-audio for the batch pipeline
  and for the streaming one, and sees the difference in their own run.
- The Learner can explain why the measurement is **time to the first sound** rather than total
  duration.
- The Learner can explain why p95 matters more than the mean, and show it on their own numbers.
- The Learner reproduces barge-in: noise does not interrupt, speech does — and sees exactly which
  threshold decides it.
- The Learner sees the price of a **synchronous** tool call in voice, and what prefetch does
  about it.

## 3. Non-goals

- **We are not doing recognition and synthesis ourselves.** Both are separate products; the stage
  calls them.
- **We are not optimising audio quality.** No noise suppression, no echo cancellation; that is a
  different discipline.
- **We are not building telephony.** No SIP, no WebRTC transport; a browser and a socket are
  enough.
- **We are not competing with cloud voice APIs.** The number obtained here is about **pipeline
  architecture**, not about how fast models are.
- **We are not optimising before measuring.** Every speed-up at this stage is measured first.
- **We are not making voice mandatory.** The whole stage can be worked through with no microphone,
  no models and no network — on fake delays.

## 4. User stories

### US-01: Get the number before

**As a** Learner
**I want** to run the batch pipeline and see the time-to-first-audio
**So that** I have a baseline to compare against

### US-02: Get the number after

**As a** Learner
**I want** to run the streaming pipeline on **the same** data
**So that** the difference is the result of an architecture change and not of a change in conditions

### US-03: Understand what exactly to measure

**As a** Learner
**I want** to see the latency broken down across the pipeline's stages
**So that** I optimise the most expensive step rather than the most noticeable one

### US-04: See why p95 and not the mean

**As a** Learner
**I want** to run it many times and see the distribution
**So that** I stop reporting the mean where the user feels the tail

### US-05: Interrupt the agent with my voice

**As a** Learner
**I want** speech to interrupt the answer and noise not to
**So that** a conversation is a conversation rather than a monologue with a button

### US-06: Not pay for a tool twice

**As a** Learner
**I want** to see what a synchronous tool call costs in voice
**So that** I know when prefetch is justified and when it is premature complexity

### US-07: Actually hear it

**As a** Learner
**I want** to say something into a microphone and hear the answer
**So that** the numbers stop being an abstraction

### US-08: Verify voice deterministically

**As a** Learner
**I want** to run the checks with no microphone, no models and no network
**So that** I can break the code and see exactly what broke

## 5. Acceptance criteria

### AC-01 (US-01) — happy path

**Given** a recorded utterance and the batch pipeline
**When** the Learner starts a run
**Then** they get a **time-to-first-audio in milliseconds** and a breakdown of that number across
the steps: recognition, the model's reply, synthesis.

**The breakdown reconciles completely:** `sum of steps + handover to the consumer = total time`,
and nothing is left unattributed. The short form ("the steps sum to the total") is true only where
the pipeline owns the time on its own; the moment a consumer takes the chunks at its own pace, it
quietly bills that pause to the next step — and the sum still reconciles while the breakdown is
already lying

### AC-01b (US-01) — domain invariant · added after review

**Given** a streaming run and a consumer that spends its own time between chunks
**When** the Learner looks at the breakdown
**Then** the consumer's time is carried as a **separate** term, and the model's step equals exactly
how long the model worked.

The mirrored half is mandatory: without it the conservation law is satisfied even when the model is
blamed for someone else's delay — the sum reconciles, and the most expensive step becomes the one
after which the browser happened to think

### AC-02 (US-02) — happy path

**Given** **the same** utterance and the streaming pipeline
**When** the Learner starts a run
**Then** the time-to-first-audio is **at least twice as small** as the batch one, and both numbers
are printed next to each other in one output

### AC-02b (US-02) — domain invariant

**Given** both pipelines
**When** the Learner compares the duration of the **answer** — from the finished request text to
the last sound — rather than the time to the first sound
**Then** it is **the same**: the model writes just as much, synthesis voices just as much.

**Streaming's gain breaks down into two different parts, and conflating them is expensive:**

    overlap             recognition runs TOGETHER with the speech — the work moved into the
                        time while the person is still talking, and after their pause only a
                        tail is left
    earlier delivery    the first chunk goes to synthesis while the model writes the rest —
                        the same amount of work, but it starts being delivered sooner

The second part **does not reduce** the total time, and that is precisely why what must be measured
is the time to the first sound. Without this criterion the lesson would be selling a speed-up that
is not in it

### AC-03 (US-03) — happy path

**Given** a run of either pipeline
**When** the Learner looks at the breakdown
**Then** every step is named and has its own number, and it is visible **which step is the most
expensive**

### AC-04 (US-04) — domain invariant

**Given** a hundred runs on the same data with a spread of latencies
**When** the Learner looks at the summary
**Then** they see the mean **and** p95, and p95 is noticeably larger than the mean.
The number that gets reported and the number the user feels are not the same.

**The spread has to be real.** The fake clock gives none by construction — and that is its virtue,
not its flaw. So the spread comes from the **model**: latency is a function of the run index, so a
hundred runs give a hundred real measurements, and a repeat run gives the same hundred. A list of
numbers typed by hand satisfies the "Then" and does not satisfy the "Given"

### AC-04b (US-04) — domain invariant · added after review

**Given** samples of different sizes — not only a hundred runs
**When** the Learner takes p95
**Then** the runs worse than it are **no more than 5 %** at every size.

Nearest rank is `ceil(0.95·n)`, and rounding gives a different rank at roughly half of all sample
sizes. At thirty runs p95 landed on the fastest run with 6.7 % of runs worse than it: the module
that exists precisely to expose the tail was hiding it. A criterion at **one** sample size checks
one lucky point

### AC-05 (US-05) — error

**Given** an agent that is speaking, and incoming audio 100 ms long at noise level
**When** the pipeline handles it
**Then** the answer **is not interrupted**

### AC-05b (US-05) — happy path

**Given** the same agent and incoming audio 300 ms long at speech level
**When** the pipeline handles it
**Then** the answer **is interrupted**, and the trace names which threshold fired.
The mirrored half of AC-05: a detector that never interrupts satisfies AC-05 completely and is
broken while doing so

### AC-05c (US-05) — domain invariant

**Given** audio at speech level but shorter than the minimum duration
**When** the pipeline handles it
**Then** the answer **is not interrupted**: the decision is made by **two** conditions — level and
duration — and neither of them alone is enough

### AC-06 (US-06) — happy path

**Given** a request that needs a slow tool
**When** the Learner compares a synchronous call with prefetch
**Then** both numbers are printed, and it is visible **exactly how many** milliseconds prefetch buys

### AC-06b (US-06) — domain invariant

**Given** a request that does **not** need the tool
**When** prefetch is switched on
**Then** the prefetch result is discarded, and this is named in the trace as **wasted work**.
Prefetch is not free: it performs a call that may turn out not to be needed, and the lesson has to
show both sides

### AC-07 (US-07) — happy path

**Given** a machine with a microphone and the models installed
**When** the Learner opens the page and speaks
**Then** they hear the answer, and in the same window see the same numbers as in a run

### AC-07b (US-07) — error

**Given** a machine **without** the models installed
**When** the Learner opens the page
**Then** the page says what is missing and what to install, instead of falling over with a
technical error

### AC-07c (US-07) — happy path · added after review

**Given** a machine **without** a microphone and without models — that is, any machine
**When** the socket is brought up and a whole conversation is run through it
**Then** the connection is established, chunks arrive, the breakdown reconciles, and recognition
costs as much as **the entire** utterance lasts, not one frame.

This criterion appeared because it was missing. Live mode never worked **once**: the socket's
annotation was a string, the type was imported inside the factory, and FastAPI took it for a query
parameter, closing every connection before `accept()`. Two reviewers read the file and saw nothing
— because reading does not run it. Now a check runs it

### AC-10 (US-07) — authorization

**Given** an open page on which the Learner has not yet clicked anything
**When** the page has loaded
**Then** the microphone is **not on**: access is requested only after an explicit action, and
stopping releases the device. The recording indicator shows the actual state, not the intent

### AC-10b (US-07) — authorization

**Given** a session in which the Learner spoke
**When** it has ended
**Then** neither the samples nor the recognised text are stored on disk; the trace holds only
durations and decisions.
The mirrored half: **the durations are there**. A session that leaves nothing behind satisfies
"audio is not stored" completely and makes the stage unmeasurable

### AC-11 (US-03) — cross-context

**Given** a pipeline run with tracing switched on
**When** the Learner compares the printed breakdown against the steps in the trace
**Then** they **match**: the same steps, the same numbers.
Measurement and observability are two different mechanisms, and a divergence between them means at
least one of them is lying. Stage 6 showed that metrics and the trace answer different questions;
here they must answer **the same way** about the same thing

### AC-08 (US-08) — happy path

**Given** a machine with no microphone, no models and no network
**When** the Learner runs the stage's checks
**Then** all of them are green or marked **not evaluated**; none red

### AC-08b (US-08) — domain invariant

**Given** the checks that measure time
**When** they run on a slow or loaded machine
**Then** they do not flicker: the numbers come from **fake** delays rather than from a real clock.
A timing check that fails once in ten runs is worse than no check at all: it gets disabled

### AC-09 (US-01) — error

**Given** recognition that returned empty text
**When** the pipeline continues
**Then** it calls neither the model nor synthesis, and names the empty input as its own state.
Silence is not a request

## Test plan

| AC | Test | Level | What it proves |
|---|---|---|---|
| AC-01 | `the batch pipeline reports first audio and its parts` | unit | The breakdown, and the sum reconciles |
| AC-01b | `the streaming breakdown adds up with a slow consumer` | unit | **FAILURE.** The conservation law with three terms |
| AC-02 | `streaming reaches first audio at least twice as fast` | unit | Two numbers side by side, and the ratio |
| AC-02b | `the answer segment costs the same in both pipelines` | unit | **FAILURE.** Earlier delivery does not reduce the work; the gain is split into two parts |
| AC-03 | `every stage of the pipeline is named and timed` | unit | The most expensive step is visible |
| AC-04 | `p95 is visibly larger than the mean` | unit | **FAILURE.** A distribution, not one number |
| AC-04b | `p95 keeps its promise at every sample size` | unit | **FAILURE.** Nearest rank, not rounding |
| AC-05 | `noise does not interrupt` | unit | **FAILURE.** The level threshold |
| AC-05b | `speech does interrupt, and the trace names why` | unit | The mirrored half |
| AC-05c | `short speech does not interrupt` | unit | **FAILURE.** Two conditions, not one |
| AC-06 | `prefetch buys a measured number of milliseconds` | unit | A number, not a claim |
| AC-06b | `an unused prefetch is named as wasted work` | unit | **FAILURE.** The price is named |
| AC-07 | `the page plays audio and shows the same numbers` | e2e | **NOT EVALUATED** without a microphone |
| AC-07c | `the socket actually runs a conversation` | integration | The socket is **executed**, not read |
| AC-07b | `a missing model is explained, not crashed` | integration | **FAILURE.** A third state |
| AC-10 | `the microphone needs an explicit action` | integration | **FAILURE.** Consent, not intent |
| AC-10b | `no audio or transcript is written down, but durations are` | unit | A mirrored pair |
| AC-11 | `the trace carries the same breakdown as the timing` | unit | **FAILURE.** Two mechanisms, one truth |
| AC-08 | `checks run without microphone, models or network` | unit | The whole suite offline |
| AC-08b | `timing checks use fake delays, not the clock` | unit | **FAILURE.** Against flicker |
| AC-09 | `empty transcription calls neither model nor synthesis` | unit | **FAILURE.** Silence is not a request |

### What this plan deliberately does not prove

- **That streaming is faster under any conditions.** The numbers are taken on **fake** delays
  chosen to the order of magnitude of real ones. This is evidence about **pipeline architecture**,
  not about how fast particular models are, and the lesson says so in its first line.
- **That the VAD threshold is right.** 100 ms of noise and 300 ms of speech are the bounds of an
  **exercise**, not production settings: the real threshold depends on the microphone, the room and
  the language.
- **That prefetch is worth switching on.** It is shown with **both** numbers: how much it buys and
  how much wasted work it creates. The decision stays with the Learner.
- **That live mode works on any machine.** It is verified only where there is a microphone and
  models; everywhere else — `NOT EVALUATED`.

### Assumptions taken

Settled at depth `easy`. Each of them can be rejected with one line in §8.

1. **Delays are faked by default.** Real models are behind a flag. Otherwise the checks need
   gigabytes of weights and flicker with the machine's load.
2. **One voice, one language.** Multilingual support and voice selection are configuration, not a
   lesson.
3. **Barge-in is decided by two numbers** — level and duration. Spectral VAD is a different
   discipline and a separate dependency.
4. **A page with no build step.** One HTML file, no frontend stack: the stage is about latency, not
   about build tooling.
5. **Prefetch has one tool**, not a scheduler. One is enough to show the price.

## 6. Non-functional requirements

| # | Requirement | Target | How we measure |
|---|---|---|---|
| NFR-1 | Size of `pipeline.py` | ≤ 110 executable lines | counted in the check |
| NFR-2 | Check run | ≤ 30 s (**estimate**, not measured), offline | `BUDGET_SECONDS`, the ceiling held by `check_all` |
| NFR-3 | Lesson length | ≤ 2500 words | the number-reconciliation check |
| NFR-4 | Share of failure modes | ≥ 1/3 of the stage's checks | a counter in the check |
| NFR-5 | Run without the voice models | green or `NOT EVALUATED`; none red | `scripts/clean_install.py` |
| NFR-6 | Flicker in the timing checks | 0 out of 20 consecutive runs | a repeat run inside the check |

**NFR-6 is not a formality.** A check that measures time and fails once in ten runs will be the
first one disabled, and with it disappears the only evidence for the stage's main thesis. That is
why the numbers come from fake delays rather than from a clock, and why that is checked separately.

## 6.1 Security and privacy

- **Audio is not stored.** Neither the raw samples nor the recognised text reach a file; the trace
  holds only durations and decisions. Recording a voice needs its own consent, which the course
  does not ask for.
- **The page sends audio nowhere except its own service.** No external addresses.
- **The microphone switches on only on an explicit user action** and switches off on one too.
- **The recognised text stays untrusted** — everything stages 2 and 5 know about that is in force.
- **The abuses this stage reproduces:** empty recognition, endless speech with no pauses, audio
  longer than the limit, a missing model. Each has its own check.

## 7. KPIs

| # | Metric | Target |
|---|---|---|
| KPI-1 | The Learner gets both numbers with one command | ≤ 1 min on a clean machine |
| KPI-2 | The batch / streaming ratio in the Learner's run | ≥ 2 |
| KPI-3 | The Learner can say why p95 > mean, using their own numbers | via the checklist |
| KPI-4 | The timing checks do not flicker | 20 consecutive runs green |

## 8. Open questions

- [ ] Will live mode be verified on a machine with a microphone? There is no access right now, so
      AC-07 stays `NOT EVALUATED`, and the page and the socket are verified without audio. Default
      now: fake input, live mode behind a flag. — owner: Learner, due: before the `stage-07` tag
- [ ] Should the voice pipeline be threaded into stage 6's service? Right now it is a separate
      module with its own demo. Default now: keep it separate; stitching makes sense at stage 10,
      when it is known what evaluation demands. — owner: Contributor, due: stage 10
- [ ] Is a spectral VAD needed instead of a level threshold? Default now: the threshold, with its
      limit named. — owner: Contributor, due: after the first run with a real microphone
