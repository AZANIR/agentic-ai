"""Вимір складання: скільки рядків кожного етапу виконалось на один запит (ADR-0001).

Найочевидніший доказ тези «капстоун збирає етапи 1–9» — перелік імпортів. Він не працює, і
причина заміряна:

    етап 6 імпортує `from stages.s02_rag.documents import PUBLIC`
    і виконує з етапу 2 РІВНО НУЛЬ рядків

`PUBLIC` — константа рівня доступу, яка їде далі як аргумент. Пошук, ембеддинги, фільтр
доступу не працюють ніколи. У переліку імпортів етап 2 присутній; у роботі його немає.

> **«Імпортує» — не те саме, що «використовує».**

Тому доказ тут — **виконані рядки**, згруповані за етапом. Етап, названий частиною складання
й такий, що дає нуль, червонить перевірку.

**Інструмент береться з етапу 9** (ADR-0002), а не пишеться заново: два визначення слова
«виконано» зробили б числа двох етапів непорівнянними. Разом з інструментом успадковані його
межі — число описує **цей запит** і **цей потік**.
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from stages.s09_frameworks.counters import executed_lines
from stages.s10_capstone import seams

HERE = Path(__file__).resolve().parent
STAGES = HERE.parent
SEAMS = HERE / "seams.py"

# Етапи, які капстоун оголошує частинами складання. Кожен мусить дати ненульове число.
PARTS: tuple[str, ...] = ("s01", "s02", "s03", "s05", "s06", "s08")

# Етапи, свідомо не ввімкнені. Нуль для них — рішення, а не помилка (ADR-0008).
NOT_WIRED: dict[str, str] = {
    "s04": "інструменти MCP потребують піднятого сервера; сервіс бере інструменти етапу 1",
    "s07": "голос не додає нового висновку, а додає залежність на гігабайти",
    "s09": (
        "етап 9 тут — ПРИЛАД, а не спосіб оркестрації: капстоун бере з нього лічильник "
        "виконаних рядків і координує сам. Числа він давав, але вони міряли самих себе: "
        "`measure(lambda: None)` показував `s09: 1`, і той рядок — вимикання трасування "
        "у `finally` лічильника"
    ),
}

# Модулі капстоуна. `run.py` і `check.py` не рахуються — як на етапах 8 і 9.
OWN: tuple[str, ...] = (
    "seams.py",
    "assemble.py",
    "service.py",
    "scenarios.py",
    "arch.py",
    "latency.py",
)


@dataclass
class Assembly:
    """Що дав вимір: виконане по етапах і ціна перехідників.

    `adapters` і `executed` — **в одній одиниці**: виконані рядки, той самий прилад. Ціна,
    порахована статично, поруч із виконаним лічила б «є в коді» проти «працює» — рівно ту
    підміну, яку цей етап і викриває. `written` лишається окремо, щоб різницю було видно.
    """

    executed: dict[str, int] = field(default_factory=dict)
    adapters: int = 0
    written: int = 0

    @property
    def worked(self) -> int:
        """Скільки рядків етапів виконалось усього."""
        return sum(self.executed.values())

    @property
    def silent(self) -> list[str]:
        """Оголошені частини, що не виконали жодного рядка. Порожньо — усі працюють."""
        return sorted(name for name in PARTS if not self.executed.get(name))

    @property
    def ratio(self) -> float:
        """Ціна складання: перехідники на одиницю виконаного."""
        return self.adapters / self.worked if self.worked else 0.0

    def line(self) -> str:
        return (
            f"виконано {self.worked} рядків етапів, перехідників {self.adapters} "
            f"з {self.written} написаних ({self.ratio:.0%}); мовчать: {self.silent or 'жоден'}"
        )


def _package(name: str) -> str:
    """Повне ім'я пакета етапу за коротким: `s01` -> `stages.s01_agent_loop`."""
    found = sorted(STAGES.glob(f"{name}_*"))
    return f"stages.{found[0].name}" if found else ""


def executable_lines(name: str) -> int:
    """Виконувані рядки модуля капстоуна: без імпортів і рядків документації.

    Та сама одиниця й той самий спосіб, що на етапах 8 і 9 — інакше «перехідники» й
    «виконане» були б у різних одиницях і виглядали б порівнянними.
    """
    tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
    return len(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.stmt)
            and not isinstance(node, (ast.Import, ast.ImportFrom))
            and not (
                isinstance(node, ast.Expr) and isinstance(getattr(node.value, "value", None), str)
            )
        }
    )


