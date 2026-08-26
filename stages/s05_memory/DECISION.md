# What to remember at all

The simplest memory stores everything the user said. It works for one day. After that retrieval
returns four facts about the same thing, contradictions accumulate faster than facts, and the
answer slowly degrades — with no error in the code at all.

So the "remember this?" decision is made **before** the write and is made the same way every
time. Otherwise memory depends on whoever wrote the call site.

## The checklist

Six questions in order. **The first one to fire is the answer**; we do not go further.

| # | Question | If yes | Why |
|---|---|---|---|
| 1 | Is this a secret, or something that must not be stored? | **do not store** | secrets are not stored even on a direct request |
| 2 | Is this about the world rather than about the person? | **do not store** | knowledge about the world lives in search (stage 2), not in memory |
| 3 | Is this derivable from what is already stored? | **do not store** | a derived fact adds volume and a reason for contradiction |
| 4 | Did the person directly ask to remember it? | **store** | a direct request is the strongest signal we have |
| 5 | Is this a property that will outlive this conversation? | **store** | facts like these are what make the second session different from the first |
| 6 | Everything else | **do not store** | a one-off is not remembered — it is simply used and forgotten |

## The order is the checklist

The rules apart from the order are worth nothing. The telling line:

> "Remember my password — hunter2"

That is a **secret** (question 1) and a **direct request** (question 4) at once. The answer
depends exclusively on which of them comes first. Put the request first — and memory stores
passwords while staying "by the checklist".

So in `decision.py` the order is a `tuple`, not a set, and a check asserts the position: the
secret's index is lower than the request's. A mutation that swaps them goes red.

## What the code does here, and what a human does

The code **does not classify**. Whether a line is a secret, whether it is derivable from what is
already stored — that is decided by a human or a model, and no heuristic over the text replaces
it. The code holds two things: the order of the questions and the rule "the first one to fire".

That looks like very little. But those are exactly the two things that break quietly:
classification errs visibly, and order does not.

## A dead rule

A rule that no situation triggers looks like work and does nothing. A checklist with such a rule
passes any check of the form "every situation has an answer" — and silently loses half its
meaning.

So the check runs **both ways**: every situation has a rule **and** every rule has a situation.
This is the same mirrored requirement as with the owner filter in `long_term.py`, and the same
lesson as on stages 2 and 3: both halves have to be claimed, because the second one never
appears on its own.

The set of situations lives in `check.py` rather than next to the rules. Written by the same
hand, a rule and a situation would only prove that the author wrote the same thing twice.

## What the checklist does not decide

**It does not decide whether a fact is true.** "I live in Kyiv" is stored the same way whether it
is so or not. Memory stores what was said, not what was verified.

**It does not decide when to forget.** That is TTL (`facts.py`) and replacement by topic
(`long_term.py`) — separate mechanisms with separate decisions (ADR-0002, ADR-0003).

**It does not decide what to do with a secret that already reached the file.** Deleting what has
been written is the store's job, that is, stage 6's.
