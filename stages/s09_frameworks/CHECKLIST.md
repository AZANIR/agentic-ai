# Checklist — stage 9

Three levels. Passing means closing all three, not the first.

## I understood

- [ ] I can say **where exactly** coordination lives in each of the four implementations.
- [ ] I understand why the task contract is code rather than a list in a README. Hint: which
      deviation is impossible to notice by reading the code.
- [ ] I can explain why the number of model calls is **not** constrained by the contract.
- [ ] I understand why "less code" without the second number is an argument missing its other
      half.
- [ ] I can say why invisible lines are measured by **execution** rather than by package size.
- [ ] I understand why the token counter sits at the provider boundary rather than inside an
      implementation.
- [ ] I can explain why there is no composite score in the table — and what it would take for one
      to appear.
- [ ] I know what this stage does **not** promise: that these numbers carry over to another task.

## I ran

- [ ] `python -m stages.s09_frameworks.run` — six scenes; I read the fourth and the fifth
      together, because separately each confirms the usual claim and together they refute it.
- [ ] `python -m stages.s09_frameworks.check` — all green; checks: 28, of them on failure modes:
      12.
- [ ] `python scripts/mutate.py s09 --expect` — the numbers in the exercises match the run.
- [ ] I did exercise 3 and ran the solution. I saw that two of the three observer positions
      undercounted **100 %** of the overhead — and both in the direction of "the framework is
      cheaper".
- [ ] I did exercise 4 and understood why a namespace package produced a quiet zero.
- [ ] I looked at exercises 5, 8 and 9 — these are holes the mutation sweep found by itself.

## I explained

Not to myself — out loud, to another person or in writing.

- [ ] **Why does a framework comparison in a blog post almost always measure the author rather
      than the frameworks?**
- [ ] **Why does LangGraph add zero tokens, and why does that not make it cheaper?**
      Hint: which currency it charges in.
- [ ] **What does "implicit coordination costs understanding" mean — as a number?**
- [ ] **Why does an implementation that broke the contract stay in the table instead of
      disappearing from it?**
- [ ] **Why are "not evaluated" for CrewAI and "not evaluated" for ADK different events?**
      Hint: what exactly the reader has to do in each case.
- [ ] **Why parse the written table back, when the same program has just generated it?**

## I am ready to move on

- [ ] I can name seven limits of the stage — and none of them is a surprise.
- [ ] I can apply the "constraint → tool" rule to a task that is not in the table, and name the
      column I took the conclusion from.
- [ ] I understand why the interpreter constraint settles the choice **first** — and why no blog
      post writes about it.
- [ ] I can say what exactly I would do if the framework I needed did not install on my Python.