def adapter_statement_lines() -> set[int]:
    """Номери виконуваних рядків самих перехідників у `seams.py`.

    Рахуються **тільки** функції, названі в `seams.ADAPTERS`. Увесь `seams.py` включив би
    оголошення швів — тобто прозу про ціну — у саму ціну.

    Одна множина на обидва числа: скільки написано (її розмір) і скільки виконалось (її
    перетин із трасою). Два різні визначення дали б «виконано більше, ніж написано» — і
    саме це й трапилось у першій редакції, де виконане брали за рядковими межами функції.
    """
    tree = ast.parse(SEAMS.read_text(encoding="utf-8"))
    wanted = {function.__name__ for function in seams.ADAPTERS.values()}
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in wanted):
            continue
        lines |= {
            inner.lineno
            for inner in ast.walk(node)
            if isinstance(inner, ast.stmt)
            and not isinstance(inner, (ast.Import, ast.ImportFrom, ast.FunctionDef))
            and not (
                isinstance(inner, ast.Expr) and isinstance(getattr(inner.value, "value", None), str)
            )
        }
    return lines


def _adapters_executed(seen: set[tuple[str, int]]) -> int:
    """Скільки рядків перехідників ВИКОНАЛОСЬ. Та сама одиниця, що й у етапів.

    Різниця з написаним не є похибкою й показова сама по собі: `build_search` працює на
    старті сервісу, а не на запиті, тож у ціну ОДНОГО запиту він не входить зовсім.
    """
    wanted = adapter_statement_lines()
    return sum(
        1 for filename, lineno in seen if lineno in wanted and Path(filename).resolve() == SEAMS
    )


def adapter_lines() -> int:
    """Скільки рядків перехідників НАПИСАНО. Друга половина порівняння з виконаним."""
    return len(adapter_statement_lines())


@contextmanager
def watching() -> Iterator[set[tuple[str, int]]]:
    """Трасувати виконані рядки **всіх** етапів одним проходом.

    Один прохід, а не контекст на етап. Перша редакція відкривала `executed_lines` окремо
    для кожного з семи — і міряла нуль для шести: `sys.settrace` глобальний **на потік**,
    тож кожен наступний контекст затирав попередній, і активним лишався останній.

    Симптом був тихий і правдоподібний: таблиця друкувалась, числа були цілі, і лише
    останній етап мав ненульове. Розкладання шляхів по етапах робиться **після** виміру.
    """
    packages = [package for name in PARTS if (package := _package(name))]
    # Разом із етапами трасується сам капстоун: без цього рядки перехідників у виміряному
    # не з'являться взагалі, і ціну довелося б рахувати іншим приладом — тобто в іншій одиниці.
    with executed_lines(*packages, __package__ or "stages.s10_capstone") as seen:
        yield seen


def _by_stage(seen: set[tuple[str, int]]) -> dict[str, int]:
    """Розкласти виконані рядки по етапах за шляхом файлу."""
    counted = dict.fromkeys(PARTS, 0)
    folders = {name: _folder(name) for name in PARTS}
    for filename, _lineno in seen:
        parts = Path(filename).parts
        for name, folder in folders.items():
            if folder and folder in parts:
                counted[name] += 1
                break
    return counted


def _folder(name: str) -> str:
    """Імʼя теки етапу за коротким іменем: `s01` -> `s01_agent_loop`."""
    found = sorted(STAGES.glob(f"{name}_*"))
    return found[0].name if found else ""


def measure(work: Callable[[], Any]) -> Assembly:
    """Прогнати роботу під трасуванням і зібрати числа.

    **Прогрів обовʼязковий.** Перший прогін у процесі виконує ще й рядки імпорту пакета —
    етап 9 заміряв там різницю всемеро. Імпорт трапляється раз на процес, а не раз на
    запит, тож у ціну прогону він не входить.
    """
    work()
    with watching() as seen:
        work()
    return Assembly(
        executed=_by_stage(seen),
        adapters=_adapters_executed(seen),
        written=adapter_lines(),
    )
