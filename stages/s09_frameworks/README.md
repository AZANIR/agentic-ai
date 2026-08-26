# Stage 9 — Frameworks: your own numbers instead of someone else's claim

> **A framework is scaffolding, not architecture.** Scaffolding speeds up construction and says
> nothing about what you are constructing. Chosen before the shape of the building is known, it
> **becomes** the shape.

Eight stages built the system by hand. The question most people start with was never asked once:
**"which framework should I take?"** That is not an accident, it is the construction of the
course. The question comes ninth because it can only be answered against something to compare
with.

## What you will be able to do after this stage

- Name **where exactly** coordination lives in each of the four implementations — and what it
  costs to find out why this particular step ran.
- Say how many lines you actually wrote and how many work invisibly on your behalf.
- See how many tokens a framework adds **of its own**, on top of what you asked for.
- State the choosing rule as **constraint → tool** rather than as a "winner".
- Notice the constraint that settles the choice **first** and that no blog post writes about.

## Run this before reading

```bash
python -m stages.s09_frameworks.run     # six scenes, no key, no network
python -m stages.s09_frameworks.check   # 28 checks, 12 of them on failure modes
```

## Part 1. The most expensive finding happened before the first line of code

```
pip install "crewai>=0.60"
ERROR: Could not find a version that satisfies the requirement crewai>=0.60
```

**The precise wording matters here**, because the imprecise one is refuted by a single command.
`pip download crewai` on Python 3.14 happily returns **0.11.2**: old releases declare
`>=3.10,<4.0` and install fine. The `<3.14` (or `<=3.13`) bound starts at **0.14.0**.

And 0.14.0 is also where `crewai.BaseLLM` and `crewai.tools.BaseTool` appear — the seams through
which this stage hands over its own client (ADR-0007). So the choice is: **either a release that
installs and has nothing to plug our client into, or a release with the right API that does not
install.**

That is not a failure of the stage. It is the sharpest of the constraints the stage teaches you
to see: **it settles the choice first**, before elegance is even on the table. And no framework
comparison in a blog post shows it — because every one of them was written on the version where
everything installed.

The side effect turned out to be worse than the incompatibility itself. The `[s09]` extra without
a marker failed **as a whole** and took LangGraph down with it, which installed perfectly. The
instruction **punished obedience**: a reader who did what was written was left with nothing, and
one who did not was left with a working stage.

```toml
crewai>=0.60; python_version < '3.14'
```

One marker. And three distinct states instead of two:

```
package not installed          fixed by installing it
package cannot be installed    fixed only by a different interpreter
credentials missing            fixed by an account
```

## Part 2. What makes the comparison honest

Three implementations of "the same task" are comparable only when the task **is** the same.
Otherwise what gets measured is the author's fluency, not the frameworks.

The problem is not dishonesty, it is invisibility. A CrewAI implementation naturally wants one
more delegation step; a LangGraph one wants a separate validation node. Every deviation looks
like "that's how it is done here", and every one makes somebody else's column incommensurable.

So the contract is **code**, not a list in a README:

```
input             the same question
tools             exactly search_notes, exactly one call
model             the client is supplied from outside, and the counter saw it
stopping          an answer was given, not cut off halfway
shape             the answer rests on the notes that were handed over
```

A violator **stays** in the table — without numbers, naming the element it broke. Dropping it
silently would show three rows as all of them; fixing it would compare a corrected task against
the others.

**The number of model calls is not constrained by the contract.** That is a measured column, not
a violation: bounding it would declare a framework broken for being a framework.

## Part 3. The table

```
| implementation | my lines  | invisible      | calls    | tokens | over request | prose |
| no framework   |        37 |              0 |        2 |    118 |           0 |     0 |
| LangGraph      |        54 |           1895 |        2 |    118 |           0 |     0 |
| CrewAI         |        62 |  NOT EVALUATED |        — |      — |           — |    10 |
| Google ADK     |        43 |  NOT EVALUATED |        — |      — |           — |     1 |
```

