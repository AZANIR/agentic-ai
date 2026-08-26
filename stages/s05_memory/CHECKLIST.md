# Checklist — stage 5

Three levels. Passing means closing all three, not the first.

## I understood

- [ ] I can explain why the model remembers nothing, and what memory actually is then.
- [ ] I tell short-term and long-term memory apart and can name the job of each.
- [ ] I can name the **four conditions** under which a fact reaches the context.
- [ ] I understand why the owner filter runs **before** the top-k selection and not after — and
      what exactly breaks the other way round. Hint: it is not a leak.
- [ ] I can explain the trap of compressing the summary twice and why it cannot be seen by eye.
- [ ] I understand why retrieval from memory is **the same** problem as search on stage 2.
- [ ] I can say why a contradiction is decided by topic, and what that choice costs.
- [ ] I know what this stage does **not** promise: that a stored fact is true.

## I ran it

- [ ] `python -m stages.s05_memory.run` — all six scenes; read scene 3 carefully.
- [ ] `python -m stages.s05_memory.run --prompt` — saw how facts enter the prompt as a separate
      marked block rather than being woven into the instructions.
- [ ] `python -m stages.s05_memory.check` — all green; 42 checks, 27 of them on failure modes.
- [ ] `python scripts/mutate.py s05 --expect` — the numbers in the exercises match the run.
- [ ] Did exercise 2 (the filter after the selection) and saw that **one** check went red — and
      that without it the suite would stay green on code that quietly loses answers.
- [ ] Did exercise 3 (the summary rewritten) and tried to spot the defect by eye in the output.

## I explained

Not to myself — out loud, to another person or in writing.

- [ ] **Why does "store everything" make the agent worse when no error appears at all?**
      Hint: the limit is on tokens, not on nonsense.
- [ ] **Why does the check "somebody else's fact did not arrive" prove nothing on its own?**
      Hint: on an empty result it is green.
- [ ] **Why is time passed as a parameter rather than read from the clock inside?**
      Hint: a TTL check that passes at night and fails during the day.
- [ ] **Why does the old fact stay in the file after being replaced?**
      Hint: "so what was it before" is asked more often than you would think.
- [ ] **Why is the order in the "what to remember" checklist worth more than the rules?**
      Hint: "remember my password".

## I am ready for what comes next

- [ ] I can name what of this stage survives the move to a real store and what does not.
- [ ] I can explain why the `Memory` interface here is deliberately narrow.
- [ ] I know the five limits of the stage named in the lesson — and none of them is a surprise.
