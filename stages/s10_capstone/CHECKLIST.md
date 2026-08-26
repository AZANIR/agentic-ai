# Checklist — stage 10

Three levels. Passing means closing all three, not the first.

## I understood

- [ ] I can explain the difference between "the stage is imported" and "the stage works" — and name
      what it is measured by.
- [ ] I know why the thesis "the capstone imports the mature parts of stages 1–9" was thrown away.
      Hint: look at the first lines of `stages/s06_platform/app.py`.
- [ ] I can explain why stage 9 moved from "parts" into "deliberately not wired in", even though it
      produced a non-zero number. Hint: run `measure(lambda: None)`.
- [ ] I understand why the price of assembly is **two** numbers, and why both must be in the same
      unit. I can say what the first draft put in the numerator.
- [ ] I can explain why `build_search` gives three written lines and zero executed ones — and why
      that is not an error.
- [ ] I understand why a mismatch goes into an adapter, **never** into a part — and what an edit to
      a part touches besides the part itself.
- [ ] I can name the two forms in which an adapter decides, and say which guard is permitted.
- [ ] I know why `ARCHITECTURE.md` is parsed by code, and why an **unparsed row** is a defect rather
      than silence.
- [ ] I can explain why retrieved text reaches the model behind a data-block fence, and what exactly
      the capstone reopened by bypassing `build_prompt`.
- [ ] I understand why the second deploy cost no adapter at all — and what that says about what
      stages 6 and 10 agree on.
- [ ] I know what this stage does **not** promise: that six scenarios are coverage, and that the
      deploy has been verified.

## I ran

- [ ] `python -m stages.s10_capstone.run` — eight scenes; I read the third more carefully than the
      rest, because it is the one that shows how much of each stage actually works.
- [ ] `python -m stages.s10_capstone.check` — all green; checks: 32, of them on failure modes: 16.
      Two stay `NOT EVALUATED` — and I know why that is a third state rather than a failure.
- [ ] `python scripts/mutate.py s10 --expect` — the numbers in the exercises match the run.
- [ ] `uvicorn stages.s10_capstone.serve:app` — the service came up, and I found the line in
      `serve.py` that shows there is no HTTP layer of its own here.
- [ ] I did exercise 10 and saw that a broken price looks exactly like an intact one.
- [ ] I looked at exercises 3, 4, 10, 11 and 12 — these are holes the mutation sweep found itself.
- [ ] I broke a row in `ARCHITECTURE.md` into three columns and saw exactly what the check says.

## I explained

- [ ] I told a colleague why an import list is not proof of assembly — and what to replace it with.
- [ ] I explained why "less code in the capstone" means nothing without the second number.
- [ ] I showed the "what assembly revealed" section and explained why an empty section would be the
      stage's most suspicious outcome.
- [ ] I said in my own words why the latency number is printed **after** its conditions, not before
      them.
- [ ] I explained why "the instrument was measuring itself" is the same class of defect as
      "imports ≠ uses".
