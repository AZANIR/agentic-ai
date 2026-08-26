# Checklist — stage 4

Three levels. Passing means closing all three, not the first.

## I understood

- [ ] I can name the three roles — host / client / server — and say which of them owns which.
- [ ] I can explain what exactly `list_tools()` changes, and why that matters more than convenience.
- [ ] I understand why `json.loads` over the whole response breaks, and why a regex is worse still.
- [ ] I can name the three failure phases and say why they must not be merged into one.
- [ ] I can explain what stays with the client when a foreign server declares the tools.
- [ ] I tell a tool, a resource and a prompt apart — and can give an example of each.
- [ ] I know what this stage does **not** promise: that the model will ignore hostile text in a description.

## I ran it

- [ ] `pip install -e ".[s04]"` — and saw that before it, the demo honestly said what it did not show.
- [ ] `python -m stages.s04_mcp.run` — all six scenes.
- [ ] `python -m stages.s04_mcp.run --raw` — looked at the server's **raw** response.
- [ ] `python -m stages.s04_mcp.check` — all green; 36 checks, 21 of them on failure modes.
- [ ] `python scripts/clean_install.py mcp` — and saw `NOT VERIFIED` instead of green.
- [ ] `python scripts/mutate.py s04 --expect` — the numbers in the exercises match the run.
- [ ] Broke the parser (exercise 1) and saw that one defect is visible from seven places.

## I explained

Not to myself — out loud, to another person or in writing.

- [ ] **Why is a tool description from somebody else's server more dangerous than its code?**
      Hint: you do not execute the code, and the description goes into the prompt.
- [ ] **Why are "the server never came up" and "the server went quiet" different events?**
      Hint: what you are going to do in each of the two cases.
- [ ] **Why can missing data not be returned as an empty dict?**
      Hint: what tells a broken server from a working one after that.
- [ ] **Why is an MCP tool not an endpoint?**
      Hint: what the model wants — three calls or an answer.
- [ ] **What exactly is being paid for with that second per call?**
      Hint: two things, and neither of them is speed.

---

## Manual checklist: somebody else's server

Our server is ours, so its behaviour is predictable. The interesting part starts here.

```bash
# Take any public MCP server and point client.py at it
```

- [ ] **Look at the raw response first.** Is there prose? Is there a block at all?
- [ ] How many tools does it declare? Walk [`DECISION.md`](DECISION.md) over each one:
      how many of them should really have been parameters?
- [ ] Are the schemas usable in `tools=` without conversion? Write down what you had to fix.
- [ ] **Read every description with your own eyes.** Is any of them phrased as an instruction to
      you rather than a description of an action? This is not paranoia: the description goes into
      the prompt, and you did not write it.
- [ ] How many of the declared tools would you mark irreversible? How many did the server mark?
      The difference is what `bridge.py` decides on your behalf.
- [ ] Kill the server mid-call (close the process by hand). Which phase? How long did you wait?
- [ ] Time a single call. Compare it with the second our demo takes — and think about whether
      that difference comes from the protocol or from what the server itself does.

### With a real model

```bash
# .env:  LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
```

- [ ] Hand the model a registry from `bridge.registry()` and see whether it picks the right tool
      by the description **from the server** rather than from your code.
- [ ] Slip in the hostile description from scene 5 of the demo and see whether the model obeys.
      If it does — make sure the gate fired anyway. That is exactly what this stage promises.
