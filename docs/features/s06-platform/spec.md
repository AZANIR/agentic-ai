---
status: Draft
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
---

# Spec — s06-platform

> **Glossary:** [CONTEXT](../../../CONTEXT.md) (roles + domain objects), [GLOSSARY](../../../GLOSSARY.md) (course terms)
> **Reference module / docs / channels used:** `planning/2026-08-22-agentic-ai-course-design.md` §9 (s06) · `CURRICULUM.md` · `PLAYBOOK.md` · stages 1–5 as the parts · `deploy/docker-compose.yml` as the existing base · source article #6 (From Prototype to Production)

## 1. Context

After five stages the repository holds an agent loop, search, routing, tools across a process
boundary and memory. Each of them works. **There is no system.**

Stage 6 stitches them into one service and shows that going to production is not "the same thing,
only on a server". It is a different set of tasks, and almost none of them are about the quality
of the answers:

> **A prototype answers the question "does this work?". Production answers the question "what
> happens when it breaks at three in the morning, and who finds out".**

Three things that were not in the prototype and could not have been:

    boundaries   who is allowed to ask, how many times, and at whose expense
    visibility   what the service is doing now and what it was doing when nobody was watching
    life         it survives a restart, an upgrade, and a second process alongside

The last one is the most treacherous. A prototype lives in one process, and any state in process
memory works flawlessly. A second worker turns that state into a source of untruth, and does it
**silently**: counters drift apart, the background job runs twice, the cache serves something
stale. There is no error anywhere.

That is why the central trap of this stage is reproduced **deliberately and live**: `--workers 2`,
a scheduler in process memory, and a job that runs twice in a single interval. The Learner sees it
as a number in their own log instead of reading a paragraph about it.

The chosen approach: **one service that imports stages 1–5 without changing them**. If the
stitching requires editing stage 3, then the boundary between stages was in the wrong place.

Settled at interview depth `easy`: the decisions are fixed in the course design specification.
The assumptions taken are at the end of §5, after the test plan.

## 2. Goals

- The Learner can bring up **one** service that answers a request using all five previous stages,
  and can see in the trace exactly which nodes fired.
- The Learner understands that authentication, the rate limit and the budget guard are **three
  different** mechanisms with three different failures, not "security".
- The Learner sees why metrics do not answer the question "why did the agent decide that", and
  what does answer it — the trace.
- The Learner reproduces the two-worker trap, sees it live, and fixes it.
- The Learner deploys the service behind HTTPS and verifies it with one script that works the same
  way against a local build and against a real URL.

## 3. Non-goals

- **We are not writing a new agent.** The stage stitches what exists; any edit to stages 1–5 is a
  signal that the boundary was in the wrong place, and grounds for an ADR rather than a quiet patch.
- **We are not building a full supervisor.** An intent classifier is sufficient, and the trade-off
  between the two is named honestly rather than declared away.
- **We are not doing multi-tenancy.** One key — one owner of memory; roles, per-team quotas and
  administration are out of scope.
- **We are not optimising latency.** Measurement arrives at stage 7, evaluation at stage 8.
  Optimising before measuring is guessing.
- **We are not inventing our own monitoring.** The metrics format is standard, the dashboard is
  stage 10.
- **We are not automating VM provisioning.** A terminal and two files; Terraform is a different
  book.

## 4. User stories

### US-01: Get an answer from the service, not from a demo

**As a** Learner
**I want** to send a request to one service and receive the agent's answer
**So that** I can see that the five stages really do add up to one thing

### US-02: See the path a request took

**As a** Learner
**I want** to get a trace with the nodes that fired on this request
**So that** I can answer the question "why did the agent decide that", not only "how long did it take"

### US-03: Keep out whoever has no right to be there

**As an** Operator
**I want** a request without a valid key never to reach the agent
**So that** I do not pay for somebody else's requests and do not hand over somebody else's memory

### US-04: Survive abuse without falling over

**As an** Operator
**I want** requests that come in too often to be refused before the model is called
**So that** one client cannot exhaust the resource for everybody

### US-05: Not go bankrupt overnight

