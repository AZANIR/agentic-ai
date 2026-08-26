# Stage 1 — The agent loop

> Stage article: [Three Guards Every Agent Loop Needs](https://artstroy.net/articles/three_guards_every_agent_loop_needs)
> · [Exercises](exercises.md) · [Checklist](CHECKLIST.md)

## What you will be able to do after this stage

- Explain **in words** why a language model does not execute functions itself.
- Read any agent framework and recognise this same loop inside it.
- Name three ways an agent breaks, and point at the code that stops each one.

Time: 2–3 hours. Cost: nothing.

## Run this before you read

```bash
python -m stages.s01_agent_loop.run
```

No network, no key needed. The first line tells you where the answers come from.
Look at the output — we are about to take apart where every line of it came from.

---

## Part 1. What an agent is

Picture an extremely well-read person locked in a room. You slide a note under the door, they
read it, think, and slide an answer back. One note in, one note out. They cannot open the door,
look something up, or call anyone. All they can do is **talk**.

That is an ordinary language model. Powerful, and it **does** nothing.

Now give them a phone, access to email, and the ability to run scripts. And, above all, let
them decide **what to use and when**. That is an agent.

An agent is three things:

| Part | What it is | Where it lives in our code |
|---|---|---|
| **Brain** | the language model that reasons and decides | `shared/llm.py` |
| **Tools** | the functions it is allowed to call | [`tools.py`](tools.py) |
| **Memory** | optional; our agent has none | stage 5 |

And one loop joining them:

```
        task
          ↓
    ┌─→ model: "what next?"
    │     ↓
    │  picks a tool
    │     ↓
    │  we run the tool
    │     ↓
    │  the result goes back to the model
    │     ↓
    └── "am I done?" — no
              ↓ yes
          answer
```

This loop is called **ReAct** (Reasoning + Acting). Everything is built on it: LangGraph,
CrewAI, AutoGen, Google ADK. The only difference is how much of it has been hidden from you.

Here nothing is hidden.

---

## Part 2. The one sentence that matters most in this stage

> **The model does not execute functions. It asks for them.**

When a model "calls a tool", what it actually returns is text along the lines of: "I want
`get_order_status` with the arguments `{"order_id": "ord_4471"}`". After that it is **your
code** that decides whether to call that function at all.

This is not a technical footnote. It is what makes agents governable: between the model's
decision and its consequence in the real world there is a gap, and a check fits in that gap.

That is exactly where we put three guards.

---

## Part 3. Reading the code — five files

The order matters: each one builds on the one before it.

### `tools.py` — what the agent is allowed to do

```python
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]  # the schema the model will see
    func: Callable[..., str]  # the function we will call
    irreversible: bool = False  # whether confirmation is required
```

Three tools: `get_weather` (the canonical one from the article), `get_order_status` (our
NovaShop domain), and `initiate_return` — irreversible.

**The most important thing here is `description`.** The model does not see the code. It picks a
tool by reading its name and its description. A vague description breaks that choice harder
than a weaker model does — and it is the cheapest way there is to ruin an agent.

The registry is a plain dictionary rather than a decorator. A decorator would look neater, and
it would hide the registration: you have to be able to see the full list of what is allowed at
a glance.

### `validate.py` — the trust boundary

Forty lines that decide whether the arguments coming back from the model even resemble the
truth. Three cases: a required field is missing, an unexpected field is present, the type is
wrong.

**Types are never coerced.** The string `"3"` where a number was declared is a rejection, not an
invitation to guess. Silent coercion would hide the model's mistake at exactly the point where
you need to see it.

One detail that is easy to trip over:

```python
if expected in ("integer", "number") and isinstance(value, bool):
    return False
```

In Python `bool` is a subtype of `int`, so `isinstance(True, int)` is true. Without that line
`True` would pass quietly wherever a number is expected.

### `loop.py` — the loop itself

All the "magic" is one `while`. Read it end to end; it is worth it.

```python
while result.steps < limit:                    # ← guard 1
    response = client.chat.completions.create(...)
    message = response.choices[0].message

    if not message.tool_calls:                 # the model answered with text
        result.answer = message.content
        return result

    for call in message.tool_calls:
        outcome = _execute(call, tools, tracer, confirmed=confirmed)
        messages.append({"role": "tool", ...})  # the result — back to the model
```

Note `messages.append({"role": "tool", ...})`. The tool's result **must** go back to the model.
Without that it would be answering blind — and that is precisely what the commonest mistake in
home-made agents looks like.

One more detail from the protocol:

```python
arguments = json.loads(call.function.arguments)
```

`arguments` arrives as a **JSON string**, not a dictionary. That is how the protocol works, and
our fake model reproduces it exactly — otherwise your code would work against the fake and
break against a real provider.

### `gate.py` — the confirmation gate

Thirty lines that decide the fate of **the whole step** rather than of an individual call. Why
the step — part 4.

### `run.py` — the demo

Four scenarios, each showing one acceptance criterion. Look at the output rather than the code.

---

## Part 4. Three guards

### Guard 1 — the step limit

**What breaks without it.** The task is unclear, a tool returns something unusable, the model
tries again. And again. Tokens burn, there is no answer.

**How we stop it.** A counter in the loop. When the limit is spent:

```python
result.stopped_by_limit = True
return result  # answer stays None
```

There is no answer — and inventing one is **not allowed**. An honest "I could not do it" beats
a plausible piece of text with nothing behind it. Scenario 3 of the demo shows this.

### Guard 2 — argument validation

**What breaks without it.** The model invents a field `town` instead of `city`, your function
receives an unexpected argument and crashes — or, worse, works on the wrong thing.

**How we stop it.** Arguments do not reach the function until they have passed the schema. The
reason for the rejection goes back to the model as the result of the step, and the loop
**continues**.

Look at scenario 2 in the demo output:

```
-> модель просить get_weather({"town": "Київ"})
<- Аргументи не підходять — не вистачає обов'язкових полів: city; невідомі поля: town...
-> модель просить get_weather({"city": "Київ"})
<- У Києві +28°C...
```

The model corrected itself **in one round**, because it got both facts at once. Had we reported
only the first, it would have learnt about `town` on the next call — more tokens, more latency.

### Guard 3 — the confirmation gate

**What breaks without it.** A customer asks "what is your returns policy?", the model hears
"process a return" — and processes one. Money is refunded, the warehouse is notified, there is
nothing left to roll back.

**How we stop it.** Before **anything** in the step runs, [`gate.py`](gate.py) looks over every
tool the model asked for in that one response:

```python
blocked = screen(message.tool_calls, tools, confirmed=confirmed)
if blocked is not None:
    return result        # NOTHING was executed
```

Confirmation arrives as **a separate second run**, not as a console prompt:

```bash
python -m stages.s01_agent_loop.run --confirm
```

The reason is prosaic: `input()` in CI reads end-of-stream and crashes, and the check would then
need standard input mocked — the first piece of magic in the course.

**Why the gate looks at the whole step rather than at each call separately.** The model can ask
for several tools in a single response. Check them one at a time and you get a trap:

| | one call at a time | the whole step |
|---|---|---|
| without confirmation | we block on the first; the reader never learns about the rest | we show **every** irreversible action |
| with confirmation | we run **all** of them, including the invisible ones | we run exactly what we showed |

Which is to say a per-call gate turns confirmation into blanket permission. The run has to show
**what would actually happen** — all of it, not the first item. Confirming blind is not
confirmation.

This flaw was in the first version of the stage and was found only by an independent review.
The author wrote both the code and the tests, and the two agreed with each other — they were
simply wrong together.

---

## What to break

The most useful part. Break it, look, put it back.

1. In [`gate.py`](gate.py) replace `and tool.irreversible` with `and False` — the gate stops
   firing at all. Run the demo: scenario 4 now processes the return by itself. Run
   `python -m stages.s01_agent_loop.check` — **three** checks go red, and each one says what
   exactly broke (`виконано попри блокування`, `незворотну функцію виконано без
   підтвердження`, `у трейсі демо немає step_blocked`). Put it back.

   > Careful with the more intuitive edit: drop only `not confirmed` from the condition and the
   > gate starts blocking **always** rather than never. The demo does not pass confirmation, so
   > the output does not change, and you will conclude you are looking in the wrong place. That
   > is exactly the mistake the first version of this lesson made.
2. In [`validate.py`](validate.py) remove the line about `bool`. Add a tool with an integer
   parameter and send it `True`. Watch what gets through.
3. In your `.env` (see [`.env.example`](../../.env.example)) set `AGENT_MAX_STEPS=1`. What happens to scenario 1?
4. In [`tools.py`](tools.py) replace the description of `get_order_status` with `"Does a
   thing."` — and run against a **real** model. Does it still pick the right tool?

The full list is in [`exercises.md`](exercises.md).

---

## Manual checklist: a real model

The checks deliberately stay off the network, so half of criterion AC-05 is yours to close. Five minutes:

1. Sign up at [Groq](https://console.groq.com) — free tier, no card needed.
2. In `.env`:
   ```ini
   LLM_BASE_URL=https://api.groq.com/openai/v1
   LLM_API_KEY=gsk_your_key
   LLM_MODEL=llama-3.3-70b-versatile
   ```
3. `python -m stages.s01_agent_loop.run`

What should happen:

- [ ] The first line changed from `[FakeLLM]` to `[LLM] https://api.groq.com/...`
- [ ] Scenario 1: the model picked `get_order_status` on its own, without being told to
- [ ] Scenario 4 showed the gate, and `--confirm` carried the action out
- [ ] Scenario 3 **may** end differently: the fake's looping is scripted, and a real model will
      more likely just answer with text. That is not a bug — the step limit is proved by the
      check, not by the demo
- [ ] The wording of the answers is different, and that is fine. The loop, the tools and the
      output format are the same

That last point is the whole idea: **the model changed, the code did not.**

---

## The limits of this stage — so you do not carry them into production

- **Validation** covers flat objects with scalar types only. Nested objects and arrays are not
  checked. In production this is where `jsonschema` or `pydantic` belongs.
- **The agent has no memory.** Every run starts from nothing. It is a visible gap — stage 5
  closes it.
- **Green checks do not mean "the agent is good".** The checks measure the logic **around** the
  model: the limit fired, the arguments were cut off, the gate held. The quality of the answers
  themselves is stage 8.
- **The confirmation gate is a teaching one.** In production a confirmation has to survive a
  process restart and be bound to a specific user.

---

## Next

[Stage 2 — RAG](../s02_rag/): the agent knows nothing about your documents. Let us teach it to read.

Before you move on — [`CHECKLIST.md`](CHECKLIST.md): I understood / I ran / I explained.
