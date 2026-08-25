# Stage 9 — Frameworks: your own numbers instead of someone's claim

The lesson itself is in Ukrainian ([`README.md`](README.md)). This page is the map.

## What it is

Eight stages built the system by hand. The question most people start with was never asked:
**which framework?** That ordering is the point — it can only be answered against something to
compare with.

> **A framework is scaffolding, not architecture.** Chosen before the shape of the building is
> known, it *becomes* the shape.

The second thesis is operational, and it turns into columns:

> **Explicit coordination costs lines. Implicit coordination costs understanding.**

## Run it

```bash
python -m stages.s09_frameworks.run     # six scenes, no key, no network
python -m stages.s09_frameworks.check   # 28 checks, 12 of them on failure modes
python scripts/mutate.py s09 --expect
```

## The most useful finding happened before the first line of code

```
pip install "crewai>=0.60"
ERROR: Could not find a version that satisfies the requirement crewai>=0.60
```

**The precise wording matters here**, because the imprecise one is refuted by a single command:
`pip download crewai` on Python 3.14 happily returns **0.11.2** — old releases declare
`>=3.10,<4.0` and install fine. The `<3.14` (or `<=3.13`) bound starts at **0.14.0**.

And 0.14.0 is also where `crewai.BaseLLM` and `crewai.tools.BaseTool` appear — the seams
through which this stage hands over its own client. So the choice is: **either a release that
installs and has nothing to plug our client into, or a release with the right API that does not
install.**

That is not a gap in the stage. It is the sharpest constraint the stage teaches: it settles the
choice **first**, before elegance is even on the table. No blog comparison shows it, because
every one of them was written on the version where everything installed.

The side effect was worse than the incompatibility. Without a marker the `[s09]` extra failed
**as a whole** and took LangGraph down with it — an instruction that punishes obedience. One
marker fixes it, and the availability protocol now carries three states, not two:

```
package not installed        fixed by installing
package cannot be installed  fixed only by a different interpreter
credentials missing          fixed by an account
```

## The table

```
| implementation | my lines | invisible | calls | tokens | over request | prose |
| no framework   |       37 |         0 |     2 |    118 |            0 |     0 |
| LangGraph      |       54 |      1895 |     2 |    118 |            0 |     0 |
| CrewAI         |       62 |   not verified                     |          10 |
| Google ADK     |       43 |   not verified                     |           1 |
```

Note that **my lines and prose places are filled in for the rows that never ran**: both are
measured from source, and an interpreter constraint does not make code unreadable. A dash there
would have discarded the only honest numbers CrewAI can offer.

**37 against 54.** The framework does not save code here — it *adds* seventeen lines. The same
three steps are described twice, once as functions and once as a graph, plus a state type. On a
two-step task the scaffolding costs more than the building.

**0 against 1895.** Lines of the package that actually *executed* on this input — not lines
installed, and not counting the one-off import: that happens once per process, not once per
request. This is the missing half of "fewer lines": the code did not disappear, it moved
somewhere you cannot read during an incident and cannot fix.

**0 and 0 in the overhead column.** This is where the lazy reading of the thesis trips.
"Frameworks cost tokens" is **not a law**. LangGraph decides *order*, not content: exactly what
the author composed reaches the model. It charges in lines, not tokens.

CrewAI would, **we expect**, charge the other way — but that is an expectation, not a
measurement: its row is empty. A stage whose thesis is "count it, do not assume it" does not get
an exemption for itself.

## "Why did this step run" is a measured number

```
no framework    0 prose places
LangGraph       0 prose places
CrewAI         10 prose places
Google ADK      1 prose place
```

Counted from the source: keyword arguments whose values describe behaviour in prose — `role`,
`goal`, `backstory`, `description`, `instruction`, `expected_output`. Zero means the next step
is decided by code. Ten means answering "why did this step run" requires reading ten
descriptions and imagining how the model read them.

Because it is measured from **source**, the number exists even for a row that cannot be
executed: an interpreter constraint does not make code unreadable.

## The modules, in reading order

| File | What it holds | Lines |
|---|---|---|
| `contract.py` | five task elements and the function that checks them — the path included | 44 |
| `counters.py` | tokens at the provider boundary; executed-line tracing | 77 |
| `compare.py` | the table: builds, renders, and parses back | 74 |
| `baseline.py` | no framework: two model calls and a local variable | 37 |
| `via_langgraph.py` | explicit coordination — the whole order lives in one function | 54 |
| `via_crewai.py` | implicit coordination — written, never run here | 62 |
| `via_adk.py` | behind a flag; an enabled flag must not stay silent | 43 |

Budget: 110 executable lines per implementation module.

## What makes the comparison honest

Three implementations of "the same task" are comparable only if the task is the same. Otherwise
what gets measured is the author's fluency. The drift is not dishonest, it is **invisible**:
each deviation looks like "that's how it's done in this framework", and each one makes another
column incommensurable.

So the contract is code, not a checklist, and it checks the **path** — which tools were called
and why the run stopped. A violator keeps its row *without numbers*, naming the element it
broke. Dropping it silently would show three rows as all of them; fixing it would compare a
corrected task against the others.

The number of model calls is deliberately **not** constrained: that is a measured column, not a
violation. Bounding it would declare a framework broken for being a framework.

## What this stage does not prove

- **Two of four implementations were never run here.** CrewAI with the required API does not
  install on this interpreter; ADK is off behind its flag. This is the stage's weakest point,
  and it is a row in the table rather than a footnote.
- **Everything said about CrewAI's behaviour is an expectation.** Neither its token overhead nor
  its contract compliance was measured here. The prose uses the conditional; a present tense
  anywhere is a defect in the prose.
- **Fake-model numbers do not transfer to a real one.** Ratios are proven; absolute values are
  not.
- **Invisible lines describe this input.** A different task executes different lines.
- **Tokens are counted by text length**, not by the provider's tokenizer.
- **The implementations are minimal.** No retries, no cache, no breakers — added scaffolding
  would make the numbers incommensurable.
- **No framework is taught here.** The stage is about choosing, not about mastery.
- **Ecosystems are not compared.** Integration counts and blog posts are not properties of code.

## Where to break it

Ten mutations. The ones worth your time are not about frameworks but about the **honesty of the
comparison**: the contract stops looking at the path, the counter moves inside an
implementation, invisible lines get measured by installed size, prose places get declared
instead of measured.

Three of the exercises are holes the mutation sweep found itself — two in the checks, one in the
first draft of an exercise that broke nothing at all.

Walkthrough in [`exercises.md`](exercises.md), written in Ukrainian.
