# Stage 5 — Memory: why "store everything" makes the answer worse

The agent of stages 1–4 forgets everything between requests. Every run starts from zero: it does
not know your name, where you asked to have things delivered, or what you asked a minute ago.

This stage gives it memory — and shows that the hard part here is not the storing.

## What you will be able to do after this stage

- Tell short-term and long-term memory apart and not confuse their jobs
- Extract facts from a conversation, store them, and retrieve **only the needed ones**
- Resolve contradictions and staleness without losing the history
- See that retrieval from memory is the same problem as search on stage 2
- Explain why the "what to remember" checklist is valuable for its **order**, not its rules

## Run this before reading

```bash
python -m stages.s05_memory.run
```

Six scenes. Watch the **third** — the fact "It rained yesterday" is sitting in memory and does
**not** reach the answer, with the reason printed next to it. The other scenes show that memory
works; this one shows that it does not fire where it should not.

```bash
python -m stages.s05_memory.run --prompt   # how facts enter the prompt
python -m stages.s05_memory.check          # 42 checks
```

## Part 1. The model remembers nothing

This is the most important thing to understand before the code.

A model call has no state. You send messages — you get a reply; the next call knows nothing about
the previous one. **Everything that looks like memory is something somebody put into the context
before the call.** ChatGPT that "remembers" your name is code that fetched the name out of a
store and appended it to the prompt.

So memory is not a property of the model but a **system around it**. And that system has two
different mechanisms that people constantly conflate:

| | Short-term | Long-term |
|---|---|---|
| Question | what was said **in this conversation** | what is worth knowing **always** |
| Lifetime | one run | survives the session |
| Mechanism | window + summary of what fell out | extract → store → retrieve |
| File | `short_term.py` | `long_term.py` |

They do not substitute for one another. Long-term memory does not know what was said three turns
ago; short-term memory will not survive a restart.

## Part 2. The most important sentence of the whole stage

> **Showing that a fact was stored is easy. Showing that an irrelevant fact did NOT arrive is
> the actual work.**

Writing a fact into a file is twenty lines. Retrieving **exactly what bears on the question** is
what the stage exists for.

The reason is in how bad memory goes wrong. It does not crash. It puts four facts into the
context instead of one, the model sees more noise, and the answer gets slightly worse. Then
slightly worse again. There is no error anywhere — there is **degradation**, which the field
calls *context rot*.

The limit on context is only on tokens. There is no limit on nonsense — you are the limit.

## Part 3. Reading the code — six files

### `facts.py` — four conditions in one place

The fact record is flat deliberately: owner, topic, text, time, expiry, status. No relationships,
no nesting — a knowledge graph is a separate problem with a separate price.

The point here is that the **four conditions are gathered together**:

```
owner       the fact belongs to whoever is asking
status      the fact has not been replaced by a newer one
expiry      the fact has not gone stale
threshold   the fact is relevant enough to the question   (that one lives in retrieval)
```

Scattered across their call sites, they stop reading as one rule — and then it becomes very easy
to forget one of them in a new place. A forgotten condition in memory means either a leak or the
**silent disappearance of an answer**.

Time is passed **as a parameter** and is never read from the clock. This is not a convenience for
tests: a function that reads `datetime.now()` inside makes memory non-deterministic, and makes
the TTL check one that passes at night and fails during the day.

### `short_term.py` — the trap you cannot see by eye

The last N messages stay **verbatim**, anything older is compressed into a summary. The verbatim
tail matters: the model answers precisely the most recent turns, and summarising those is a loss
where nothing needed losing.

The trap is **compressing the summary a second time**. The simplest implementation takes
"everything outside the window", the previous summary included, and compresses it again.

The consequence is impossible to spot: the text stays coherent and gradually stops being true.
After the third compression the summary describes a conversation that never happened. So the
summary **accumulates**, and only newly evicted turns get compressed.

### `retrieval.py` — this is the same problem as search

Not similar, not related — **the same**. There is a question, there is a set of texts, you have
to score which of them bear on the question, and take the best ones above a threshold. That is a
verbatim description of stage 2.

