---
status: Accepted
owner: "Contributor (course author)"
reviewers: ["Tech Lead"]
updated_at: "2026-08-24"
feature_size: "S"
ticket: "n/a"
---


# 0002 — Parse the marked block, not the whole response

- **Status:** Accepted
- **Date:** 2026-08-24
- **Deciders:** Contributor, Tech Lead

## Context

An MCP server's response is text. It may contain data, or it may contain data **together with
prose around it**: explanations, warnings, reminders. That is not a defect of a particular server
but a property of the format: a server is allowed to speak.

The source article describes exactly this trap as a real one.

## Considered options

1. **Extract the marked block and parse that.**
2. **`json.loads` on the whole response** — works as long as the server keeps quiet.
3. **A regular expression over the whole text** — find something that looks like JSON anywhere.

## Decision outcome

**Chosen:** Option 1.

Option 2 breaks on the very first server that is polite. And it breaks in the worst way: a
`JSONDecodeError` mid-call, from which it is unclear whether the server broke or merely said
hello.

Option 3 is worse than both, and that is worth naming: a regular expression will find
**something** almost every time. Prose contains curly braces; an explanation contains an example.
A parser that takes the first thing that looks right will one day take an example out of the
documentation instead of the data — and will say nothing about it.

A marked block gives an unambiguous boundary: what is between the markers is data; what is
outside them is none of our business.

**A consequence that has to be a state of its own:** if there is no block **at all**, that is not
an empty result. "The server returned nothing" and "the server returned an empty list" are
different events with different causes, and merging them means losing half the diagnostics
(AC-03b).

## Consequences

**Positive**
- Prose around the data stops being a problem.
- The absence of data is named rather than guessed.
- Parsing is checkable **without a server**: feed it a string, look at what comes out. Which is
  why it lives in a module of its own.

**Negative**
- A server that sets no markers needs a branch of its own. Named in the lesson as a boundary:
  real servers differ, and the first thing to do with a new one is to look at the raw response.
