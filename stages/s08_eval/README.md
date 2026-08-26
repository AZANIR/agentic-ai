# Stage 8 — Evaluation: three verdicts instead of one impression

> **Infrastructure tells you whether the system is up. Evaluation tells you whether its
> decisions are good.** Different questions — and a service with flawless uptime can answer
> wrong with complete confidence.

Seven stages built a system. The question "does it work" still has the answer it had
before the first line of code: "I ran it a few times, seemed fine."

## What you will be able to do after this stage

- Name the three levels of evaluation and say what each of them sees that the other two do not.
- Tell an agent that **arrived correctly** from an agent that **arrived by accident** — on
  concrete cases, not in theory.
- See on your own run how swapping two answers around changes the judge's verdict.
- Say why "unscored" is counted separately and why the denominator is every case.
- Name what tracing lacks for evaluation — as a number, not a guess.

## Run this before reading

```bash
python -m stages.s08_eval.run     # eight scenes, no key and no network
python -m stages.s08_eval.check   # 31 checks, 15 of them on failure modes
python scripts/mutate.py s08 --expect
```

## Part 1. Evaluate the path, not just the destination

The stage's headline thesis is from the same source article, and it is not about metrics.

An agent can call every tool correctly, retrieve the right documents, reason sensibly at every
step — and fail the task. Or stumble, call the wrong tool, wriggle out of it and give the
right answer.

**Looking only at the last message, those two cases look identical.** One was a lucky accident,
the other was engineering.

In the stage's set they stand side by side — a straight path, the same answer reached through
recovery, and a lucky accident:

```
прямий шлях                           e2e: пройдено   траєкторія: пройдено
та сама відповідь через відновлення   e2e: пройдено   траєкторія: провалено
щаслива випадковість                  e2e: пройдено   траєкторія: провалено
```

Three identical answers, three different stories. An evaluator for which these rows are the
same does not distinguish engineering from something that merely worked out — and it will not
say what to do when less of it works out.

## Part 2. The most important sentence of the whole stage

> **A model judge is a measuring instrument, and instruments get calibrated.**

An evaluator that declares the judge's verdict to be the truth has made exactly the mistake the
stage warns against: it believed a number without asking where it came from.

So the proof of this stage is **not a table of scores** but a caught bias:

```
position bias: ЗНАЙДЕНО — 3 із 3        (the biased judge)
position bias: згода — 0 із 3           (the steady judge)

length bias: ЗНАЙДЕНО — 2 із 2
   коли буде доставка: 3 -> 5 (+2 за 81 зайвих символів)
   як повернути товар: 4 -> 6 (+2 за 78 зайвих символів)
```

The first three flips are worth nothing without the zeros that follow. **A detector that always
finds bias cannot tell a biased judge from an honest one — and therefore is not a detector.**
The mirror half is not decoration here but the condition under which the first half means
anything at all.

**The fake judge is biased on purpose.** It does not imitate any particular model — it plays
the role of a **broken instrument**, exactly as a mutation plays the role of broken code. What
it does wrong is written in its docstring rather than hidden: the first answer submitted gets a
free point, and every forty characters add a point regardless of content. With a real key the
same detector goes against a real model and gives the same report.

## Part 3. Three levels — and the rule of attribution

There are three levels, and the rule for which defect belongs to which is single and
unambiguous:

```
e2e         about the LAST answer and about nothing else
траєкторія  about the SEQUENCE of steps: order, count, redundant calls
компонент   about ONE step and its own result: refused, rejected, returned empty
```

One case can fail two levels — that is not double counting but two different facts. An agent
that called the wrong tool and got a refusal has **both** a wrong path **and** a broken step;
the reader has to see both.

There is no combined score and there will not be one. A weighted sum would demand weights, and
any weights are a hidden opinion about which level matters more, built into a number nobody
discussed.

On the set's twenty-one cases:

```
рівень        пройд  провал  не оцін  частка
e2e              12       7        2     57%
траєкторія       13       8        0     62%
компонент        13       7        1     62%
```

## Part 4. The third state and the denominator

