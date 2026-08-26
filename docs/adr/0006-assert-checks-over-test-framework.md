---
status: Accepted
owner: "Repository owner"
reviewers: []
updated_at: "2026-08-22"
feature_size: "n/a (foundational decision for the repository)"
ticket: "n/a"
---

# 0006 — Check stages with bare asserts in check.py against a deterministic fake LLM

- **Status:** Accepted
- **Date:** 2026-08-22
- **Deciders:** repository owner

## Context

Every stage needs a check the reader can run themselves to find out whether they got it right.
The difficulty is that an agent's behaviour depends on an LLM — non-deterministic and paid for. A
normal test against a live model would be flaky, slow, and would cost money on every run.

## Decision drivers

- A check has to pass offline, with no API key, in seconds (map: Constraints).
- **Failure modes** have to be checked (the endless loop, malformed arguments, the limit firing),
  not only the happy path (spec §11, item 4).
- A beginner should not have to learn a test framework in order to take a course about agents.
- CI has to be green with no secret anywhere in the repository.

## Considered options

1. **`check.py` with bare `assert` plus `shared/fake_llm.py`** — a deterministic fake replaying a
   pre-set script of responses and tool calls.
2. **`pytest` with fixtures and mocking** — the industry standard, with reports and
   parametrisation ready made.
3. **No automated checks, only a demo script** — the reader looks at the output and decides.

## Decision outcome

**Chosen:** Option 1. The decisive argument is not simplicity but **the ability to check
failures**: a fake that *always* asks for another tool call proves the step limit fires, and that
check cannot be written against a real LLM at all. Option 2 would give the same thing while
adding a framework, configuration and new vocabulary to a course that already introduces some
forty terms. Option 3 leaves the reader no way to learn that they got it wrong.

The fake LLM here is **a teaching instrument, not a mock for a test's sake**: it makes a
non-deterministic system observable.

## Consequences

**Positive**
- Zero barrier: `python -m stages.sNN_slug.check`, and that is all.
- CI needs no secrets and does not depend on a vendor being up.
- The scenarios checked are exactly the ones that cannot be reproduced against a live model.
- The reader can read the response script in `fake_llm` — literally seeing what is expected of
  the LLM.

**Negative**
- No parallel runs, reports, parametrisation, `--lf` or the rest of pytest's conveniences.
- As the number of checks grows, a stage's `check.py` gets long and has to be split by hand.
- The fake checks **the logic around** the LLM, not the quality of the model. Real quality is
  measured separately, at stage 8 — and the lesson has to say so, or the reader overreads a green
  check.

**Neutral**
- Moving to pytest is mechanical: rename `check_*` to `test_*` and delete `main()`. Worth doing
  if the repository ever grows beyond the course.

## Links

- Spec: [[../../planning/2026-08-22-agentic-ai-course-design.md]] §5.3, §11
- Architecture map: [[../architecture-map.md]] §Conventions
- Related ADRs: [[0002-profile-switched-adapters]], [[0005-tracing-from-stage-one]]