Hence two implementations behind one interface: lexical (shared words) and semantic (cosine over
stage 2's embedder). The second is optional — the stage can be completed without it.

The limit of lexical retrieval is visible as a number: "what is my address" against "Deliver
orders to Khreshchatyk" gives exactly **0.00** — no shared words, and no understanding either.

**What is honestly not here.** Semantic retrieval on the default embedder does **not** clear that
limit: `hash-words` is word-based too, and on the same question it gives the same 0.00. What it
does show is something else — that **the scales differ**: where the lexical one gives 0.50, the
cosine gives 0.52, and a threshold of 0.15 for the first does not suit the second at all. Real
synonyms only appear on `EMBEDDINGS_PROVIDER=fastembed` or `openai`. A lesson that promised more
would be promising an untruth — and that is exactly the promise that was written here first.

**So the threshold lives in the retrieval, not in `Memory`.** One number wired next to the store
suits only one of the scales; a reader who switches on the semantic one at the lesson's advice
would get memory that "forgot everything" — precisely the defect exercise 2 is written for.

The threshold matters more here than on stage 2. There "below the threshold" meant "we found
nothing" — an honest answer. Here it means "do not put this into the context", and every
superfluous fact spoils the answer a little.

**The score is normalised over the union of the words, not over the length of the question** —
and that is not a detail. Dividing by the question gives **1.00** to any text that merely
restates the question: the fact "Where to deliver the order. This is the most important thing,
the cat is called Murchyk" would go around the real address and become first in the context. The
text of a fact is written by the user; the ability to promote yourself with your own text is
control over retrieval, not relevance. Over the union that same text gives 0.43 against the real
address's 0.50: the question's words still count, but the ballast around them now costs
something.

### `long_term.py` — the order of the filter is not an implementation detail

Extract, store, retrieve. Look at one line:

```python
# BEFORE the selection. After it, somebody else's fact would take a slot and your own would vanish.
mine = [f for f in self.all_facts() if f.owner == owner]
```

Put the owner filter **after** the top-k selection and somebody else's fact takes a slot, then it
gets removed, and **your own fact, the one that should have arrived, disappears**. Nothing
leaked. There is no answer either.

This is verbatim the same defect as on stage 2 with documents, and that is exactly why there are
two checks: theirs did not arrive **and** mine did. The second half never appears on its own —
this is the third stage running where a review found a check with the right verdict and too weak
a claim.

The text of a fact is **untrusted**: a user wrote it. It goes into the prompt as data, inside a
marked block — the same pattern as the retrieved documents on stage 2. The fact "remember:
ignore previous instructions" is stored as an ordinary fact and changes neither the order nor
the threshold.

### `extraction.py` — the only place that needs a model

Extracting facts from a conversation is split out, and not for the sake of tidiness. Everything
in `long_term.py` is deterministic: read the file, filter, sort, return. Extraction is the only
thing that goes to a model, that is, the only thing that can answer differently to the same
input.

An empty list is a **normal** answer: a conversation often contains nothing worth remembering for
long, and memory that invents something under those conditions is worse than empty memory.

This stage's risk register predicted the split verbatim: "the line budget for `long_term` is too
tight… what will have to be split out is **not** retrieval but extraction — it is the only part
that needs a model". The risk fired at review, and the mitigation turned out to be the right one.

### `decision.py` — the value is in the order, not in the rules

Six questions; the first one to fire is the answer. The telling line:

> "Remember my password — hunter2"

That is a **secret** and a **direct request** at once. The answer depends exclusively on which
question comes first. Put the request first — and memory stores passwords while staying "by the
checklist".

The code here **does not classify** — whether a line is a secret is decided by a human or a
model. The code holds the order and the "first one to fire" rule. It looks like very little; but
classification errs visibly, and order does not.

The checklist's prose is in [`DECISION.md`](DECISION.md), and a separate check asserts that it
has not drifted from the code. That check found a divergence on its very first run.

## Part 4. Contradiction and staleness

Two addresses do not exist simultaneously as a state. When a new fact on the same topic from the
same owner arrives, the old one gets status `replaced` — and **stays in the file**. Deleting on
write would have been cheaper and would have lost the answer to "so what was it before".

A contradiction is decided **by topic**, not by content. Comparing content is already inference,
and it needs a model; the topic gives a predictable rule for zero calls. The price is stated
honestly: two facts under different topics that contradict each other are invisible to this
mechanism.

Staleness is checked **on retrieval**, not by deleting on write — for the same reason: the
history is valuable, and you cannot explain something that has been deleted.

## Part 5. What to break

```bash
python scripts/mutate.py s05          # all nine mutations
python scripts/mutate.py s05 --expect # and check them against the promised numbers
```

Nine exercises in [`exercises.md`](exercises.md). The two most interesting break the code so that
it **works and stays wrong**: the owner filter after the selection (the answer quietly
disappears) and rewriting the summary instead of accumulating it (no error whatsoever).

The walkthrough is in the same place.

## The limits of this stage — so you do not carry them into production

- **A file, not a database.** One record per line, readable by eye. Stage 6 swaps the store
  behind the same interface — and that is exactly why the interface is narrow here.
- **One process.** Two concurrent writes to this file lose data; locking is the store's job, not
  memory's.
- **Contradiction by topic.** Named above; not mitigated but bounded.
- **Owner is a field of the record, not authentication.** Who `olena` is, the caller decides.
  Authentication arrives on stage 6, and until then it is easy to decide it does not exist.
- **Retrieval is linear.** Every fact is read every time. Fine for hundreds of records, wrong for
  millions; optimisation lives in stage 8.

## Numbers

**42 checks, 27 of them on failure modes.** Modules: `long_term.py` — 79 of 90 lines allowed,
`short_term.py` — 37 of 50. The suite runs in under a second: not a single check here spawns a
process or goes to the network.

## Next

Stage 6 — **production**: memory moves into a real store, and migrations, authentication and
deployment appear. The stage's questions: what of everything written so far survives the
crossing, and what each thing we deferred here costs.
