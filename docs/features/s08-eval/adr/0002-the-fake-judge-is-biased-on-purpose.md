---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-25"
feature_size: "M"
ticket: "n/a"
---

# 0002 — The fake judge is biased on purpose

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Contributor, Tech Lead

## Context

The stage's central demonstration: swapping two answers around changes the judge's verdict. The
reader has to see that **on a run of their own**, not read a retelling of somebody else's
research.

Course rule no. 4: everything works offline and without an API key. The judge is a model. So
without a key there is nothing to judge with, and the demonstration is impossible.

There is a tempting but wrong answer here: "show the bias on a real model and simply skip it
offline". Then the stage's central claim is checkable only by whoever paid, and everybody else
is reading an assertion.

## Decision drivers

- AC-05 has to be **reproducible** offline, otherwise it is not a criterion but a promise.
- The check must not flicker: a real model gives different verdicts on the same data, and a bias
  detector running against it would be non-deterministic (NFR-6).
- The reader has to understand what is proven and what is not. A hidden substitution here would
  cost the trust of the whole stage.

## Considered options

**A. The real model only.** Honest, but unavailable and non-deterministic. The stage stops
passing offline.

**B. Recorded answers from a real model.** Looks like a compromise and is the worst option:
recordings go stale silently, and the reader believes they are looking at a live model.

**C. A fake, biased on purpose, inside an honest frame.**

## Decision

**C.** The fake judge implements a **documented** bias: all else being equal it picks the first
of the answers presented, and adds a point for length. This is not an imitation of any
particular model — it is the role of **a broken instrument**, the same role a mutation plays in
the checks of stages 1–7.

The frame is stated in the lesson's first line, not in a footer:

> The fake does not prove that real judges are biased. It gives the detector something to
> detect. With a key, the same detector runs against a real model and prints the same report.

## Consequences

**Good.** The demonstration is reproducible offline and deterministic. The detector is checked by
**both** halves: against the biased judge it finds bias, against the stable one it reports
agreement (AC-05b). A detector that always finds bias is not a detector.

**The price.** The reader may decide that the bias was demonstrated on a real model. Against
that: the frame in the lesson, the class name (`BiasedJudge`), and the fact that the `--real`
flag leads to the very same check against a model.

**The limit.** The magnitude of the fake's bias says nothing about the magnitude of real models'
bias. The stage shows **that the mechanism exists and how to catch it**, not a number.
