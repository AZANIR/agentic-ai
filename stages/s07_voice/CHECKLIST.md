# Checklist — stage 7

Three levels. Passing means closing all three, not the first.

## I understood

- [ ] I can explain why the measurement is time to the **first sound** rather than total
      duration.
- [ ] I can name the **two** parts of streaming's gain and say which of them does not reduce
      total time. Hint: only one of them scales with utterance length.
- [ ] I understand why p95 is shown next to the mean rather than instead of it.
- [ ] I can say why p95 is taken by nearest rank rather than by interpolation — and why
      `ceil` rather than `round`. Hint: on how many sample sizes they differ.
- [ ] I can explain why "sum of steps = total time" has a third term in streaming and why
      that term has to be zero.
- [ ] I can name the **two** conditions of barge-in and what breaks when only one is kept.
- [ ] I understand why the fake clock matters more than the fake models.
- [ ] I know what this stage does **not** promise: that my machine will get these numbers too.

## I ran

- [ ] `python -m stages.s07_voice.run` — seven scenes; I read the third one carefully.
- [ ] `python -m stages.s07_voice.check` — all green; 44 checks, 37 of them on failure modes.
- [ ] `python scripts/mutate.py s07 --expect` — the numbers in the exercises match the run.
- [ ] I did exercise 4 and saw the ratio fall from 3.5x to 1.7x — that is, most of the gain
      does not come from the chunks. In the check's message that number has two decimals:
      1.69.
- [ ] I did exercise 1 and understood why the fake clock must not sleep.
- [ ] I moved the barge-in thresholds around and found a pair where "uh-huh" does not
      interrupt but "stop" does.

## I explained

Not to myself — out loud, to another person or in writing.

- [ ] **Why is a number after worth nothing without a number before?**
- [ ] **Why is "streaming is faster" not a result?**
      Hint: what exactly got faster and what stayed the same.
- [ ] **Why is a timing check with a real clock worse than no check at all?**
      Hint: what happens after the third flicker.
- [ ] **Why is a detector that goes by level alone broken, even though it "works"?**
- [ ] **When is prefetch not worth turning on?**
      Hint: what share of requests do not need the tool.
- [ ] **Why reconcile the breakdown against the trace if the same program computes both?**
      Hint: what it means when two independent mechanisms agree.

## I am ready to move on

- [ ] I can name the stage's seven limits — and none of them is a surprise.
- [ ] I understand why live mode is written but marked `NOT EVALUATED`, and what exactly it
      would take to remove that mark.
- [ ] I understand why voice is **not** stitched into stage 6's service and when doing so
      makes sense.