Note that **"my lines" and "prose places" are filled in for the rows that never ran.** Both are
measured from source, and an interpreter constraint does not make code unreadable. A dash in
their place would have discarded the only honest numbers that can be stated about CrewAI at all.

Three numbers are worth stopping at.

**37 against 54.** A difference of seventeen lines — and this is not "the framework saves code".
Here it **adds** code: the same three steps are described twice, once as functions and once as a
graph, plus a state type declaration. On a two-step task the scaffolding costs more than the
building.

The number is honest precisely because each implementation has **its own** model call. A shared
helper would make the column asymmetric: the baseline would carry those five lines in its own,
and LangGraph would get them for free — and the error would point towards "the framework is
cheaper".

**0 against 1895.** That is how many lines of the package **executed** on the author's behalf on
this input. Not how many are installed — how many ran, and not counting the one-off import: that
happens once per process, not once per request. This is the missing half of the "less code"
argument: the code did not go away, it moved somewhere you cannot see it, cannot read it during
an incident and cannot fix it.

**0 and 0 in the "over request" column.** This is where the lazy reading of the thesis trips.
"A framework costs more in tokens" is **not a law**. LangGraph decides **order**, not content:
exactly what the author composed reaches the model. It charges in lines, not in tokens.

CrewAI, **by our expectation**, would charge the other way round — but here that is an
expectation, not a measurement: its row in the table is empty. It can be checked on Python 3.12,
and that is exactly what the last exercise is about.

A stage whose thesis is "count it, do not assume it" has no right to make an exception for
itself.

## Part 4. Explicit against implicit coordination — as a number

"Implicit coordination is cheaper" is half the truth, and precisely the half you pay for later.
The other half is measurable:

```
no framework      0 prose places
LangGraph         0 prose places
CrewAI           10 prose places
Google ADK        1 prose place
```

What gets counted are keyword arguments whose values describe **behaviour in prose**: `role`,
`goal`, `backstory`, `description`, `instruction`, `expected_output`. Zero means explicit
coordination — the next step is decided by code. Ten means that answering "why did this step run"
takes reading ten descriptions and imagining how the model read them.

**This is measured from source, not from a run.** So it exists even for a row that cannot be
executed: an interpreter constraint does not make code unreadable. A declared number would be a
flag the author raises by hand — the very defect stage 8 warns about.

## Part 5. Reading the code — seven files

### `contract.py` — what makes the numbers comparable

`44 of 110`. Five elements of the task and the function that checks they are honoured. Among the
elements is the **path**: the set of tools called and the stopping condition. Comparing against a
golden output does not catch that: an implementation that called an extra tool and arrived at the
same text would pass.

### `counters.py` — two measurements an implementation cannot make about itself

`77 of 110`. The counter wraps the client from `shared.llm` and sees the **actual** request,
whatever layer composed it. A counter inside the implementation sees only what that
implementation asked for — which is precisely what misses the overhead.

Executed-line tracing lives here too. And here is where a defect turned up that its own check
caught: the package was located by `origin`, and for a namespace package (`langgraph`) that is
`None`. The invisible-lines column would silently have shown **zero** — a quiet zero in a column
that exists precisely in order not to be zero.

### `compare.py` — a table that parses back

`74 of 110`. `parse()` reads the **written file** and counts again. An equality computed from a
single source is an identity: it holds even when the implementation never reached the file.

### `baseline.py` — no framework at all

`37 of 110`. Having read this file it is hard to miss the main point: **there is nothing here**.
Two model calls, one tool call, state passed explicitly in a variable.

The graph from stage 3 is deliberately not carried over: there it is a supervisor router with a
revision loop, here it is two sequential steps. Bending one to fit the other would compare a task
against a different task.

### `via_langgraph.py` — explicit coordination

