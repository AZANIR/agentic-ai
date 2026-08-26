# Checklist — stage 8

Three levels. Passing means closing all three, not the first.

## I understood

- [ ] I can name the three levels of evaluation and say what each of them sees that the other
      two do not.
- [ ] I can state the rule for attributing a defect to a level in one sentence — and say what
      breaks when it is ambiguous.
- [ ] I understand why there is no combined score. Hint: what exactly you would have to choose
      in order to compute one.
- [ ] I can explain why "unscored" is a state of its own rather than a grey shade of "failed".
- [ ] I can name **two** different ways in which a share counted from the evaluated breaks —
      and say which of them nobody ever finds.
- [ ] I understand why the bias detector sits **above** the judge rather than inside it.
- [ ] I can explain why length bias has no threshold **and cannot have one**. Hint: how the
      second answer of the pair differs from the first.
- [ ] I know what this stage does **not** promise: that twenty-one cases give you statistics.

## I ran

- [ ] `python -m stages.s08_eval.run` — eight scenes; I read the sixth one carefully, it is
      about why the fourth and the fifth are worth anything.
- [ ] `python -m stages.s08_eval.check` — all green; 31 checks, 15 of them on failure modes.
- [ ] `python scripts/mutate.py s08 --expect` — the numbers in the exercises match the run.
- [ ] I did exercise 2 and ran the solution. I saw that under correlated failures the
      flattering share reaches **100 %** with an honest 24 % and five evaluated cases out of
      twenty-one.
- [ ] I did exercise 6 and asked myself whether I would tell zero findings from a broken
      detector with nothing but the report in my hands.
- [ ] I looked at exercise 9 and understood why the check **itself** reverses the lines of the
      trace.

## I explained

Not to myself — out loud, to another person or in writing.

- [ ] **Why are an agent that arrived correctly and an agent that arrived by accident not the
      same thing, if the answer is identical?**
- [ ] **Why is a "green report" on a poor trace worse than a red one?**
      Hint: which way the mistake pulls and who will go looking for it.
- [ ] **Why is the judge's verdict not the truth?** And what exactly has to be shown so that
      this is not rhetoric.
- [ ] **Why does zero bias findings prove nothing without the mirror run?**
- [ ] **Why is a deterministic sampler not yet a correct sampler?**
      Hint: which check will not catch it and who ends up sending the bill.
- [ ] **Why parse the written report back if the same program has just generated it?**
      Hint: how an identity differs from an equality of two sources.

## I am ready to move on

- [ ] I can name the stage's six limits — and none of them is a surprise.
- [ ] I can say what tracing lacks for evaluation as a **number**: how many different fields
      mark a run and how many stages mark it with nothing at all. And why stage 4's `phase`
      does not belong on that list.
- [ ] I understand why it was this stage rather than stage 6 that formulated the requirement
      for the trace store — and why the answer turned out to be "we change nothing".
- [ ] I understand why evaluation does not stand in the hot path and what exactly was paid for
      that.
