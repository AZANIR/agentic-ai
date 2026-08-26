---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "M"
ticket: "n/a"
---

# 0006 — The live-mode page is one HTML file with no build

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

Live mode needs a page: a microphone, a button, an indicator, audio playback and the same numbers
as in the run.

The smallest "modern" option is a frontend framework with a build. That means `node_modules`, a
build command, configuration and one more tool that will have to be maintained for seven stages
running.

## Decision drivers

- The stage is about **latency**, not about assembling interfaces.
- The reader should open the file and see the whole of the page's code at once.
- The course has had no frontend at all so far, and starting up a stack for the sake of one page
  is the most expensive way to get a button.
- The architecture map honestly says `frontend: ""` — this stage fills it in, and fills it in
  with what is really there.

## Considered options

1. **One HTML file** with an inline script; no build at all.
2. **A frontend framework** with a build.
3. **No page at all** — only a command-line client.

## Decision outcome

**Chosen:** Option 1.

Option 2 adds a tool nobody in this course teaches and which will have to be updated. The price
is permanent, the benefit zero for one page with two buttons.

Option 3 deprives the stage of a microphone, that is, of the main thing: hearing the pause with
your own ear.

**The microphone turns on only after an explicit action** (AC-10) — and that is not politeness
but a requirement: a page that takes the microphone on load violates consent regardless of what
it does with the audio afterwards.

## Consequences

**Positive**
- Zero dependencies and zero build commands; the page opens as it is.
- All the code is visible in one file — it can be read in a single sitting.
- Stage 10 will inherit the page with no tooling at all.

**Negative**
- The page is primitive: no state, no routing. For two buttons that is an advantage, for anything
  bigger it is not, and stage 10 will decide again.
- With no build there is no type checking in the script either. The price is accepted: the script
  is short.
