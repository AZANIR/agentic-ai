---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---


# 0009 — Allow a fake provider in the prod profile behind an explicit flag

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

`Settings.validate()` refuses to start in the `prod` profile when no real LLM is configured. The
guard is right and was put in at stage 0 with a clear reason: a service with no real provider
serves its users inventions.

It is also what stopped this stage's first real deployment.

The situation is not hypothetical. The `prod` profile is the only place where the **real adapters**
switch on: Postgres instead of a file, Redis instead of process memory. Checking them without
bringing the profile up is impossible; bringing the profile up without a paid key, equally so.
Which means the most expensive part of the stage would stay unchecked purely because the author has
no account with a provider.

That contradicts the course rule outright: **everything has to work offline and with no API key**.

## Decision drivers

- The same guard's three other checks (`API_KEYS`, `DATABASE_URL`, `REDIS_URL`) are absolute and
  stay that way. The question is only about the fourth.
- A permission that can be obtained **by accident** is not a permission but a hole.
- A permission that is not visible **from outside** will sooner or later serve real users with a
  fake, and nobody will know about it.
- The reader has to be able to bring the full build up at home — otherwise the stage about
  deployment cannot be worked through without renting a server and paying for a key.

## Considered options

1. **An explicit `ALLOW_FAKE_LLM=1` flag**, with health naming the provider in its answer.
2. **Leave the guard as it is**; check only the `local` profile locally.
3. **Remove the provider check** from the guard.
4. **A third profile** — something along the lines of `staging`.

## Decision outcome

**Chosen:** Option 1.

Option 2 means that two implementations out of four (Postgres, Redis) have no check at all in the
working mode. Precisely where the stage promises "the first real deployment".

Option 3 removes the guard altogether — and brings back exactly the defect it was put in against.

Option 4 looks tidy and adds a third set of behaviours that will have to be maintained in every
factory. There are two profiles not for want of imagination, but because every further one
multiplies by every adapter.

**The flag is named so that it cannot be set by accident.** `ALLOW_FAKE_LLM=1` is not an
abbreviation and not a technical toggle: it reads as a sentence, and everybody who sees it in `.env`
understands what exactly they have allowed.

**The permission is visible from outside.** Health (`/healthz`) names `provider: fake` or
`provider: real` — with no key, which means it is visible to monitoring and to anybody who has the
address. An exception that is not visible in health is a quiet exception, and a quiet exception one
day becomes an incident.

**The fake inside the service answers any prompt** (`FakeLLM(auto_reply=True)`), because a script
is impossible here by construction: the requests are written by the user. The answers have the
right **shape** and zero content, and that is named in the module itself.

## Consequences

**Positive**
- The production adapters get checked for real: Postgres, Redis, the proxy, TLS, the volume.
- The reader brings the full build up with no paid key — the course rule stays in force.
- The guard's three other checks are untouched.

**Negative**
- The guard has been weakened, and that weakening stays in the code forever. The compensation is
  visibility in health, not trust in discipline.
- Somebody can bring the service up with a fake and never look at health. The only thing that helps
  against that is monitoring that looks at that answer — and that is already stage 10.
- The auto-replying fake gives **contentless** answers. A demonstration of the pipeline — yes; a
  demonstration of quality — no, and no check claims it does.
