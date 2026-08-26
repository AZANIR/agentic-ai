# Stage 3 — Router: when one agent is not enough

> Previous stage: [Stage 2 — RAG](../s02_rag/README.md) ·
> This stage's code is pinned at tag `stage-03`

## What you will be able to do after this stage

- explain why one bloated agent loses to three narrow ones, and name the boundary where that
  starts;
- write the routing yourself and see that there is nothing in it beyond a `while` and a
  dictionary;
- design a state schema deliberately — and say what adding a field to it will cost;
- stop a revision loop with a counter rather than with an invoice;
- carry the access level through a handoff so that it does not go missing on the way;
- answer "do we need a supervisor" from a checklist — and most often hear "no".

## Run this before you read

```bash
python -m stages.s03_router.run
python -m stages.s03_router.run --prompt    # shows the prompt the route is chosen by
python -m stages.s03_router.check
python -m stages.s03_router.decision        # the "do you need a supervisor" checklist
```

No API key needed. LangGraph is not needed either: without it the stage still runs end to end,
and the route-comparison check honestly says it was **not verified**.

## Part 1. Why one agent stops coping

In stage 1 the agent had three tools; in stage 2 a fourth appeared. The temptation is obvious:
add a fifth, a tenth, a twentieth. Every description goes into the same prompt.

At some point the model starts choosing worse than it did with five tools. The most common
reaction is to rewrite the prompt, and it does not work, because the problem is not in the
prompt:

> **One model holds one description of the task in its head. The wider that description, the
> blurrier the choice.**

This is not a property of one particular model and it will not go away with the next version. It
is the same thing that happens to a person handed a forty-point job description.

## Part 2. The one sentence that matters most in this stage

> **A supervisor is the same agent, with other agents as its tools.**

No new architecture appears. The same loop as in stage 1, the same registry, the same model call
— except that behind the "tool" name stands not a function but another agent with its own narrow
set.

Two things follow immediately, and they are what make this stage non-trivial:

- **The specialist receives a task, not the asker.** Everything the supervisor knew and did not
  pass on does not exist for the specialist. Access rights are the first thing lost this way.
- **The supervisor may disagree with the answer.** That brings a revision loop, and with it the
  possibility of spinning forever on your money.

## Part 3. Reading the code — five files

### `state.py` — the state schema, the most expensive decision of the stage

**Every** node reads and writes the state. The easiest thing is to make it a dictionary: adding a
field is one line and nobody declares anything. That is what most examples look like.

And that is exactly why the main point is invisible in them:

> **When adding a field costs one line, nobody asks what the field actually costs.**

And it costs as much as the number of nodes that come to depend on it — none of which will
mention that it appeared. Six months later the field can neither be renamed nor removed, because
nobody knows who reads it.

Here the schema is declared, and `__slots__` makes it a contract for free:

```python
class State:
    __slots__ = DECLARED   # reading or writing anything else is an error
```

Look at scene 2 of the demo: it prints **the whole** list of what the graph knows about a task.
Ten fields. To add an eleventh you have to open this file — that is, see everyone who reads it.
That is the entire cost, and it is charged at the moment of the action rather than six months
later.

**Three fields are immutable after creation.** The main one is `access`: the access level comes
in from the call into the graph, and no node has the right to raise it.

### `specialists.py` — three narrow competences built from what already exists

The orders specialist is stage 1's loop with its registry and its three guards. The knowledge
specialist is stage 2's retrieval with the access filter. The third and simplest one is added
here.

**The competence description matters more than the node's name.** The model picks the route, and
it picks it by the description: `orders` tells it nothing, whereas "the status of a specific
order by its number, processing a return" does. Run `--prompt` and look at what the model
actually sees.

**The specialist takes the access level from the state, not from its arguments:**

```python
found = knowledge_base().search(state.query, access=state.access, top_k=3)
```

An argument can be forgotten while adding a fourth specialist. A state field cannot.

### `graph.py` — the whole supervisor in half a screen

Forty-nine executable lines out of eighty. Read them and it is hard not to notice: **there is
nothing new here**. A dictionary, a model call, a `while` with a counter.

Three places are worth reading slowly:

**The model picks the route, and the graph validates it.**

```python
choice = _ask(client, route_prompt(state), model)
if choice not in SPECIALISTS:
    return _refuse(state)
```

