"""Supervisor: маршрут, передача, цикл ревізій. Увесь граф — один екран.

Прочитавши цей файл, важко не помітити головного: **тут немає нічого нового**. Словник
спеціалістів, виклик моделі, `while` із лічильником — усе це вже було на етапі 1, просто за
назвою інструмента тепер стоїть агент, а не функція. Саме тому етап починається зі свого
графа, а не з бібліотеки: у шістдесяти рядках видно, що магії немає (ADR етапу 0001).

Три речі, які варто прочитати повільно:

**Маршрут обирає модель, а граф його перевіряє.** Модель може назвати вузол, якого немає, — і
назве, рано чи пізно. Тому назва звіряється з реєстром, а не використовується як є; вигадана
назва означає «спеціаліста немає», а не помилку виконання (ADR етапу 0004).

**Цикл ревізій має лічильник, і лічильник живе у стані.** Без нього supervisor, якому
відповідь не подобається, повертатиме задачу нескінченно — і кожне коло коштує грошей. Це
той самий захист, що ліміт кроків на етапі 1, у тому самому місці: до дії, не після.

**Виняток спеціаліста й поламаний контракт — різні події.** Перше стає результатом кроку:
склад може бути недоступний, і граф має це пережити. Друге (`StateFieldError`) валить прогін
одразу, бо продовжувати роботу на порожньому значенні гірше, ніж упасти.
"""

from __future__ import annotations

from typing import Any

from shared.llm import get_model
from stages.s03_router.specialists import SPECIALISTS, catalogue, safely
from stages.s03_router.state import State

SUPERVISOR = "supervisor"
NO_SPECIALIST = "none"
FINISH_REASONS = ("answered", "no_specialist", "revision_limit", "specialist_failed")

_ROUTE = """Ти диспетчер підтримки NovaShop. Обери, кому віддати запит.

Доступні спеціалісти:
{catalogue}

Запит: {query}

Відповідай ОДНИМ словом — назвою спеціаліста або {none}, якщо не підходить жоден."""

_JUDGE = """Запит: {query}
Відповідь спеціаліста: {answer}

Ця відповідь закриває запит? Відповідай одним словом: ok або мало."""


def route_prompt(state: State) -> str:
    """Промпт вибору маршруту. Окремою функцією, щоб перевірка бачила те саме, що модель."""
    return _ROUTE.format(catalogue=catalogue(), query=state.query, none=NO_SPECIALIST)


def _ask(client: Any, prompt: str, model: str | None) -> str:
    reply = client.chat.completions.create(
        model=model or get_model(), messages=[{"role": "user", "content": prompt}]
    )
    return (reply.choices[0].message.content or "").strip().lower()


def _refuse(state: State) -> State:
    """Компетенції немає. Чесна відмова з переліком — і жодного виклику спеціаліста."""
    state.answer = "Не маю спеціаліста для цього запиту. Доступні компетенції: " + ", ".join(
        SPECIALISTS
    )
    state.finish_reason = "no_specialist"
    return state


def run_graph(
    query: str,
    *,
    access: str,
    client: Any,
    tracer: Any,
    revision_limit: int = 2,
    model: str | None = None,
) -> State:
    """Прогнати запит графом і повернути стан — із маршрутом, лічильниками й причиною."""
    state = State(query=query, access=access, revision_limit=revision_limit)
    state.visit(SUPERVISOR)

    choice = _ask(client, route_prompt(state), model)
    tracer.step("route", chosen=choice, known=choice in SPECIALISTS)
    if choice not in SPECIALISTS:
        # Вигадана назва — це «немає спеціаліста», а не помилка. Модель має право помилитись;
        # граф не має права їй повірити на слово.
        return _refuse(state)

    specialist = SPECIALISTS[choice]
    while True:
        answer = safely(specialist, state)
        state.handoffs += 1
        state.visit(choice)

        if answer.error:
            state.error = answer.error
            state.finish_reason = "specialist_failed"
            tracer.step("specialist_failed", node=choice, error=answer.error)
            return state

        verdict = _ask(client, _JUDGE.format(query=state.query, answer=answer.text), model)
        tracer.step("judge", node=choice, verdict=verdict, revisions=state.revisions)
        if verdict.startswith("ok"):
            state.answer = answer.text
            state.sources = answer.sources
            state.finish_reason = "answered"
            return state

        if state.revisions >= state.revision_limit:
            state.finish_reason = "revision_limit"
            tracer.step("revision_limit", node=choice, revisions=state.revisions)
            return state

        state.revisions += 1
        tracer.step("revision", node=choice, revisions=state.revisions)
