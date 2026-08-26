"""The "what to remember at all" checklist — and why its value is in the order, not the rules.

The simplest memory stores everything the user said. It works for one day: after that retrieval
returns four facts about the same thing, contradictions accumulate faster than facts, and the
answer slowly degrades. So the "remember this?" decision is made **before** the write, and it is
made the same way every time — otherwise memory depends on whoever wrote the call site.

**What the code actually does here.** Not classification: whether a line is a secret is decided
by a human or a model, and no heuristic here replaces that. The code holds the **order** of the
questions and the rule "the first one to fire is the answer". That is not a trifle: `"remember my
password"` is a secret and a direct request at once, and the answer depends exclusively on which
question comes first. The order is the checklist; the rules apart from it are worth nothing.

**Why "no rule without a situation" is a requirement of its own.** A rule that no situation
triggers looks like work and does nothing. Such a checklist passes any check of the form "every
situation has an answer" — and silently loses half its meaning. So the check runs **both ways**,
like the owner filter in `long_term`: every situation has a rule **and** every rule has a
situation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Situation:
    """A line already described by properties. A human classifies — the checklist only orders."""

    text: str
    secret: bool = False
    asked: bool = False
    about_world: bool = False
    derivable: bool = False
    durable: bool = False


@dataclass(frozen=True)
class Rule:
    """One question of the checklist. `keep` is the answer if this one fired first."""

    question: str
    keep: bool
    why: str
    applies: Callable[[Situation], bool]


@dataclass(frozen=True)
class Decision:
    """An answer with the name of the rule: "did not remember" without a reason is just a loss."""

    keep: bool
    rule: str
    why: str


# The order is the checklist. The secret stands before the request deliberately: "remember my
# password" has to give "no", and no other arrangement gives that.
RULES: tuple[Rule, ...] = (
    Rule(
        question="Is this a secret, or something that must not be stored?",
        keep=False,
        why="secrets are not stored even on a direct request",
        applies=lambda s: s.secret,
    ),
    Rule(
        question="Is this about the world rather than about the person?",
        keep=False,
        why="knowledge about the world lives in search (stage 2), not in memory",
        applies=lambda s: s.about_world,
    ),
    Rule(
        question="Is this derivable from what is already stored?",
        keep=False,
        why="a derived fact adds volume and a reason for contradiction",
        applies=lambda s: s.derivable,
    ),
    Rule(
        question="Did the person directly ask to remember it?",
        keep=True,
        why="a direct request is the strongest signal we have",
        applies=lambda s: s.asked,
    ),
    Rule(
        question="Is this a property that will outlive this conversation?",
        keep=True,
        why="facts like these are what make the second session different from the first",
        applies=lambda s: s.durable,
    ),
    Rule(
        question="Everything else",
        keep=False,
        why="a one-off is not remembered — it is simply used and forgotten",
        applies=lambda s: True,
    ),
)


def decide(situation: Situation) -> Decision:
    """The first rule that fires is the answer. The last one always fires."""
    for rule in RULES:
        if rule.applies(situation):
            return Decision(keep=rule.keep, rule=rule.question, why=rule.why)
    raise AssertionError("the last rule has to catch everything — the checklist is broken")
