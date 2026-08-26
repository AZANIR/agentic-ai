# Checklist — stage 3

Three levels. Passing means closing all three, not the first one.

## I understood

- [ ] I can explain why one agent with twenty tools chooses worse than one with five, and why
      rewriting the prompt does not cure it.
- [ ] I can say in one sentence what a supervisor is, without using the word "orchestration".
- [ ] I understand why the state schema is the most expensive decision in the graph to change.
- [ ] I can name two events the graph reacts to in **opposite** ways, and explain why.
- [ ] I understand why the access level sits in the state rather than being passed as an
      argument.
- [ ] I can say when a supervisor is **not** needed, and name the checklist's third verdict.
- [ ] I know what this stage does **not** prove: that the route will be right on a real model.

## I ran it

- [ ] `python -m stages.s03_router.run` — saw all five scenes.
- [ ] `python -m stages.s03_router.run --prompt` — read what the model sees.
- [ ] `python -m stages.s03_router.check` — all green; 38 checks, 20 of them on failure modes.
- [ ] `python -m stages.s03_router.decision` — seven situations and an answer to each.
- [ ] Removed the revision limit (exercise 2) and saw the second implementation go red as well.
- [ ] `python scripts/mutate.py s03 --expect` — the numbers in the exercises match the run.
- [ ] `pip install -e ".[s03]"` — and saw the line "AC-06 перевірено: 7 маршрутів збіглися".
- [ ] Put `graph.py` and `langgraph_impl.py` side by side and found parts of the first inside the
      second.

## I explained

Not to yourself — out loud, to another person, or in writing.

- [ ] **Why does the graph not take the model at its word about a node name?**
      Hint: what happens when the model says `weather`.
- [ ] **Why does a specialist's exception not bring the run down, while reading an unknown field
      does?**
      Hint: one of the two means the world broke, the other that the contract did.
- [ ] **Why is a handoff a dangerous place for access rights?**
      Hint: what exactly the specialist receives, and what it does **not** receive.
- [ ] **Why is a revision loop with no counter not merely "a bit slower"?**
      Hint: multiply the number of rounds by the price of a model call.
- [ ] **When is one agent better, and when a classifier?**
      Hint: the middle row of [`DECISION.md`](DECISION.md).

---

## Manual checklist: a real model

The checks run on a fake, and the route in them is right **by construction**. The most
interesting part of this stage starts here.

```bash
# .env:  LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
python -m stages.s03_router.run
```

- [ ] Does the banner say a real model is running?
- [ ] **How many of the six requests went where they went on the fake?** Write the number down.
      This is the first real routing-quality metric in the course, and it is almost certainly not
      6 out of 6.
- [ ] The request that went elsewhere — why? Look at the competence descriptions in
      `specialists.py` and try to work out which of them the model read differently from how you
      wrote it.
- [ ] **Rewrite one competence description** so that it differs more sharply from its neighbour.
      Run it again. Did it change? That is exactly the work stage 8 starts measuring.
- [ ] Ask a question on the boundary between two competences — "how many days do I have to return
      order ord_4471", say. Where did it go? Both answers are defensible, and that is fine.
- [ ] Ask something outside every competence. Did the model say `none`, or invent a node? If it
      invented one, look at how the graph rejected it.
- [ ] Make the supervisor **disagree** with an answer (ask something the knowledge base only
      partly covers, for instance). How many revisions ran before the limit?

### With LangGraph installed

```bash
pip install -e ".[s03]"
python -m stages.s03_router.check
```

- [ ] Did the check print "AC-06 перевірено: 7 маршрутів збіглися з власним графом"?
- [ ] How much time did that check add to the run? Write it down — that is the price of a second
      implementation.
- [ ] Open `langgraph_impl.py` and `graph.py` side by side. Find every part of the second inside
      the first. If some part cannot be found, that is the most interesting place for a question.
