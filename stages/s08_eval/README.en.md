# Stage 8 — Evaluation: three verdicts instead of one impression

The lesson itself is in Ukrainian ([`README.md`](README.md)). This page is the map.

## What it is

Seven stages built a system. The question "does it work" still has the same answer it had
before the first line of code: *I ran it a few times, seemed fine.*

> **Infrastructure tells you whether the system is up. Evaluation tells you whether its
> decisions are good.** Different questions — and a service with flawless uptime can answer
> wrong with complete confidence.

Two theses drive the stage. The first is from the source article:

> **Evaluate the path, not just the destination.**

An agent can call every tool correctly and still fail the task; or stumble, call the wrong
tool, recover, and answer correctly. **Looking only at the last message, those two are
identical.** One was engineering, the other was luck.

The second thesis is not in the article and is specific to this repository:

> **A model judge is a measuring instrument, and instruments get calibrated.**

So the proof of this stage is not a table of scores. It is a **caught bias**.

## Run it

```bash
python -m stages.s08_eval.run     # eight scenes, no key, no network
python -m stages.s08_eval.check   # 31 checks, 15 of them on failure modes
python scripts/mutate.py s08 --expect
```

## The proof

```
position bias: FOUND — 3 of 3        (biased judge)
position bias: agreement — 0 of 3    (steady judge)

length bias: FOUND — 2 of 2
   3 -> 5 (+2 for 81 redundant characters)
   4 -> 6 (+2 for 78 redundant characters)
```

The three flips are worth nothing without the zeros that follow. **A detector that always
finds bias cannot tell a biased judge from an honest one** — the mirror half is the condition
under which the first half means anything at all.

The default judge is a fake, biased **on purpose**. It does not imitate any real model; it
plays the role of a broken instrument, exactly the way a mutation plays the role of broken
code. What it does wrong is written in its docstring, not hidden: the first answer submitted
gets a free point, and every forty characters add one regardless of content.

## The modules, in reading order

| File | What it holds | Lines |
|---|---|---|
| `trajectory.py` | steps into trajectories; the grouping key is a **parameter** | 70 |
| `cases.py` | 21 cases generated through the real tracer, 9 edge by observation | 36 |
| `levels.py` | three independent verdicts, each carrying its evaluator kind | 46 |
| `judge.py` | two protocols — pairwise and pointwise; the closed list of "unavailable" | 99 |
| `bias.py` | detectors that sit **above** the judge, never inside it | 56 |
| `report.py` | three shares, a third state, and a parser that reads the written file back | 67 |
| `online.py` | cheap checks on everything, the judge on a deterministic share | 61 |

Budget: 110 executable lines per implementation module.

## Two mistakes that make the report greener

Both are in the stage because both are the kind nobody looks for — they arrive as good news.

**An empty level counted as passed.** A trace with no steps of the required kind does not
prove health; it proves there is nothing to look at. A level that scores missing data as
success gets greener the poorer the trace is. Lose tracing entirely and it reports 100 %.

**A denominator taken from the evaluated cases.** The formula looks *more* honest — "count the
share of what we managed to evaluate". It behaves in two ways, both bad:

| How the judge fails | Honest share | Flattering share |
|---|---|---|
| uniformly (quota exhausted) | 57 % → 5 % | stays inside a 4 pp band |
| correlated (breaks on messy answers) | 57 % → 24 % | 57 % → **100 %** |

Under uniform failure the number does not lie — it goes **silent** about coverage collapsing
from 21 cases to 3. Under correlated failure the failing cases are the ones that drop out, and
a broken instrument reports perfect quality.

The first one gets found eventually, when somebody asks how many cases were actually scored.
The second never does. Measure both yourself:

```bash
python -m stages.s08_eval.solutions.exercise_2_the_denominator_climbs
```

## The grouping key is a parameter, and both stages are right

Stage 1 writes one `trace_run` per scenario, so a trajectory is a trace. The stage 6 service
writes one `trace_run` per process, so a trajectory is a request. Grouping by trace id would
collapse the whole service file into a single trajectory — and it would still "work": totals
compute, the report prints, no error. Fixing either key would declare the other stage broken.

Step order comes from the sequence number, not from file order. While a single appender is
writing, that is indistinguishable — which is why the check **deliberately reverses the lines**
of the written trace. A property that cannot be violated on the happy path requires the check
to create the conditions under which it is violated.

## What the traces lack — measured, not assumed

Stage 6 deferred this question here twice. The answer is **computed from the sources**, not
written in prose: **three fields** name the run (`scenario`, `scene`, `trace_ref`) and **four**
stages name it with nothing at all — 2, 3, 4 and 7. Stage 4 has a `phase`, but that is the
*failure* phase: on the happy path it is `None`, so it cannot key a run.

The first edition of this paragraph said four fields and two stages, and was wrong on both
counts. A number describing what measurement lacks must not itself be a guess, so the survey
now parses the tracer calls and a check reconciles it with the prose. On a service trace the evaluator is blind on two measurements — no answers recorded, so
an empty answer cannot be caught; no terminal request step, so an unfinished run cannot be
caught.

Crucially, a blind measurement does **not** become a finding. Otherwise every service
trajectory would be flagged "run did not finish", and 100 % of traffic would be marked
problematic over something the evaluator cannot see. Same mistake as counting empty as passed,
mirrored: there, missing data was read as success; here, as failure. Both times the right
answer is the third state.

The **trace store requirement** is settled here too, and it turned out smaller than the guess:
read everything in one pass, group by a key on the reader's side, append without rewriting,
recover order from the sequence number, read it with `cat`. JSONL satisfies all five; an
external sink adds none.

## What this stage does not prove

- **21 cases are not statistics.** No confidence intervals, and pretending otherwise is worse
  than not counting at all.
- **The fake judge does not prove real judges are biased.** The literature does that; this one
  gives the detector something to detect.
- **Sampling is verified locally**, in the same process. A real deployment stays not-verified.
- **±3 percentage points is an exercise bound** on a stream from two hundred. The real one
  depends on traffic volume and the price of a judgement.
- **With a real judge, determinism is not required** — the flicker check becomes not-verified
  with a key, rather than green.
- **No drift over time.** Drift needs stored history, which this stage deliberately does not
  keep. It prints the numbers drift is computed from and stops there; comparing windows is
  stage 10.

## Where to break it

Fourteen mutations. The ones worth your time are not about evaluation but about the **honesty of
the report**: an empty level becomes passed, the denominator moves to the evaluated, an
instrument failure gets billed to the agent, a blind measurement turns into a finding. All of
them leave the harness working and the report looking better.

Walkthrough in [`exercises.md`](exercises.md), written in Ukrainian.
