---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0003 — Run the scheduler as its own process, not as part of the application

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

A periodic job (clear out what has gone stale, total up the day's spend) obviously belongs to the
service. A scheduler library can start inside the application in two lines, and that is exactly how
most examples are written.

With two workers there are two such schedulers. The job runs twice per interval.

This is the same defect as with the counters, in a second outfit — and so the stage shows **both**
faces of one cause: process-local state stops being true the moment there is more than one process.

## Decision drivers

- A job run twice is sometimes harmless and sometimes catastrophic. The difference is decided not
  by the scheduler but by what the job does — which means harmlessness cannot be relied on.
- The trap has to be **reproduced live**, not described: the reader has to see the number "2" in
  their own log.
- The fix has to be as simple as the defect — otherwise the reader will not apply it.

## Considered options

1. **A separate process** with exactly one instance of the scheduler.
2. **A distributed lock**: every worker has a scheduler, and whoever gets there first takes the job.
3. **The operating system's own scheduler**, poking the service.

## Decision outcome

**Chosen:** Option 1.

Option 2 works and costs more than it looks: the lock has to be taken, released, and then survive a
process that died holding it. It is the right decision for jobs that have to run **often** and
**fast**; for a daily cleanup it pays complexity for a property nobody asked for.

Option 3 moves the schedule out of the application and into the machine. The schedule stops being
part of the code, which means it stops being visible in review and stops travelling with the
service.

**The trap deliberately stays in the repository** — behind a flag, not in a comment. The exercise
switches the scheduler on inside the application, the reader sees the doubling, switches the flag
off and sees a single run. A defect described in prose is not remembered.

## Consequences

**Positive**
- The job runs exactly once, no matter how many workers there are.
- The trap can be shown live and switched off with one flag.
- The scheduler scales separately from the service.

**Negative**
- One more process in the deployment: one more container and one more place where something can
  fail to come up. Health has to speak about it too.
- A dead scheduler is invisible in the service's metrics. Named in the RUNBOOK.
