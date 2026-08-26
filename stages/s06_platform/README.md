# Stage 6 — Platform: five capabilities become a system

After five stages the repository holds an agent loop, search, routing, tools across a process
boundary and memory. Each of them works. **There is no system.**

This stage stitches them into one service and shows that going to production is not "the same
thing, only on a server".

## What you will be able to do after this stage

- Bring up one service that answers using all five previous stages
- Tell the three boundary mechanisms apart — who, how often, at whose expense — and their three
  failures
- Explain why metrics do not answer the question "why did the agent decide that"
- Reproduce the two-worker trap **live** and see both of its halves
- Deploy behind HTTPS and verify it with one script that works locally and on a domain alike

## Run this before reading

```bash
python -m stages.s06_platform.run           # seven scenes, no key, no containers
python -m stages.s06_platform.run --trace   # plus one request's trace
python -m stages.s06_platform.check         # 69 checks
```

Watch the **sixth** scene. The others show that the service works; that one shows that it stops
being true the moment there are two processes.

## Part 1. What changes in production

A prototype answers the question **"does this work?"**. Production answers a different one:

> **What happens when it breaks at three in the morning, and who finds out.**

Three things that were not in the prototype and could not have been:

    boundaries   who is allowed to ask, how many times, and at whose expense
    visibility   what the service is doing now and what it was doing when nobody was watching
    life         it survives a restart, an upgrade, and a second process alongside

The last one is the most treacherous, and half of this stage is devoted to it.

## Part 2. The most important sentence of the whole stage

> **State in process memory stops being true the moment there is more than one process. And it
> stops silently.**

A prototype lives in one process. Any counter, cache or schedule in memory works flawlessly. A
second worker makes every one of them untrue — with no error, no exception, no line in the log.

That one cause has **three faces**, and the stage shows all three:

| Where | Consequence | Is it visible |
|---|---|---|
| Scheduler | the job runs twice per interval | in the logs — if anybody is looking |
| Counter | a limit of 30 passes 60 | **nowhere**: the service behaves normally |
| Metrics | the endpoint serves one worker's slice | until the numbers start "almost reconciling" |

**The second matters more than the first.** A doubled job gets noticed; a doubled limit means the
boundary quietly became something else, and no monitor will say a word about it.

## Part 3. Three gates — three mechanisms, not "security"

`guards.py`, 40 lines. What matters most here is the **order**:

    1. who you are         without it there is nobody to count and nobody to charge
    2. how many times      the cheap check before the expensive one
    3. at whose expense    counting the spend of the rejected is wasted work

A rate limit before authentication would count every anonymous caller as one client: a single
attacker would close the service for everybody else. A budget before the rate limit would spend
its bookkeeping on those who are going to be rejected anyway.

**No gate reaches the model.** A breaker that fires after the spend is called a report.

Three details, each of them a decision:

**The key comparison is constant-time.** A plain `==` finishes at the first differing byte, which
means the response time tells you the length of the shared prefix. The price of the right
comparison is one function from the standard library; the price of the wrong one is a key guessed
one character at a time.

**A refusal does not say whether such a key exists.** "No such key" and "expired" sound the same.
A difference in the answer is an oracle: keep trying until the text changes.

**The key never leaves the module.** What goes into the trace, the metrics and the counter keys is
a derived owner identifier. A key in a trace is a key in a file read by whoever is debugging.

## Part 4. Health and metrics answer different questions

    health    whether the service and each dependency are working RIGHT NOW
    metrics   how much of what happened over a period, and of which kind
    trace     WHY the agent decided that

Confusing the first two with the third is the most expensive observability mistake. A metric will
say that 3 % of requests were rejected and will not say **why those three**.

**Health names every dependency separately.** "The service is alive" with no list is the answer
that keeps the monitor quiet until a user complains: the process really is alive, the database has
merely been unreachable for an hour.

**The reason is the error's type, not its text.** The database driver's text carries the address,
the user and the port, and health is read by somebody who has no key.

**Health is public, metrics are closed.** The number of requests per client is business
information.

## Part 5. Mirrored halves — again, and not by accident

This stage has **four** pairs, and no second half follows from its first:

| Claims | Satisfied by an empty result |
|---|---|
| somebody else's was rejected | a gate that lets nobody through |
| the unhealthy dependency was named | health hard-wired to "broken" |
| a failure gives a non-zero exit code | a script that always fails |
| somebody else's memory did not arrive | an empty result |

This is the fifth stage running where a review finds a check with the right verdict and too weak a
claim. Here they were written in pairs from the start — and even so two of them passed **empty**
in our own smoke script: "health does not expose the connection string" went green on an empty
body, and "the service is alive" matched an `up` that belonged to a dependency while the service
itself was `down`.

## Part 6. What deploying itself found

Four defects. Not one of them is visible from the code or from the checks:

**The volume belonged to root** while the process runs as an unprivileged user. The first trace
write gave `PermissionError`, the proxy returned `502`. Locally the directory belongs to whoever
started the command, so this can only be seen inside a container.

**Nobody had applied the migrations.** The table was not there — and the first failed query left
the transaction in an aborted state. The service stayed dead **after the cause was gone**: this is
a "memory of the past" defect, and no test sees it, because every test takes a fresh connection.

**The configuration refused to start `prod` without a paid key** — stage 0's guard fired correctly
and blocked verification of the real adapters. The resolution is an explicit flag, visible in
health (ADR-0009).

**The scheduler restarted silently.** Nothing pokes it from outside, so it can only be noticed
through `ps` or the log — exactly what ADR-0003 named as the price of moving it into its own
process.

## Part 7. What to break

```bash
python scripts/mutate.py s06          # all eighteen mutations
python scripts/mutate.py s06 --expect # and check them against the promised numbers
```

The three most interesting leave the code **working and wrong**: the counter becomes
process-local, the owner filter disappears from the query, the budget is checked before the rate
limit.

The walkthrough is in [`exercises.md`](exercises.md).

## The limits of this stage — so you do not carry them into production

- **One key, one owner.** There are no roles, permissions or per-team quotas; revoking a key needs
  a restart (ADR-0006).
- **The budget counts an estimate**, not the provider's invoice. A breaker has to fire before the
  catastrophe, not balance the books.
- **Metrics are process-local.** With N workers the endpoint serves one worker's slice. A
  multi-process collector is what production does; here it is named, not hidden.
- **The trace does not explain retrieval.** Stages 2 and 5 write no steps, so the trace says
  "which branch" and does not say "why these documents" (ADR-0005).
- **Certificate trust was not verified.** Locally it is self-signed by construction, and the smoke
  script marks that as a third state rather than a pass.
- **There are no backups.** `down -v` erases both facts and traces; copies are stage 10.

## Numbers

**69 checks, 57 of them on failure modes.** Modules: `app.py` — 66 of 120 lines allowed,
`guards.py` — 40 of 100. Smoke against a live build: 10 passed, 0 failures, 1 not verified.

## Next

Stage 7 — **voice**: the same pipeline twice, batch and streaming, with measurement. The stage's
questions: why 600 ms, why p95 matters more than the mean, and what a synchronous tool call costs
when a human is waiting at the other end.