**As an** Operator
**I want** the service to stop calling the model when spending reaches the limit
**So that** a loop that ran away costs ten dollars and not ten thousand

### US-06: See that the service is alive

**As an** Operator
**I want** a health endpoint and a metrics endpoint
**So that** an external monitor sees a failure before a user does

### US-07: Step into the two-worker trap on purpose

**As a** Learner
**I want** to watch a background job run twice under two workers
**So that** I recognise this class of defect in my own code before it shows up in production

### US-08: Deploy behind HTTPS

**As an** Operator
**I want** to bring the service up on a machine with a certificate and a domain
**So that** I have a real URL that can be reached from outside

### US-09: Verify what was deployed in one move

**As an** Operator
**I want** one script that checks a live service
**So that** "seems to work" is replaced by a list of checks with a verdict

### US-10: Survive a restart

**As an** Operator
**I want** memory and traces to survive a container restart
**So that** upgrading the service does not erase what it knows

## 5. Acceptance criteria

### AC-01 (US-01) — happy path

**Given** a running service and a valid key
**When** the Learner sends three different requests: about an order's status, about the returns
policy, and an arithmetic one
**Then** each receives an answer, and **the three answers arrive by different branches** — visible
in the trace, not inferred from the wording of the answers

### AC-02 (US-02) — happy path

**Given** a processed request
**When** the Learner looks at that request's trace
**Then** the trace contains, in execution order, **the steps the service itself writes** — accepting
the request, the guards' decisions, the choice of branch, the call into memory, the answer — and each
one carries a **reason**, not just a duration. One request's trace is found by its identifier

**The boundary is named explicitly.** Stages 2 and 5 write **no** step into the trace at all:
`store.search()` takes no tracer, and `Memory.context_for()` returns its reasons in
`Context.skipped` rather than in the trace. That is why AC-02 requires the service's own steps
rather than "all the stages involved": a requirement on somebody else's code, which §3 forbids
editing, is a hidden task rather than a criterion. Whether to thread the tracer down into stages 2
and 5 is a decision for `design`, with its own ADR (see §8)

### AC-03 (US-03) — authorization

**Given** a request with no key, or with an invalid one
**When** the service handles it
**Then** the request is **refused before any call to the model**, and the trace holds no step for
that request other than the refusal itself. The response does not reveal whether such a key exists

### AC-03b (US-03) — authorization

**Given** a request with a valid key
**When** the service handles it
**Then** the request **reaches** the agent, and the memory it sees belongs to the owner of that key
and to nobody else.
The mirrored half of AC-03: a guard that lets nobody through satisfies AC-03 completely and is
broken while doing so

### AC-03c (US-03) — authorization

**Given** two keys belonging to different owners, and similar facts in each one's memory
**When** both ask **the same** question
**Then** each receives **their own** fact, and neither sees the other's.
The mirrored pair to AC-03b, and it is needed precisely because AC-03b proves only its own side: a
service that passes the wrong owner into memory and comes back empty satisfies it completely.
Nothing leaked; the answer disappeared — the same class as at stage 5

### AC-04 (US-04) — error

**Given** a client that has exceeded the permitted rate
**When** it sends the next request
**Then** the request is refused **before the model is called**, the response names when it may be
retried, and this refusal differs from an authentication refusal — not only in its text, but in the
metrics as well

### AC-04b (US-04) — authorization

**Given** two different clients, one of which has exhausted its limit
**When** both send a request
**Then** the second one **receives an answer**: the limit is counted per client, not per service. A
shared counter satisfies AC-04 and makes one client able to stop everybody

### AC-05 (US-05) — domain invariant

**Given** spending that has reached the configured limit
**When** the next request arrives
**Then** the call to the model **does not happen**, the response names the cause as an exhausted
budget, and that cause differs from the rate limit. The limit comes from configuration, not from a
constant in the code

### AC-05b (US-05) — domain invariant

**Given** a service whose budget is not exhausted
**When** a request goes through
**Then** the spending record **grows** by the cost of that request, and the amount is visible in the
metrics. A guard that never counts will never fire

### AC-06 (US-06) — happy path

