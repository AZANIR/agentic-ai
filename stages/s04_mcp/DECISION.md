# A separate tool or one more endpoint

The commonest MCP mistake looks like diligence: take your REST API and declare every endpoint a
tool. The result is a server with forty tools where the model chooses worse than it would among
five — the same defect as on stage 3, arriving from the other side.

> **An MCP tool is not an endpoint. It is a job somebody wants done.**

`GET /orders/{id}`, `GET /orders/{id}/items` and `GET /orders/{id}/shipping` are three endpoints
and **one** tool: "tell me about the order". The model does not want three calls; it wants an
answer.

## Three verdicts

    SEPARATE TOOL   the job stands on its own, the model picks it deliberately
    PARAMETER       the same job, a different volume or filter
    DO NOT EXPOSE   the model has no reason to call this

## The checklist

The rules are checked top to bottom, and the first one to fire wins. The order is a decision
too:

| Position | What is checked | Why here |
|---|---|---|
| 1–2 | **Safety** | An action that cannot be confirmed is not exposed at all — however self-contained it is |
| 3–4 | **Whether the job stands alone** | Is this something somebody wants done, or a variant of something else |
| 5–6 | **The shape of the answer** | The weakest argument: volume and filter are almost always cured by a parameter |

| # | Signal | Answer |
|---|---|---|
| 1 | The model has no reason whatsoever to call this | **DO NOT EXPOSE** |
| 2 | An irreversible action with no way to confirm | **DO NOT EXPOSE** |
| 3 | This is a job of its own, not a variant of another | **SEPARATE TOOL** |
| 4 | It needs different permissions from the action beside it | **SEPARATE TOOL** |
| 5 | The same job, a different volume or filter | **PARAMETER** |
| 6 | One of many endpoints of a single entity | **PARAMETER** |
| — | No signal fired | **PARAMETER** |

The same rules live as code in `decision.py`, and a check asserts that the table below matches
**verbatim** what the code prints.

```
python -m stages.s04_mcp.decision
```

## Seven situations

| Situation | Answer | Why |
|---|---|---|
| An internal data-migration endpoint | **DO NOT EXPOSE** | The model has no reason to call it, and the price of a mistake is the whole database. |
| Deleting an account with no confirmation gate | **DO NOT EXPOSE** | The irreversible without a confirmation is not exposed. Gate first, tool after. |
| Start a return for an order | **SEPARATE TOOL** | A job of its own with its own result. The model picks it deliberately. |
| Search of internal documents for operators | **SEPARATE TOOL** | Different permissions from the public search. One tool with a flag will not do. |
| Orders from the last month instead of all of them | **PARAMETER** | The same job, a different filter. A second tool only blurs the choice. |
| GET /orders/{id}/items next to GET /orders/{id} | **PARAMETER** | The model wants an answer about the order, not three calls about its parts. |
| One action users ask for in words every day | **SEPARATE TOOL** | The simplest case, and worth having on the list too: if they ask, expose it. |

## What the checklist does not decide

**It does not say how many tools is too many.** That depends on how different the descriptions
are from one another, not on a count. Twenty tools with sharp boundaries work better than five
the model confuses.

**It does not save you from a bad description.** A tool named correctly and described vaguely
loses to the same tool with a sharp description. The description is what the model chooses by;
stage 3 shows that on numbers.

**The second row of the table is the most important one.** An irreversible action with no
confirmation gate is not exposed at all. Gate first — then the tool, not the other way round.
