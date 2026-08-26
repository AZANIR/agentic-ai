---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0001 — Delays are faked by default, real models come behind a flag

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

The stage measures time. The most obvious way is to take the real `faster-whisper` and `piper`,
run them and write the numbers down.

That gives a check weighing two gigabytes of weights, running for a minute and giving
**different numbers** on every machine — that is, a check that can neither be run in CI nor used
as evidence.

## Decision drivers

- The course's rule: everything works offline, with no key and no downloading of models.
- NFR-6 demands zero flickers out of twenty runs. A real model on a loaded machine will never
  give that.
- The stage's thesis is about **pipeline architecture**, not about how fast models are. A number
  that depends on the graphics card does not prove the thesis.
- The reader has to be able to hear it for real — so live mode is needed.

## Considered options

1. **Fakes by default, real models behind a flag.**
2. **Real models only.**
3. **Fakes only**, with no live mode.

## Decision outcome

**Chosen:** Option 1.

Option 2 puts the stage out of reach for a reader without a graphics card, and makes the check
flicker.

Option 3 is more honest than 2, and it takes away the one thing that makes a stage about voice
interesting at all: hearing it with your own ear. The numbers stay an abstraction until you hear
the pause.

**The fake here is not a stub but a model of the delay.** It sleeps a set number of
milliseconds, picked to the **order of magnitude** of the real one: recognising a second of
audio costs hundreds of milliseconds, generating the first token — hundreds, synthesising a
phrase — hundreds. The proportions are preserved, the absolute numbers are not, and the lesson
says so in its first line.

**Most important: the fake does not really sleep.** It moves the **fake clock** (ADR-0002). A
measurement run takes milliseconds of real time and gives the same numbers on any machine.

## Consequences

**Positive**
- The checks are deterministic, fast, and pass in CI with no dependency at all.
- The numbers are the same for the author and for the reader — that is, they can be talked about.
- Live mode exists and turns on with one flag.

**Negative**
- The numbers are **not** a promise of performance. That is named in the lesson, in the spec and
  in §11 risks — three times, because this is exactly what will be misread.
- Live mode is only checked where there is a microphone and the models. Everywhere else —
  `NOT EVALUATED`.
