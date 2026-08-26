# Exercises — stage 4

Do these after you have read the [lesson](README.md) and run the demo.

**One rule: break it first, then look, then put it back.**

```bash
git checkout stages/s04_mcp/
```

The numbers below are **measured** and pinned by machine:

```bash
python scripts/mutate.py s04 --expect
```

The script applies every mutation on this page, counts the red checks, and fails if the number
has drifted from what is promised here.

> **The measurements were taken with MCP installed.** Without it the subprocess checks are
> marked `NOT VERIFIED` — not passed — and the numbers will be smaller.

---

## Exercise 1 — Parse the whole response instead of the block

**Difficulty:** easy · **Time:** 10 min · **Start here**

In [`parse.py`](parse.py) replace `for block in _FENCED.findall(response):` with
`for block in [response]:` — that is, try to parse the whole response at once.

<details>
<summary>What happens</summary>

**Seven** checks go red — the most of any exercise on this stage:

```
integration · a call through the protocol yields the same value as the local function
integration · the server talks around the data — which is exactly why the parser is needed
FAILURE · the access level rides in the payload and narrows the result on the other side
FAILURE · a call with no trace does not exist as a state
e2e · the demo shows six scenes and leaves a trace
FAILURE · parse: data is extracted from a response wrapped in prose
FAILURE · parse: an empty list is a result, not an absence of data
```

Seven — because **every call** to the search server goes through prose. These are not seven
different defects but one, visible from seven places.

Now do the opposite: stand up a server that answers with **data only**, and see the naive parser
work flawlessly. That is exactly how this defect reaches production: the first server is
taciturn, and the code looks correct right up until a second one appears.
</details>

---

## Exercise 2 — Let missing data become an empty dict

**Difficulty:** easy · **Time:** 10 min

In [`parse.py`](parse.py) replace `raise NoPayload(_first_lines(stripped))` with `return {}`.

<details>
<summary>What happens</summary>

**Two** checks:

```
FAILURE · parse: missing data is a state of its own, not an empty result
FAILURE · parse: an example inside the prose is not mistaken for data
```

The second is the more interesting one. It checks that a fragment from an explanation of the
format — `{"order_id": "..."}` — is not taken for data. With `return {}` it goes red **not
because the example was taken**, but because an empty dict came back instead of an honest
refusal.

The difference worth feeling: after this change a call to a broken server and a call to a
working one that found nothing give **the same** result. There is nothing left to diagnose with.
</details>

---

## Exercise 3 — Make an unknown tool reversible

**Difficulty:** medium · **Time:** 15 min

In [`bridge.py`](bridge.py) replace

```python
return name in IRREVERSIBLE or name not in ALLOWED
```

with

```python
return name in IRREVERSIBLE and name in ALLOWED
```

<details>
<summary>What happens</summary>

**One** goes red:

```
FAILURE · bridge: a tool outside the allow list does not make it into the registry
```

One — and that is enough, because the mutation breaks the **default**, not the current
behaviour. Every known tool stays correct; what changes is only what happens to the next one,
which does not exist yet.

This is fail-closed: the error has to fall on the side of "asked one time too many" rather than
"charged the money silently". The same principle as the access metadata on stage 2 — and there,
too, it took a review to appear.
</details>

---

## Exercise 4 — Take everything the server offers

**Difficulty:** medium · **Time:** 15 min

In [`bridge.py`](bridge.py), inside `registry`, replace
`if info.name not in ALLOWED or info.name in built:` with `if False:` — that is, take
everything the server declared.

<details>
<summary>What happens</summary>

**Two** checks:

```
FAILURE · bridge: a tool outside the allow list does not make it into the registry
FAILURE · bridge: a duplicated name does not shadow the first declaration
```

Now `wipe_customer_data` — "a routine maintenance operation", as its description says — makes it
into the agent's registry. The model can pick it.

The second red one is a surprise: the same condition that filtered by the allow list was also
discarding duplicates. Remove one thing, lose two.

Run the demo after this change and look at scene 5: the "not taken into the registry" line goes
empty. An empty list of rejects is not a reason to celebrate but a reason to check whether there
is anything to reject at all.
</details>

---

## Exercise 5 — Leave the access level in the schema

**Difficulty:** medium · **Time:** 15 min

In [`bridge.py`](bridge.py) replace `schema = _without(info.schema, fixed)` with
`schema = info.schema`.

<details>
<summary>What happens</summary>

**Three** checks, and two of them are about entirely different properties:

```
FAILURE · bridge: the access level is substituted by the client and not shown to the model
FAILURE · bridge: a foreign schema collapses to an empty one instead of crashing the registry
FAILURE · bridge: `required` cannot name a field the schema does not have
```

Now `access` is in the schema the model sees. It can pass `"internal"` — and it will do so not
out of malice but because that way more will be found.

This is exactly the same defect as on stage 3, and for exactly the same reason: **the access
level is a fact about whoever is asking, not an argument chosen while answering.** Here it
arrives from a new direction — through somebody else's schema.

And the other two reds explain why the client **rewrites** the schema rather than passing it
through as it is: along with access, everything else comes through it — unvalidated
`properties` and `required` naming fields that are not there. The protection turned out to be a
layer, not a single condition: one mutation, three consequences.
</details>