The model can name a node that does not exist — and it will, sooner or later. Scene 4 of the demo
shows this: the model said `weather`, no specialist was invoked, and the answer lists the real
competences. **The model has the right to be wrong; the graph does not have the right to take it
at its word.**

**The revision loop has a counter, and the counter lives in the state.** It is the same guard as
stage 1's step limit, in the same place — before the action, not after.

**A specialist's exception and a broken contract are different events**, and the reactions to
them are opposite:

    a specialist raised           an environment event    -> becomes a step result, the graph lives
    a node read an unknown field  a programmer's error    -> we stop, naming the field

The first is normal: the warehouse can be down. The second means the contract is broken, and
carrying on with an empty value is worse than stopping.

### `langgraph_impl.py` — the same thing with a library

```bash
pip install -e ".[s03]"
```

Read it **after** `graph.py`, for the recognition:

    our specialists dictionary  ->  add_node for each of them
    our if choice not in ...    ->  add_conditional_edges
    our while with a counter    ->  an edge going back into the node
    our state.finish_reason     ->  END

The check compares seven routes and fails on any divergence. Without the library installed it
prints that AC-06 was **not verified** — the difference between "they matched" and "we did not
look" has to be visible.

**One divergence is worth attention.** LangGraph's state is a `TypedDict`, that is, a dictionary:
`state.get("typo")` returns a silent `None`. Our `state.py` deliberately does otherwise. This is
not a flaw in the library — it cannot know in advance which nodes you will add, and it chooses
flexibility. The price of that flexibility is exactly the one described above, and seeing it side
by side is more useful than reading about it.

### `decision.py` — do you need a supervisor here

The most common answer is **no**. A graph of three agents looks like architecture, while one
agent with three tools looks unfinished; systems in which every answer costs three model calls
instead of one are built on that feeling.

There are three verdicts, not two, and the middle one is the most important: **classifier** — a
cheap branch choice with no revision loop. Most systems built as supervisors needed exactly that.

The order of the rules is a decision too: structural constraints first, then cost, and only at
the end size — the weakest argument, and the one heard most often. The full version is in
[`DECISION.md`](DECISION.md).

## Part 4. What to break

After each change run `python -m stages.s03_router.check` and look at **how many** checks went red
and **which ones**.

1. **Remove the route-against-registry validation** in `graph.py`. The model can now send a task
   to a node that does not exist.
2. **Make the revision limit unreachable** (`>= 10_000`). The second implementation goes red too.
3. **Give the knowledge specialist a fixed access level** instead of `state.access` — first
   `"public"`, then `"internal"`. Two almost disjoint sets of red.
4. **Allow writes to `access`** — in two ways: `if False:` and `FROZEN = frozenset()`.
5. **Empty the list of competences** in the routing prompt.
6. **Remove one situation from the checklist**, leaving the rule without it.

The walkthrough with measured results is in [`exercises.md`](exercises.md).

## Manual checklist: a real model

The checks run on a fake, so the route in them is deterministic. What happens with a real model
is separate, in [`CHECKLIST.md`](CHECKLIST.md), and it is the most interesting part of the stage.

## The limits of this stage — so you do not carry them into production

- **The hand-rolled graph is not production-fit.** Thirty-seven lines show the mechanics; they
  can do neither parallel branches, nor checkpoints, nor recovery after a crash.
- **On the fake the route is correct by construction.** A real model routes differently and
  sometimes worse. That is not a defect of the implementation but a quantity you measure — stage
  8.
- **The specialists share one process.** The network arrives in stage 4 (MCP) and stage 6
  (deployment).
- **There is no memory between runs.** State lives for one run; memory is stage 5.
- **Every route costs a model call.** In stage 6 that becomes a budget question, and the cheaper
  classifier appears there as a deliberate trade-off.

## The numbers

**38 checks, 20 of them on failure modes** — exactly half, as in the previous stages. Among
them is a check that reconciles **the numbers in this lesson** with what the command prints: in
stage 2 the prose drifted away from the suite, and a reader who took the advice to run the checks
would have seen the discrepancy with their very first command.

## Next

Stage 4 — **MCP**: the stage 3 agent moves from local functions onto a protocol without changing
its own logic. The stage's question: why `list_tools()` makes an integration discoverable, and
why a few well-considered tools beat a map of every endpoint in your API.
