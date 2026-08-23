"""Той самий граф на LangGraph. Друга реалізація тієї самої задачі, не заміна першій.

    pip install -e ".[s03]"

Модуль **необов'язковий**: без встановленої бібліотеки етап проходиться до кінця, а перевірка
маршрутів чесно каже, що її не виконано (NFR-5). Різниця між «збіглося» і «не перевіряли»
має бути видимою — інакше зелений набір означає менше, ніж здається.

Читати цей файл варто **після** `graph.py`, і саме заради впізнавання: тут ті самі частини під
іншими назвами.

    наш словник спеціалістів   ->  add_node на кожного
    наш if choice not in ...   ->  add_conditional_edges
    наш while з лічильником    ->  ребро, що повертається у вузол
    наш state.finish_reason    ->  END

Що LangGraph дає натомість: паралельні гілки, чекпоінти, стрімінг проміжних кроків, готову
візуалізацію. Нічого з цього на етапі 3 не потрібно — і в цьому весь сенс порівняння: платити
залежністю варто за те, чим користуєшся.

**Одна розбіжність варта окремої уваги.** Стан LangGraph — це `TypedDict`, тобто словник:
`state["typo"]` поверне `KeyError` під час виконання, а `state.get("typo")` — мовчазний `None`.
Наш `state.py` навмисно робить інакше (ADR етапу 0002). Це не вада бібліотеки: вона обирає
гнучкість, бо не знає наперед, які вузли ти додаси. Ціна цієї гнучкості — та сама, про яку
каже ADR, і побачити її поруч корисніше, ніж прочитати про неї.
"""

from __future__ import annotations

from typing import Any, TypedDict

from stages.s03_router.graph import (
    NO_SPECIALIST,
    SUPERVISOR,
    _ask,
    route_prompt,
)
from stages.s03_router.specialists import SPECIALISTS, safely
from stages.s03_router.state import State


class Carried(TypedDict, total=False):
    """Те, що LangGraph переносить між вузлами. Наш State їде всередині як значення."""

    state: State
    client: Any
    model: str | None
    choice: str


def available() -> bool:
    """Чи можна побудувати граф. Викликається перед усім, що торкається бібліотеки."""
    try:
        import langgraph.graph  # noqa: F401
    except ImportError:
        return False
    return True


def _supervisor(carried: Carried) -> Carried:
    state = carried["state"]
    state.visit(SUPERVISOR)
    choice = _ask(carried["client"], route_prompt(state), carried.get("model"))
    return {**carried, "choice": choice if choice in SPECIALISTS else NO_SPECIALIST}


def _specialist(carried: Carried) -> Carried:
    state, choice = carried["state"], carried["choice"]
    answer = safely(SPECIALISTS[choice], state)
    state.handoffs += 1
    state.visit(choice)
    if answer.error:
        state.error = answer.error
        state.finish_reason = "specialist_failed"
    else:
        state.answer = answer.text
        state.sources = answer.sources
        state.finish_reason = "answered"
    return carried


def _refuse(carried: Carried) -> Carried:
    state = carried["state"]
    state.answer = "Не маю спеціаліста для цього запиту. Доступні компетенції: " + ", ".join(
        SPECIALISTS
    )
    state.finish_reason = "no_specialist"
    return carried


def build() -> Any:
    """Скласти граф. Три вузли, одне умовне ребро — рівно те саме, що в `graph.py`."""
    from langgraph.graph import END, StateGraph

    builder = StateGraph(Carried)
    builder.add_node(SUPERVISOR, _supervisor)
    builder.add_node("specialist", _specialist)
    builder.add_node("refuse", _refuse)
    builder.set_entry_point(SUPERVISOR)
    builder.add_conditional_edges(
        SUPERVISOR,
        lambda carried: "refuse" if carried["choice"] == NO_SPECIALIST else "specialist",
        {"specialist": "specialist", "refuse": "refuse"},
    )
    builder.add_edge("specialist", END)
    builder.add_edge("refuse", END)
    return builder.compile()


def run_graph(
    query: str,
    *,
    access: str,
    client: Any,
    revision_limit: int = 2,
    model: str | None = None,
) -> State:
    """Той самий підпис, що у власного графа, — щоб порівняння було можливим."""
    state = State(query=query, access=access, revision_limit=revision_limit)
    build().invoke({"state": state, "client": client, "model": model})
    return state