**Given** a running service
**When** an external monitor calls the health endpoint
**Then** the response arrives **without authentication**, names the state of every external
dependency separately, and a service with a broken dependency says so rather than reporting "alive"

### AC-06c (US-06) — happy path

**Given** a service whose dependencies are all healthy
**When** the monitor calls the health endpoint
**Then** the response says the service is **alive**, and every dependency is named as healthy.
Without this criterion an endpoint hard-wired to "broken" satisfies AC-06 and AC-11 together — a
guard that lets nobody through and a monitor that always screams are the same defect

### AC-06b (US-06) — cross-context

**Given** processed requests, some successful and some refused
**When** the monitor reads the metrics endpoint
**Then** the metrics tell the **kinds of failure** apart — authentication, rate limit, budget, agent
error — and the number of successful ones matches the number of traces over the same period.

**The reconciliation is asserted for one worker.** The metrics collector keeps its counters in
process memory — the third face of the same cause as the limits and the scheduler. With N workers
the endpoint serves one worker's slice, and the reconciliation stops adding up non-deterministically.
The lesson says this outright instead of leaving it to the Learner as a surprise

### AC-07 (US-07) — error

**Given** a service started with two workers and a scheduler inside the application
**When** the background job's time comes
**Then** the job runs **twice**, and this is visible as a number in the logs. After the scheduler is
moved into its own process, the same job under the same two workers runs **once**

### AC-07b (US-07) — error

**Given** those same two workers with counters in process memory
**When** a client sends exactly as many requests as the limit allows, and one more
**Then** the extra request **goes through**: each worker has its own counter, and the limit has
quietly doubled.

**The second half of the same trap, and it matters more than the first.** A doubled job is visible
in the logs; a doubled limit is visible nowhere — the service behaves normally, the boundary merely
means twice as much. After the switch to a shared store, the same run refuses the extra request

### AC-08 (US-08) — happy path

**Given** a machine with a domain and open ports
**When** the Operator follows the sequence described in the instructions
**Then** the service is reachable over HTTPS, and a call over an unencrypted connection is
redirected to the secure one.

**The criterion is split deliberately.** The mechanics — the redirect, the presence of a
certificate, working under a domain name — are checked locally against a self-signed one.
**The validity of a certificate from a public authority cannot be checked without a machine**, so
that half is marked `NOT EVALUATED` rather than passed. Stage 4 did the same with the checks that
need MCP: what was not run has a third state, and it does not equal green

### AC-09 (US-09) — cross-context

**Given** an address for the service — a local build or a real domain
**When** the Operator runs the smoke script against that address
**Then** the script runs **the same** list of checks in both cases and exits with a non-zero code if
even one of them failed. The local run needs neither a domain nor a certificate

### AC-09b (US-09) — happy path

**Given** a healthy local build
**When** the Operator runs the smoke script
**Then** the script exits with a **zero** code and prints the list of what passed.
The mirrored half of AC-09: a script that always returns a non-zero code satisfies AC-09 to the
letter and checks nothing

### AC-10 (US-10) — domain invariant

**Given** a service that has stored a fact and written a trace
**When** the container restarts
**Then** the fact is still available and the trace is still readable. The data lives outside the
container's lifecycle

### AC-12 (US-03) — authorization

**Given** a processed request with a valid key
**When** the Learner reads the log, the trace and the answer itself
**Then** the key's value **appears in none of the three**. The trace holds a derived owner
identifier, from which the key cannot be reconstructed

### AC-13 (US-06) — authorization

**Given** a request to the metrics endpoint with no key
**When** the service handles it
**Then** the metrics are **not served**: the number of requests per client is business information.
The health endpoint stays open while this is true, and names neither versions, nor addresses, nor
connection strings

### AC-14 (US-09) — happy path

**Given** a machine with no key, no network and no running containers
**When** the Learner runs the stage's checks
**Then** all of them are green or marked **not evaluated**; none red. A check that needs a container
says so in words instead of failing

### AC-11 (US-01) — error

**Given** an unavailable external dependency that handling a request depends on
**When** a request arrives
**Then** the service answers with a named error rather than hanging or falling over entirely; at the
same time the health endpoint reports the broken dependency

## Test plan

