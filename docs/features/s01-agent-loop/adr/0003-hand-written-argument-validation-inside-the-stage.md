---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-23"
feature_size: "S"
ticket: "n/a"
---

# 0003 — Validate arguments with hand-written code inside the stage

- **Status:** Accepted
- **Date:** 2026-08-23
- **Deciders:** Contributor, Tech Lead

## Context

The second failure mode from the source article: the model invents arguments the tool does not
expect. A check has to stand between the model's decision and the function call — that is the
line of trust. The question is not whether it is needed, but **whose code** writes it and **where
it lives**: inside the stage itself or straight in the shared layer.

Validation will also be needed by stages 3 and 4, so the decision affects more than stage 1.

## Decision drivers

- Transparent mechanics is quality goal №1: the reader has to see that the check is their own
  responsibility, not a library's behaviour.
- The validation module has to fit into ≤60 lines of executable code (spec §6).
- A tool's schema is already described as an ordinary dictionary — exactly the format that goes
  to the model.
- Duplication between stages 1, 3 and 4 is acceptable: the stages are deliberately self-contained
  (repository ADR 0002).

## Considered options

1. **Hand-written code inside the stage** — a separate module beside the loop; lifting it into
   the shared layer becomes an exercise at stage 3, when a second consumer appears.
2. **Straight into the shared layer `shared/`** — zero duplication between stages 1, 3 and 4.
3. **An off-the-shelf library (`pydantic` or `jsonschema`)** — shorter and more reliable in
   production.

## Decision outcome

**Chosen:** Option 1. Option 3 would replace ten lines of comprehensible code with a single call,
after which the reader would know that "validation somehow happens" and would not know what
exactly is being checked — at a stage whose entire point is to show the mechanics. Option 2 would
put a call into somebody else's function, instead of code before your eyes, at the very first
stage — that is, the same flaw, only inside our own repository.

Duplication here is not debt but **a teaching device**: stage 3 gets a ready-made exercise, "lift
validation into the shared layer", which is meaningful precisely because a second consumer already
exists.

**Explicitly decided:** no type coercion is performed. Text where a number was declared is a
rejection, not an invitation to guess. Silent coercion would hide the model's mistake in exactly
the place the reader has to see it.

## Consequences

**Positive**
- The reader sees ~40 lines that fully explain what "check the arguments" means.
- A validation rejection goes back to the model as the step's result — the loop does not die, and
  that is visible in the code.
- Stage 3 gets an exercise with a real occasion behind it rather than an artificial one.

**Negative**
- The validation code will be duplicated at stages 3 and 4 until it is lifted. Deliberate;
  recorded in SAD §11 as accepted debt.
- A hand-written implementation covers fewer cases than `jsonschema`: nested objects and arrays
  are not supported at this stage. The lesson has to name that boundary, or the reader will carry
  the code into production and be surprised.

**Neutral**
- Moving to a library is a swap of one module behind the same interface; at stage 6, where
  validation becomes the line of trust of a public endpoint, that will be the right move.

## Links

- Spec: [[../spec.md]] AC-03, §6 (size of the validation module)
- SAD: [[../sad.md]] §4, §5, §8, §11
- Stage article: [Three Guards Every Agent Loop Needs](https://artstroy.net/articles/three_guards_every_agent_loop_needs) — failure mode 2
- Related ADRs: [[0001-split-stage-into-four-responsibility-modules]]
