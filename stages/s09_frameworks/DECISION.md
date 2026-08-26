# Checklist: how to choose an agent framework

Not "which one is better". Every item here answers a question somebody will ask six months from
now — when changing the decision is already expensive.

## 1. Does it install on your interpreter

**The question:** is there a release that supports the Python you work on?

This is the cheapest check and the sharpest constraint, and it settles the choice **first**. No
comparison in a blog post shows it: every one of them was written on the version where everything
installed.

Check it **before** you write a line of code. A framework chosen for its elegance and discarded
over `Requires-Python` costs exactly as much as you managed to write.

Separately: **mark the dependency, do not hope**. An extra without a marker fails as a whole and
takes down with it whatever would have installed perfectly — that is, it punishes the reader for
obedience.

## 2. How much code works on your behalf — and how much of it will you read during an incident

**The question:** where does the code you did not write live, and will you be able to open it at
three in the morning?

"Less code" is half the argument. The other half: the code did not go away, it moved somewhere
you cannot see it, cannot read it and cannot fix it.

Measure what **executed**, not what is installed. Package size is impressive and means nothing:
it carries support for dozens of integrations, none of which will run on your task.

## 3. Which currency the framework charges in

**The question:** does it add lines or tokens?

These are different currencies, and different people pay them at different times.

```
an order orchestrator     charges in lines, adds zero tokens     MEASURED
a role framework          probably the other way round           NOT MEASURED
```

The first line is stage 9's measurement. The second is an expectation, and it is deliberately
marked: a stage that teaches counting has no right to slip a guess into the same table.

"A framework costs more in tokens" is **not a law** but a property of a particular framework.
Count it, do not assume: the difference in the provider's bill shows up on production traffic,
not on a demo.

And count it **at the provider boundary**. A counter inside your own code sees only what you
asked for — which is precisely what misses the overhead.

## 4. Will you be able to answer "why did this step run"

**The question:** how many places must be read to learn the reason?

Explicit coordination: the next step is decided by code, and the answer is in one place. Implicit:
the next step is decided by text the model read, and the answer has to be **reconstructed** from
descriptions.

Both trade-offs are legitimate. But the second becomes expensive exactly when you need it — during
an incident, when the job is not to understand the system but to name the cause quickly.

This is measurable: count the places where behaviour is described in prose.

## 5. Does it let you reach the provider's client

**The question:** can you hand the framework your own client?

If not, you will not be able to count tokens, run offline, substitute the provider, or check
anything without network and a key.

Frameworks are fond of their own clients, and the shortest path is to let them have their way. The
lines spent on not letting them are also a price of the scaffolding, and they have to land in the
count honestly.

## 6. What happens with the next minor release

**The question:** which call breaks first?

A floor pin (`>=0.2`) will hand whoever installs the stage a year from now an entirely different
package. A pin at the minor boundary narrows the window but does not close it: an API break is
caught by a **smoke test**, not by a version.

The smoke test has to **execute** the implementation, not import it. An import survives the
disappearance of an entry point; a call does not.

## 7. Is it needed here at all

**The question:** what does the "no framework" row in the same table show?

Without a baseline, the comparison answers "which of them" rather than the question you are
actually asking.

On a task of two sequential steps the scaffolding may cost more than the building — and the only
way to find that out is to put both numbers side by side.

## What this checklist deliberately leaves out

**Ecosystem size.** Integration counts, stars and articles are not properties of code, and none of
them will help at three in the morning.

**Speed.** Latency here is set by the model, not by the scaffolding. Measuring it on a fake means
measuring your own fake.

**A composite score.** Weights on constraints are an opinion about whose constraint matters more.
Only you know your constraint, and that is exactly why the conclusion has the shape
"constraint → tool".
