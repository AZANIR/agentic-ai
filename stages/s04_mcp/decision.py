"""The "a separate MCP tool or one more endpoint" checklist — by rules, not by eye.

The commonest MCP mistake looks like diligence: take your REST API and declare every endpoint a
tool. The result is a server with forty tools where the model chooses worse than it would among
five — and that is the same defect as on stage 3, arriving from the other side.

> **An MCP tool is not an endpoint. It is a job somebody wants done.**

`GET /orders/{id}`, `GET /orders/{id}/items` and `GET /orders/{id}/shipping` are three endpoints
and **one** tool: "tell me about the order". The model does not want three calls; it wants an
answer.

The order of the rules is a decision too. First it is checked whether the **action** is a job of
its own, and only then everything else: response size, permissions, frequency. Response size
sounds convincing and is in fact the weakest of them — it can almost always be fixed with a
parameter.

Three verdicts:

    SEPARATE TOOL   the job stands on its own, the model picks it deliberately
    PARAMETER       the same job, a different volume or filter
    DO NOT EXPOSE   the model has no reason to call this
"""

from __future__ import annotations

from dataclasses import dataclass, field

TOOL = "SEPARATE TOOL"
PARAMETER = "PARAMETER"
HIDE = "DO NOT EXPOSE"


@dataclass(frozen=True)
class Rule:
    signal: str
    answer: str
    text: str


@dataclass(frozen=True)
class Verdict:
    answer: str
    rule: str


@dataclass(frozen=True)
class Situation:
    name: str
    expected: str
    why: str
    signals: dict[str, bool] = field(default_factory=dict)


RULES = [
    Rule("no_reason_to_call", HIDE, "The model has no reason whatsoever to call this"),
    Rule("irreversible_without_confirm", HIDE, "An irreversible action with no way to confirm"),
    Rule("distinct_task", TOOL, "This is a job of its own, not a variant of another"),
    Rule("different_permissions", TOOL, "It needs different permissions from the action next to it"),
    Rule("same_task_other_shape", PARAMETER, "The same job, a different volume or filter"),
    Rule("one_of_many_endpoints", PARAMETER, "One of many endpoints of a single entity"),
]

SITUATIONS = [
    Situation(
        name="An internal data-migration endpoint",
        expected=HIDE,
        why="The model has no reason to call it, and the price of a mistake is the whole database.",
        signals={"no_reason_to_call": True},
    ),
    Situation(
        name="Deleting an account with no confirmation gate",
        expected=HIDE,
        why="The irreversible without a confirmation is not exposed. Gate first, tool after.",
        signals={"irreversible_without_confirm": True},
    ),
    Situation(
        name="Start a return for an order",
        expected=TOOL,
        why="A job of its own with its own result. The model picks it deliberately.",
        signals={"distinct_task": True},
    ),
    Situation(
        name="Search of internal documents for operators",
        expected=TOOL,
        why="Different permissions from the public search. One tool with a flag will not do.",
        signals={"different_permissions": True},
    ),
    Situation(
        name="Orders from the last month instead of all of them",
        expected=PARAMETER,
        why="The same job, a different filter. A second tool only blurs the choice.",
        signals={"same_task_other_shape": True},
    ),
    Situation(
        name="GET /orders/{id}/items next to GET /orders/{id}",
        expected=PARAMETER,
        why="The model wants an answer about the order, not three calls about its parts.",
        signals={"one_of_many_endpoints": True},
    ),
    Situation(
        name="One action users ask for in words every day",
        expected=TOOL,
        why="The simplest case, and worth having on the list too: if they ask, expose it.",
        signals={"distinct_task": True},
    ),
]


def decide(signals: dict[str, bool]) -> Verdict:
    """Walk the rules top to bottom and stop at the first one that fires."""
    for rule in RULES:
        if signals.get(rule.signal):
            return Verdict(answer=rule.answer, rule=rule.text)
    return Verdict(answer=PARAMETER, rule="No signal fired — this is a parameter, not a tool")


def table() -> str:
    """The same checklist as a table — DECISION.md is assembled from it."""
    rows = ["| Situation | Answer | Why |", "|---|---|---|"]
    rows += [f"| {s.name} | **{decide(s.signals).answer}** | {s.why} |" for s in SITUATIONS]
    return "\n".join(rows)


if __name__ == "__main__":
    print(table())