`54 of 110`. Every possible order of steps lives in `_wire()`, and nowhere else. That is the main
property of explicit coordination: the question "why this step" has an answer in **one** place.

### `via_crewai.py` — implicit coordination

`62 of 110`. **Written, but never run here** — see part 1. The client is supplied through
`BaseLLM`, a documented extension point; that is the largest part of the file, and it is a
finding too: the lines spent on stopping the library from going to the network its own way are
also a price of the scaffolding, and they honestly land in the "my lines" column.

### `via_adk.py` — a flag that must not stay silent

`43 of 110`. The subtlest decision of the stage is here. "Not evaluated" is right for someone who
never asked for ADK. But for someone who **explicitly turned the flag on**, that same state would
be a lie: they asked for a fourth row, got three, and learned nothing about it.

```
flag off                     not evaluated, its own row in the table
flag on, package missing     a LOUD failure naming what is absent
```

**This implementation does not need Google credentials** — a consequence of that same ADR-0007:
`_model()` steers ADK away from Gemini and onto our client. The first draft demanded them anyway
and punished obedience: a reader who ran the two commands from the docstring got seventeen reds
and advice to open an account their own code does not need.

## Part 6. The choosing rule

There is no composite score and there cannot be one: weights on constraints are an opinion about
whose constraint matters more, baked into a number nobody agreed on.

| If your constraint is | Take | Column |
|---|---|---|
| you need to understand the order of steps during an incident | explicit coordination | prose places |
| the provider's bill hurts | whatever adds zero over the request | over request |
| the code will be read by newcomers | fewer invisible lines | invisible lines |
| the task is two steps with no branching | nothing; the baseline is already shorter | my lines |
| you need parallel branches, checkpoints, streaming | a graph orchestrator | invisible lines |

Every rule names the column it was derived from. A rule you cannot apply outside this table is a
retelling, not a rule — and your task will be exactly outside it.

## Part 7. What to break

Ten mutations in [`exercises.md`](exercises.md). The most expensive ones are not about frameworks
but about the **honesty of the comparison**: the contract stops checking the path, the counter
moves inside an implementation, invisible lines get measured by package size, "prose places" gets
declared as a number instead of measured.

```bash
python scripts/mutate.py s09 --expect
```

**Read the names, not the count.** A mutation caught by an incidental check is worse than one
caught by the check that claims it.

## The limits of this stage — so you do not carry them into production

- **Two implementations out of four were never run.** CrewAI with the required API does not
  install on this Python; ADK is off behind its flag by default. This is the stage's weakest
  point, and it is named by a row in the table rather than hidden.
- **Everything said about CrewAI's behaviour is an expectation.** Neither its token overhead nor
  its compliance with the contract was measured here. The lesson uses the conditional; a present
  tense anywhere is a defect in the prose.
- **Fake-model numbers do not transfer to a real one.** What is proven are **ratios**, not
  absolute values.
- **Invisible lines describe this input.** A different task will execute different ones — that is
  a property of the measurement.
- **Tokens are counted by text length**, not by the provider's tokenizer. Enough for ratios, not
  for a bill.
- **The implementations are minimal.** No retries, no cache, no breakers: added scaffolding would
  make the numbers incommensurable.
- **We teach no framework here.** The stage is about choosing, not about mastery.
- **We do not compare ecosystems.** Integration counts and article counts are not properties of
  code.

## Numbers

| What | How much |
|---|---|
| Implementations / of them run here | 4 / 2 |
| Checks / on failure modes | 28 / 12 |
| My lines: baseline / LangGraph | 37 / 54 |
| Invisible lines: baseline / LangGraph | 0 / 1895 |
| Prose places: LangGraph / CrewAI | 0 / 10 |
| Mutations in the exercises | 10 |

## Next

Stage 10 — the capstone: assemble judgement, not notes. A support agent that **imports** the
mature parts of stages 1–9 and justifies every decision by citing a source stage.
