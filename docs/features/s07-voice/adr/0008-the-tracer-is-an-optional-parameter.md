# 0008 · The tracer is an optional pipeline parameter

- Status: Accepted
- Date: 2026-08-25
- Context: stage 7 (voice), AC-11; `CONVENTIONS.md` — a trace is present from stage 1

## Context

AC-11 requires reconciling the printed breakdown against the steps in the trace: two independent
mechanisms that have to give the same answer. The course's convention demands the same —
`shared.trace` is present from the first stage, and stage 8 will build evaluation on top of
ready-made trajectories.

The first edition of the stage had **no trace at all**. `grep -rl shared.trace stages/s07_voice`
gave zero files, against 4/2/4/2/2/3 on the earlier stages. The check that carried the name AC-11
asserted only that `ws.py` contains the line `from stages.s07_voice.pipeline import` — that is,
it reconciled an import, not numbers.

And the pipeline has to stay a pure function: the checks run it hundreds of times and must not
write to disk.

## Decision

`batch()` and `streaming()` take `tracer` as an **optional** parameter. The default substituted
is `_Untraced` — an object with an empty `step()`.

A null object, not `if tracer is not None:` before every call: seven branches in a pipeline of
fifty-odd lines read worse than one three-line class, and every one of them is a place where
somebody will forget the check.

The demo opens `trace_run(...)` and passes the tracer into the scenes; the AC-11 check writes to
a temporary file and reconciles the numbers from both mechanisms.

## Consequences

**Good.** The checks stay offline and leave no traces on disk. The demo writes a real trace into
`traces/`, which stage 8 will read. Reconciliation becomes possible: time to first audio in the
trace has to equal the number from the breakdown, and the sum of the model's steps in the trace —
the model's step in the breakdown.

**The price.** A default of "we write nowhere" means a forgotten tracer is not noticed at once —
the code works, the trace is empty. The guard: the reconciliation check goes red if there are no
steps in the trace.

**The limit.** What goes into the trace is **numbers and reasons**, not content: the text of the
answer is not there, and that is a separate assertion in the check (AC-10b). A session leaves
numbers behind it.

## Alternatives considered

**Always write to the trace.** Every check run touches the disk; hundreds of runs in the mutation
harness — hundreds of files. Plus the checks stop being independent of one another.

**A global module-level tracer.** Exactly the defect stage 6 has a whole lesson about, and one
this stage has already reproduced once in `streaming.last_timing`. Two simultaneous runs would
overwrite each other's trace.

**Do not trace at all, leaving AC-11 to the breakdown.** Then "two independent mechanisms" is one
mechanism named twice, and there is nothing to reconcile against. Plus stage 8 gets no input data.