| AC | Test | Level | What it proves |
|---|---|---|---|
| AC-01 | `three requests take three different branches` | integration | Three branches visible in the trace, not in the wording |
| AC-02 | `the trace names every node and its reason` | integration | Steps, order, reasons; lookup by identifier |
| AC-03 | `a request without a key never reaches the agent` | integration | **FAILURE.** No step other than the refusal |
| AC-03b | `a valid key reaches the agent and sees its own memory` | integration | Mirrored: the guard is not deaf |
| AC-03c | `two owners asking the same question get their own fact` | integration | **FAILURE.** Mirrored pair: somebody else's did not arrive **and** one's own did |
| AC-04 | `an over-quota request is refused before the model` | integration | **FAILURE.** The refusal is named separately from authentication |
| AC-04b | `one client's limit does not stop another` | integration | **FAILURE.** A counter per client, not per service |
| AC-05 | `an exhausted budget stops the model call` | integration | **FAILURE.** The cause differs from the rate limit |
| AC-05b | `spending is counted and visible` | integration | A guard that counts |
| AC-06 | `health names each dependency separately` | integration | **FAILURE.** A broken dependency is not "alive" |
| AC-06c | `a healthy service reports healthy` | integration | A positive verdict: a monitor that always screams is the same defect as a guard that lets nobody through |
| AC-06b | `metrics tell the failure kinds apart` | integration | Kinds of failure + reconciliation with the traces |
| AC-07 | `two workers run the job twice, one scheduler runs it once` | e2e | **FAILURE.** The trap live, and its fix |
| AC-07b | `two workers double the rate limit until the store is shared` | e2e | **FAILURE.** The second half of the trap: a doubling the logs do not show |
| AC-08 | `https serves the service and http redirects` | e2e | Checked by the script; locally — self-signed |
| AC-09 | `the smoke script runs the same list against both targets` | e2e | One list, two targets, a non-zero code |
| AC-09b | `the smoke script exits zero against a healthy build` | e2e | The mirrored half of AC-09: a script that always fails proves zero |
| AC-10 | `data survives a container restart` | e2e | **FAILURE.** State outside the container |
| AC-11 | `an unavailable dependency degrades, not crashes` | integration | **FAILURE.** A named error + health |
| AC-12 | `the key appears in no log, trace or response` | integration | **FAILURE.** A derived identifier instead of the key |
| AC-13 | `metrics need a key, health does not` | integration | **FAILURE.** Aggregates disclose too |
| AC-14 | `the suite is green or not-verified, never red, without Docker` | unit | **FAILURE.** A third state instead of a crash |

### What this plan deliberately does not prove

- **That the service will hold up under load.** There is not a single throughput number here and
  there will not be: the load test arrives at stage 10, after the measurement at 7 and 8.
- **That HTTPS is configured correctly on a real domain.** What is checked locally is the mechanics
  — the redirect and the presence of a certificate; the correctness of the chain of trust is proved
  only by a real run, and that is named in §8 as a dependency on an external resource.
- **That the budget accounting is accurate.** It counts an **estimate** of cost from tokens, not the
  provider's invoice. A guard has to fire before the catastrophe, not balance the books.
- **That an intent classifier is better than a supervisor.** It is cheaper and sufficient at this
  volume; the limit is named in the lesson with a number rather than an opinion.

### Assumptions taken

Settled at depth `easy` without a separate question. Each of them can be rejected with one line
in §8.

1. **The service is synchronous.** Request → answer on one connection. A queue and long-running
   jobs would double the complexity of the stage for zero new lessons.
2. **Key = owner of the memory.** The simplest model that still gives a mirrored isolation check.
3. **The limit and the budget live in a shared store under the `prod` profile** and **deliberately
   in process memory under `local`**. The local half is not a concession but an exercise: that is
   exactly where the Learner starts two workers and sees that it is not only the scheduler that
   doubled, but the limit as well.
4. **One domain, one service.** No load balancer, no multiple environments.
5. **Secrets live in an environment file on the server.** A secret store is the right answer and
   out of scope.

## 6. Non-functional requirements

