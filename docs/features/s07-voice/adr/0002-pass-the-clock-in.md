---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0002 — Time is passed in as a clock parameter, not read from the system one

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Stage 5 already decided that time is passed in as a parameter: otherwise the TTL check passes at
night and fails during the day. Here the same decision is needed for a different reason — a
**stronger** one.

A check that measures time with a real clock depends on the machine's load. It passes nine times
and fails the tenth, and that is the worst kind of check: it gets disabled.

And with it disappears **the only evidence for the stage's main thesis**.

## Decision drivers

- NFR-6: zero flickers out of twenty consecutive runs.
- A flickering check is worse than a missing one: a missing one is visible, a flickering one gets
  disabled.
- The numbers have to be the same for authors and for readers, otherwise they cannot be talked
  about.
- Live mode needs a real clock anyway — so the source has to be **swappable**, not faked once and
  for all.

## Considered options

1. **The clock is a parameter**, fake by default, real behind a flag.
2. **A real clock** plus wide tolerances in the checks.
3. **Mock `time.perf_counter`** in the checks.

## Decision outcome

**Chosen:** Option 1.

Option 2 looks simpler and hides its price in the tolerances. A tolerance wide enough not to
flicker on a loaded machine no longer distinguishes batch from streaming — that is, the check
stops proving the thing it was written for.

Option 3 works, and it makes the check depend on **where exactly** the code calls the clock. Move
the call one line up and the mock misses, and the check silently stops measuring.

**The fake clock does not sleep.** `sleep(200)` moves the counter by 200 and returns control
immediately. So a run that "takes" 1500 ms executes in milliseconds — and the twenty-run check
(NFR-6) becomes free.

## Consequences

**Positive**
- The same data always gives the same number. A flicker is impossible by construction.
- Twenty consecutive runs cost milliseconds.
- Live mode takes a real clock through the same interface.

**Negative**
- The pipeline has no right to call `time` directly — and a check has to watch for that,
  otherwise the rule lives until the first convenient exception.
- Fake time does not catch real effects: contention for the processor, garbage-collector pauses,
  network delays. The stage makes no claim about them either.
