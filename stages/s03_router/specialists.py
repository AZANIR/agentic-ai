"""Три вузькі компетенції. Кожна — вже написаний код, а не новий.

У цьому й теза етапу: **supervisor складається з наявного**. Спеціаліст замовлень — це цикл
етапу 1 із його реєстром і трьома захистами. Спеціаліст знань — пошук етапу 2 з фільтром
доступу. Третій, найпростіший, доданий тут: без нього маршрутів було б два, і маршрутизація
виродилась би в «або-або».

**Опис компетенції важливіший за назву вузла.** Маршрут обирає модель, і обирає вона за
описом: `orders` їй нічого не каже, а «статус замовлення, повернення, оформлення» — каже. Тому
опис — обов'язкове поле, і перевірка вимагає, щоб він був довшим за назву.

**Рівень доступу спеціаліст бере зі стану, не з аргументів.** Це ADR етапу 0003, і практична
причина проста: аргумент можна забути, додаючи четвертого спеціаліста, а поле стану — ні. Тут
видно, як воно доїжджає: `state.access` іде прямо в пошук етапу 2.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from shared.trace import trace_run
from stages.s01_agent_loop.loop import run_agent
from stages.s02_rag.answer import build_answer
from stages.s02_rag.tools import knowledge_base
from stages.s03_router.state import State, StateFieldError

_NUMBER = re.compile(r"-?\d+(?:[.,]\d+)?")


@dataclass
class Answer:
    """Що спеціаліст повернув supervisor'у. Порожній текст із помилкою — теж результат."""

    text: str = ""
    sources: list[str] = field(default_factory=list)
    steps: int = 0
    error: str | None = None


@dataclass(frozen=True)
class Specialist:
    """Вузька компетенція: як вона називається, що вміє, і чим це робить."""

    name: str
    competence: str
    handle: Callable[..., Answer]


def _orders(state: State, *, client: Any = None, tracer: Any = None) -> Answer:
    """Замовлення: цикл етапу 1 без жодної зміни в ньому.

    Трейсер приходить від графа, а не створюється тут. Перша версія писала кроки циклу
    у тимчасову теку й губила їх: у трейсі прогону не було жодного `tool_call`, хоча
    демо обіцяє, що ці трейси читатиме етап 8.
    """
    from shared.fake_llm import text as scripted
    from shared.llm import get_client

    client = client or get_client(demo_script=[scripted("Не маю чим підтвердити.")])
    if tracer is not None:
        result = run_agent(state.query, client=client, tracer=tracer)
    else:
        with TemporaryDirectory() as tmp:
            with trace_run("specialist", path=Path(tmp) / "t.jsonl", stage="s03") as own:
                result = run_agent(state.query, client=client, tracer=own)
    return Answer(text=result.answer or "", steps=result.steps)


def _knowledge(state: State, **_: Any) -> Answer:
    """Знання: пошук етапу 2 з рівнем доступу, взятим зі стану."""
    found = knowledge_base().search(state.query, access=state.access, top_k=3)
    built = build_answer(state.query, found, model_text=_join(found))
    return Answer(text=built.text, sources=built.sources, steps=1)


def _join(found: Any) -> str:
    """Текст із знайденого. Справжня модель приходить сюди на етапі 6; тут — склейка."""
    return " ".join(hit.fragment.text for hit in found.hits)


def _math(state: State, **_: Any) -> Answer:
    """Підрахунки: сума чисел із запиту. Навмисно примітивно — суть у маршруті, не в математиці."""
    numbers = [float(n.replace(",", ".")) for n in _NUMBER.findall(state.query)]
    if not numbers:
        return Answer(text="У запиті немає чисел, які можна скласти.", steps=1)
    total = sum(numbers)
    parts = " + ".join(f"{n:g}" for n in numbers)
    return Answer(text=f"{parts} = {total:g}", steps=1)


SPECIALISTS: dict[str, Specialist] = {
    "orders": Specialist(
        name="orders",
        competence=(
            "Статус конкретного замовлення за його номером, оформлення повернення, "
            "перевірка, що з посилкою. Потрібен номер замовлення."
        ),
        handle=_orders,
    ),
    "knowledge": Specialist(
        name="knowledge",
        competence=(
            "Правила магазину й опис товарів: строки повернення, умови доставки, "
            "з чого зроблений товар. Відповідає за документами, не за номером замовлення."
        ),
        handle=_knowledge,
    ),
    "math": Specialist(
        name="math",
        competence=(
            "Підрахунки за числами із самого запиту: скласти суми, порахувати підсумок. "
            "Не звертається ні до замовлень, ні до документів."
        ),
        handle=_math,
    ),
}


def catalogue() -> str:
    """Перелік компетенцій у тому вигляді, у якому його бачить модель."""
    return "\n".join(f"- {s.name}: {s.competence}" for s in SPECIALISTS.values())


def safely(specialist: Specialist, state: State, **kwargs: Any) -> Answer:
    """Викликати спеціаліста так, щоб його виняток не вбив граф.

    Виняток спеціаліста — **подія середовища**, а не поламаний контракт: склад може бути
    недоступний, файл зіпсований, мережа мовчить. Такий випадок стає результатом кроку, і
    supervisor вирішує далі сам.

    Помилку схеми стану ця функція **не ловить** навмисно: `StateFieldError` означає, що
    контракт зламано, і продовжувати роботу на порожньому значенні — гірше, ніж упасти.
    """
    try:
        return specialist.handle(state, **kwargs)
    except StateFieldError as error:
        # Контракт зламано. Додаємо ім'я вузла й летимо далі: підміняти це на «подію
        # середовища» означало б продовжити роботу на порожньому значенні (AC-02b).
        raise StateFieldError(f"вузол {specialist.name!r}: {error}") from error
    except Exception as error:  # noqa: BLE001 — саме широкий перехват і є суттю функції
        return Answer(error=f"спеціаліст {specialist.name!r} зламався: {error}")