Two mistakes that make the report **greener**, and that is exactly why they are the most
expensive.

**The first: "unscored" is passed off as "passed".** A trace with no steps of the required kind
does not prove health — it proves there is nothing to look at. A level that scores missing data
as success shows a greener report the poorer the trace is. A run in which tracing fell over
entirely will get a hundred percent.

**The second: the denominator is taken from the evaluated.** The formula looks more honest: "we
count the share of what we managed to evaluate". The consequence is the opposite, and has two
faces:

| How the judge fails | Honest share | Flattering share |
|---|---|---|
| uniformly (quota) | 57 % → 5 % | stays inside a 4 pp band |
| correlated (breaks on messy answers) | 57 % → 24 % | 57 % → **100 %** |

In the first mode the number does not lie — it **goes silent** about coverage collapsing from
twenty-one cases to three. In the second, the cases that drop out are mostly the failing ones,
and the report shows perfect quality through a broken instrument.

The first mistake gets found eventually — when somebody asks how much was evaluated at all.
Nobody ever goes looking for the second: it arrives with good news. So "unscored" stands in a
column of its own, and the division is by everything.

Measure both modes yourself:

```bash
python -m stages.s08_eval.solutions.exercise_2_the_denominator_climbs
```

## Part 5. Reading the code — seven files

### `trajectory.py` — the grouping key is a parameter

`70 of 110`. Two stages group differently, and **both are right**: stage 1 writes one
`trace_run` per scenario, so a trajectory is a trace; the stage 6 service writes one `trace_run`
per process, so a trajectory is a request.

Grouping by `trace_id` would collapse the service's whole file into a single trajectory.
Grouping by `trace_ref` would give nothing at stage 1. Fixing one would declare the other
stage broken.

Step order comes from `seq`, not from the order in the file. While a single appender is
writing, that makes no difference — and that is exactly why the check **deliberately reverses
the lines** of the written trace: a property that cannot be violated on the happy path requires
the check itself to create the conditions in which it is violated.

### `cases.py` — cases are generated, not stored

`36 of 110`. Recorded trace files survive a format change **silently**, and the stage would go
on evaluating a format that no longer exists. Here a case description is run through the same
`shared.trace` as every stage: the trace is real, and a format change breaks generation
loudly, together with all the stages.

**Edge is derived, not declared.** An `edge: true` label would satisfy the "a third are edge"
requirement by flipping a flag, and a set of twenty happy paths would stay green. Here edge is
read from an observable property: the trace contains a step that refused, hit a limit or named
an unknown tool, or there is no answer at all. Nine out of twenty-one.

### `levels.py` — three verdicts, never one

`46 of 110`. Every verdict carries the **kind of evaluator** alongside it: deterministic or
judging. That is not decoration but a requirement, and it is verified by machine — the
judge-call counter reads zero for every deterministic evaluator, and the total calls per run equal
the number of judging evaluators. Nineteen calls for twenty-one cases: for two
traces with no answer the judge is not called at all — nobody pays for missing data.

### `judge.py` — two protocols, not one

`99 of 110`. Pairwise and pointwise measure different things and are needed for different
things:

```
compare(task, first, second) -> the winner    catches position bias
score(task, answer, expected) -> a score      catches length bias
```

The pairwise one has no **score**, the pointwise one has no **order**. One protocol would not
have shown both biases, and that is exactly why there are two.

A judge's unavailability is a **closed list**: no key configured, the provider refused on quota or
rate, the budget is spent, a timeout hit, the answer was unparseable. All of that is
"unscored". Everything else is a failure.

### `bias.py` — the detector sits above the judge, not inside it

`56 of 110`. A judge that checks itself for bias is checking its own idea of bias. The detector
knows nothing about how the judge is built: it presents the same data differently and watches
whether the verdict changed.

The pairs for position are **deliberately balanced**: both answers are equally well-founded and
equal in length, so only the order of presentation can tell them apart. An unbalanced pair
would show a mixture of two biases, and the reader would not know which one they saw.

A tie is a **value of its own**, not the absence of a verdict: the transition "A won" → "tie"
is a flip too, because the verdict changed with the presentation.