| # | Requirement | Target | How we measure |
|---|---|---|---|
| NFR-1 | Size of `app.py` — stitching only | ≤ 120 executable lines | counted in the check |
| NFR-1b | Size of `guards.py` — three guards | ≤ 100 executable lines | counted in the check |
| NFR-2 | Check run | ≤ 60 s (**estimate**, not measured), offline, no key | `BUDGET_SECONDS`, the ceiling held by `check_all` |
| NFR-3 | Lesson length | ≤ 2500 words | the number-reconciliation check |
| NFR-4 | Share of failure modes | ≥ 1/3 of the stage's checks | a counter in the check |
| NFR-5 | Run without Docker | every check green or `NOT EVALUATED`, none red | `scripts/clean_install.py` |
| NFR-6 | Response time of the smoke script | ≤ 30 s (**estimate**, not measured) against a local build | timed inside the script itself |

**The numbers in NFR-2 and NFR-6 are marked as estimates deliberately.** Nobody has measured them
yet: the service has not been written. A number with no measurement behind it, put into a document
without the marker, becomes a claim that holds nothing up — and stages 2, 3, 4 and 5 caught this
class one after another. The marker comes off the moment the first run produces a real number, and
is replaced with "(measured N)".

**NFR-1 is named by the file, not by "the application module".** A budget with no name is satisfied
by splitting into N files of 119 lines each — which is to say, never satisfied at all.

## 6.1 Security and privacy

- **The key never reaches a log, a trace or a response.** What lives in the trace is a derived owner
  identifier, and the check asserts precisely the absence of the key from what was written.
- **An authentication refusal does not distinguish "no such key" from "key expired".** A difference
  in the response is an oracle for brute force.
- **The health endpoint is reachable without a key and therefore names nothing sensitive**: the
  names of the dependencies and their state, with no versions, addresses or connection strings.
- **The metrics endpoint is closed**, because aggregates disclose too: the number of requests per
  client is business information.
- **Request text is untrusted** — everything stages 2 and 5 know about that stays in force; the
  service weakens none of it.
- **The abuses this stage reproduces:** a request with no key, a request with somebody else's key,
  exceeding the rate, exhausting the budget, an unavailable dependency. Each has its own check.

## 7. KPIs

| # | Metric | Target |
|---|---|---|
| KPI-1 | The Learner brings the service up locally from scratch | ≤ 10 minutes following the instructions |
| KPI-2 | The Learner reproduces the two-worker trap and sees the number | 100 % via the exercise |
| KPI-3 | The smoke script passes against a local build | 100 % on a clean machine |
| KPI-4 | The Learner can name the three different failure mechanisms and what tells them apart | via the checklist |

## 8. Open questions

- [ ] Will a real deployment happen on a real VM, or will the stage stay with local verification?
      There is no access to a machine right now, so everything is built to work in both modes, and
      AC-08 in the part about "a valid certificate from a public authority" stays unverified until
      a machine appears. Default now: local verification with a self-signed certificate,
      `NOT EVALUATED` for the rest. — owner: Operator, due: before the `stage-06` tag
- [ ] Should the tracer be threaded down into stages 2 and 5? Right now they write no step at all:
      `store.search()` takes no tracer, and `Memory.context_for()` returns its reasons in
      `Context.skipped`. Because of this the service's trace shows **which branch** was chosen and
      does not show **why** exactly these documents and facts were found — that is, half of the
      promise that "the trace answers the question why" stays out of reach. Adding an optional
      `tracer=None` is an additive edit, but §3 requires an ADR for any edit to stages 1–5, and here
      it is apt: the question is not whether it is possible, but whether the boundary between stages
      was drawn in the right place. Default now: do not thread it; stage 8 will read the traces and
      then say what it is missing. — owner: Contributor, due: `design` of stage 6
- [ ] Is a separate endpoint needed for reading a trace, or is a file enough? Default now: a file,
      as in stages 1–5; an endpoint will appear at stage 8 if evaluation demands it. — owner:
      Contributor, due: stage 8
- [ ] `SDD-AC` trailers in commits — debt from stage 1, still not closed. Default now: it does not
      block stage 6, and is closed by a separate pass over all the stages. — owner: Contributor,
      due: before stage 7
