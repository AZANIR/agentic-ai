# Checklist: what to measure when evaluating an agent

Not "which metrics to collect". Every item here answers a question somebody will ask after the
first "and where did you get the idea that it works?"

## 1. Three levels separately — not one score

**The question:** where did it break, not whether it broke?

A combined score answers "whether", and stops there. Three verdicts answer "where":

```
e2e         about the LAST answer and about nothing else
траєкторія  about the SEQUENCE of steps: order, count, redundant calls
компонент   about ONE step and its own result
```

The rule of attribution has to be **unambiguous**, otherwise the same defect lands in a
different row every time and no level has a history.

A weighted sum of three levels is not a compromise but a hidden decision: any weights are an
opinion about which level matters more, built into a number nobody discussed.

## 2. "Unscored" is a third state, not a grey shade of the second

**The question:** did we check this at all?

"Broken" and "not checked" are different events. A suite that merges them stops distinguishing
a broken system from an interrupted run, and does so **in favour of green**: missing data is
naturally scored as "we saw nothing bad".

Two sides of one rule, and both are needed:

- An empty level is **not passed**. Otherwise the poorer the trace, the better the report.
- A blind measurement is **not a finding**. Otherwise a hundred percent of traffic is marked
  problematic because of something the evaluator cannot see.

And the mirror half: a run in which **everything** ended up in the third state is not a
success. Empty green is not a result, and the report has to say so in words.

## 3. The denominator is every case, not the evaluated ones

**The question:** how much did we weigh when we counted that percentage?

A share counted from the evaluated breaks in two different ways, and neither is visible from
the number itself:

| How the instrument fails | What the number does |
|---|---|
| failures are uniform | **stands still** while coverage collapses |
| failures correlate with what breaks the instrument | **climbs** — the higher, the worse things really are |

The first case gets found when somebody asks how much we evaluated at all. The second never
does: it arrives with good news.

So "unscored" stands in a **column of its own**, and the division is by everything. The
coverage number next to the quality number is not redundancy: the first is what makes the
second readable.

## 4. The kind of evaluator is a field, not an understanding

**The question:** was this compared, or was it judged?

A deterministic evaluator and a model judge have different costs, different reproducibility and
different failure modes. If that is not visible in the report, "the judge only where judgement
is needed" stays a wish rather than a property.

It is verified **by machine**: the judge-call counter reads zero for every deterministic
evaluator, and the total calls per run equal the number of judging evaluators. An understanding
that nobody counts stops being true within six months.

## 5. Judge bias is part of the suite, not a separate initiative

**The question:** and did we calibrate the instrument?

A model judge is a measuring instrument. An instrument nobody has checked gives numbers that
are believed exactly until somebody swaps two columns around.

The minimum a suite has to hold:

- **Position bias** — the same pair twice, in AB and BA order. A tie is a value of its own: the
  transition "A won" → "tie" is a flip too, because the verdict changed with the presentation.
- **Length bias** — a short correct answer and **the same one** plus truthful extra text. There
  is no threshold here and there cannot be: both are correct, so any preference for the longer
  one is a point for length.
- **The mirror half** — the same detector against a judge known to behave steadily. Without it,
  zero findings is indistinguishable from a broken detector.

The detector sits **above** the judge. A judge that checks itself for bias is checking its own
idea of bias.

## 6. Edge cases by observable property, not by label

**The question:** what exactly makes this case an edge one?

An `edge: true` label satisfies any requirement about the share of edge cases **by flipping a
flag**, and a set of twenty happy paths stays green.

Edge has to be readable from what is **visible** in the trace: a refusal step, rejected
arguments, an exhausted limit, an empty result, an unknown tool. Then the requirement about the
share cannot be satisfied by editing metadata.

## 7. Online: cheap checks on everything, the judge on a share — and both numbers named

**The question:** how much traffic did we actually see?

Three properties, each with its reason:

- **Out of band.** No evaluation step stands between the request and the response. The service
  whose latency was measured over a whole stage does not get an unmeasured term added to it.
- **The selection is deterministic.** A random number against a threshold makes the check
  flicker, and the tolerance has to be widened so far that it stops distinguishing ten percent
  from one.
- **The share is reconciled against a number.** A sampler that always says "yes" is
  deterministic too, and it also "matches the declared share". The bill for that mistake comes
  not from the checks but from the provider.

And the price is named directly: **a request that never reached the tracer is not evaluated at
all.** Inline checks would have caught it too — at the cost of latency on every request. That
is a trade-off, not an oversight, and it has to be said out loud.

## 8. The report is read back

**The question:** are these totals and these rows from one source or from two?

An equality computed from one source is an identity: it will always reconcile, including when a
case never made it into the report at all. Parsing the **written file** is the only way to
catch that.

The same principle is broader than the report: agreement between two independent mechanisms
means something, agreement of a mechanism with itself does not.

## What this checklist deliberately leaves out

**Statistical significance.** Twenty cases give no confidence intervals, and pretending
otherwise is worse than not counting them at all. If significance is needed, so is a different
order of volume and a different discipline.

**Drift over time.** It needs **stored history** of results, and that is an evaluation platform
rather than a suite. The numbers drift is computed from do have to be named; comparing windows
is a separate decision with a separate price.

**The quality of the provider's model.** What is evaluated is the **agent** — its decisions and
its path — not who writes the better text. Confusing the two means optimising your choice of
vendor instead of your own system.