### `report.py` — the report is parsed back

`67 of 110`. `parse()` reads the **written file** and counts again. An equality computed from
one source is an identity: it will always reconcile, including when a case never made it into
the report. Two independent sources are the only way to catch that.

### `online.py` — cheap checks on everything, the judge on a share

`61 of 110`. No evaluation step stands between the request and the response: everything is read
from the trace **afterwards**. The service whose latency stage 7 spent a whole stage
measuring does not get an unmeasured term added to it.

The price is named directly: **a request that never reached the tracer is not evaluated at
all.** Inline checks would have caught it too — at the cost of latency on every request.

The selection is deterministic, by a hash of the identifier:

```
семпл на 1000 запитах: 106 до судді = 10.6%
заявлено 10%, межа ±3%, мінімальний потік 200
```

A random number against a threshold would make the check flicker, and the tolerance would have
to be widened so far that it would stop distinguishing ten percent from one.

## Part 6. What the traces lack — measured, not assumed

Stage 6 deferred the decision here twice: "stage 8 will say what it actually lacks". Here is
the answer.

**Three different fields** serve as the run key — `scenario`, `scene`, `trace_ref` — and
**four** stages mark the run with nothing at all: 2, 3, 4 and 7. Stage 4 has a `phase`, but
that is the phase of a **failure**: on the happy path it is `None`, so it cannot be a key.

The first edition of this paragraph named four fields and two stages — wrong twice, counting `phase` as a key and forgetting stage 7. So the list is now **computed** from the
sources by parsing the tracer calls, and a check reconciles it with the prose: a number about
what measurement lacks must not itself be a guess.

On the service's trace the evaluator is blind on two measurements: no answers are recorded, so an
empty answer cannot be caught; no terminal step for the request, so an unfinished run cannot
be caught.

The key thing is that a blind measurement **does not turn into a finding**. Otherwise
every service trajectory would get "the run did not finish", and a hundred percent of traffic
would be marked problematic because of something the evaluator cannot see. This is the same
mistake as "empty counted as passed", only mirrored: there, missing data was read as success;
here, as failure. Both times the right answer is the third one.

**The requirement for the trace store** is formulated here, and it turned out smaller than
the guess: read everything in one pass, group by a key on the reader's side, append
without rewriting, recover order from `seq`, be readable with `cat`. JSONL gives all five; an
external sink adds none. A promise that travelled through three stages is closed with an answer
rather than a fourth deferral.

## Part 7. What to break

Fourteen mutations in [`exercises.md`](exercises.md). The most expensive ones are not about
evaluation but about the **honesty of the report**: an empty level becomes passed, the
denominator is taken from the evaluated, an instrument failure is billed to the agent, a blind
measurement becomes a finding. All of them leave the harness working and make the report look
nicer.

```bash
python scripts/mutate.py s08 --expect
```

**Read the names, not the count.** A mutation caught by an incidental check is worse than one
caught by the check that asserts about it.

## The limits of this stage — so you do not carry them into production

- **Twenty-one cases are not statistics.** There are no confidence intervals here, and
  pretending otherwise is worse than not counting them at all.
- **A fake judge does not prove that real judges are biased.** That is shown in the literature.
  It gives the detector something to detect.
- **Sampling is verified locally**, in the same process. A real deployment is `NOT EVALUATED`.
- **±3 percentage points is the exercise's bound** on a stream from two hundred. The real one
  depends on traffic volume and the price of a judgement.
- **With a real judge determinism is not guaranteed** — the flicker check with a key becomes
  `NOT EVALUATED` rather than green.
- **There is no drift over time.** It needs stored history, which this stage deliberately does
  not keep. The stage prints the numbers drift is computed from; comparing windows is stage 10.

## The numbers

| What | How many |
|---|---|
| Cases in the set / edge among them | 21 / 9 |
| Checks / on failure modes | 31 / 15 |
| Mutations in the exercises | 14 |
| Judge calls per run | 19 |

## Next

Stage 9 — frameworks: the same thing but in somebody else's code, and with the question of what
exactly you hand over along with control.