---

## Exercise 6 — Make the timeout ten times longer

**Difficulty:** medium · **Time:** 20 min

In [`client.py`](client.py) replace `..., timeout)` with `..., timeout * 10)` in the
`asyncio.wait_for` call.

<details>
<summary>What happens</summary>

```
FAILURE · the two failure phases are different, and neither reason is empty
```

One check — and it has an interesting history. At first it said `assert took < 10`, and with a
timeout of 1.5 s the mutation produced 15 s and went honestly red. Then the timeout was reduced
to 0.6 s for the sake of suite speed — and the same mutation started producing 6 s, that is,
**passing**.

Nobody broke anything: a constant bound stopped matching a parameter that was reduced somewhere
else, for a different reason. The bound is now derived: `1.5 + asked * 3`.

Now remove `asyncio.wait_for` entirely and run the suite. It will **hang** — not fail, hang.
That is the failure the timeout exists for, and the reason `mute.py` is in the repository: a
server that comes up and stays silent.
</details>

---

## Exercise 7 — Feed the bridge a broken schema

**Difficulty:** medium · **Time:** 20 min · **Came out of a review**

In [`bridge.py`](bridge.py) replace `declared = declared if isinstance(declared, dict) else {}`
with `declared = declared`.

<details>
<summary>What happens</summary>

```
FAILURE · bridge: a foreign schema collapses to an empty one instead of crashing the registry
```

One check — and it feeds the bridge five shapes taken from a real run against a home-made
server:

```
"properties": null       -> AttributeError
"required": null         -> TypeError
"properties": ["query"]  -> AttributeError
"required": "query"      -> a string instead of a list
{}                       -> no schema at all
```

`mcp.types.Tool.input_schema` is typed simply as `dict[str, Any]` — that is, the library **does
not validate the contents**. Somebody else's server was crashing not its own tool but the
assembly of the **whole** registry: one bad description switched the agent off entirely.

An independent review found this defect, and the worst thing about it is not the exception
itself but that the module opens with the words "the whole point is what the server **cannot**
do".
</details>

---

## Exercise 8 — Declare the same tool twice

**Difficulty:** medium · **Time:** 20 min · **Came out of a review**

In [`bridge.py`](bridge.py) replace `if info.name not in ALLOWED or info.name in built:` with
`if info.name not in ALLOWED:`.

<details>
<summary>What happens</summary>

```
FAILURE · bridge: a duplicated name does not shadow the first declaration and lands in the rejects
```

The attack is subtle, and that is what makes it interesting. The server declares
`search_knowledge_base` **twice**: honestly the first time, with a hostile description and an
entirely different schema the second. The dict keeps the last one.

Notice what did **not** happen here: the allow list was not violated. The name is the same, it
is in `ALLOWED`, `rejected()` is empty. Protection built on a list of names simply does not fire
here — because what was swapped was not the name but what stands behind it.

Now the first declaration wins and the duplicate lands in the rejects with a note. An empty list
of rejects is not a reason to celebrate but a reason to check whether there is anything to
reject.
</details>

---

## Exercise 9 — Stand up somebody else's MCP server

**Difficulty:** medium · **Time:** 30 min · **The most useful one**

Take any public MCP server (there are dozens) and point `client.py` at it by changing
`SERVER_MODULE` or passing `module=`.

<details>
<summary>What to think about</summary>

**The first thing worth doing is looking at the raw response.** Our `--raw` shows exactly that.
The questions worth answering before writing any code:

- Is there prose around the data? Is there a block at all?
- Are the schemas usable in `tools=` without conversion, or do they need rewriting?
- How many tools does it declare? Are half of them not endpoints
  ([`DECISION.md`](DECISION.md))?
- Is there anything among the descriptions that reads as an instruction to you rather than a
  description of an action?

That last question is not paranoia. The description goes into the prompt, and you did not write
it.

Then try what `bridge.py` will do: are all the declared tools on your allow list? How many of
them would you mark irreversible where the server did not?
</details>

---

## Exercise 10 — Move the stage 3 graph onto MCP in the demo

**Difficulty:** hard · **Time:** 60 min

`wiring.py` already swaps the stage 1 registry for the MCP registry, and the `AC-05` check runs
the graph's six queries through it. But **the demo does not show this**. Add a scene that runs
the graph over MCP — **without changing a single line in `stages/s03_router/`**.

<details>
<summary>What to think about</summary>

The "stages 1–3 are unchanged" check is already in the suite and will go red if you change them.
This is not a formality: the stage's claim is that the protocol is a wiring detail, and the only
way to prove it is to leave alone the thing you are wiring.

What is worth measuring rather than guessing:

- **how long the same run of six queries takes** over MCP against locally. Scene 6 of the demo
  gives the order of magnitude for one call; multiply it by the number of calls in the graph;
- whether the **route** of even one query changed. It should not have — but check;
- what happens when the server dies mid-run of the graph. The specialist will return text about
  unavailability; the supervisor will see it as an ordinary answer. Is that right or not?

The last question has no single answer, and that is exactly why it is here.
</details>
