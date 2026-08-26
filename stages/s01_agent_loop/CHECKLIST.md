# Checklist — stage 1

Three levels. Passing means closing all three, not the first one.

## I understood

- [ ] I can explain why a language model **does not execute** functions itself, and what it does
      instead.
- [ ] I can draw the ReAct loop on a napkin without looking.
- [ ] I can name the three parts of an agent and say which one this stage is missing.
- [ ] I know why `function.arguments` arrives as a string rather than a dictionary, and what
      follows from that.
- [ ] I understand why a tool's result **must** go back to the model.

## I ran it

- [ ] `python -m stages.s01_agent_loop.run` — saw all four scenarios.
- [ ] `python -m stages.s01_agent_loop.check` — 30 green checks.
- [ ] Broke the confirmation gate (exercise 1) and saw three `AssertionError`s, each with its
      own reason — rather than one incomprehensible internal error.
- [ ] Squeezed `AGENT_MAX_STEPS` (exercise 3) and watched the answer disappear.
- [ ] Looked into `traces/` and found my own steps there.
- [ ] *(optional)* Connected a real provider and worked through the manual checklist in the
      lesson.

## I explained

Not to yourself — out loud, to another person, or in writing. If you cannot put it into words,
you did not understand it.

- [ ] **Why is the step limit a guard rather than a performance setting?**
      A hint if you are stuck: what happens to the bill if you remove it.
- [ ] **Why does a validation failure go back to the model instead of raising an exception?**
      Hint: compare what the model sees in each of the two cases.
- [ ] **Where exactly does the trust boundary of an autonomous system run, and why there?**
      Hint: look at where in the loop each of the three guards sits.
- [ ] **Why does the gate screen the whole step rather than each call separately?**
      Hint: imagine a model response containing two irreversible actions.

---

Closed all three? [Stage 2 — RAG](../s02_rag/).

If some item under "I explained" will not come out, go back to the matching section of the
lesson. That is not shameful, it is the normal way to read a technical text.
