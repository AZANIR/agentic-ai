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

# Етапи, які капстоун оголошує частинами складання. Кожен мусить дати ненульове число.
PARTS: tuple[str, ...] = ("s01", "s02", "s03", "s05", "s06", "s08", "s09")

# Етапи, свідомо не ввімкнені. Нуль для них — рішення, а не помилка (ADR-0008).
NOT_WIRED: dict[str, str] = {
    "s04": "інструменти MCP потребують піднятого сервера; сервіс бере інструменти етапу 1",
    "s07": "голос не додає нового висновку, а додає залежність на гігабайти",
}

# Модулі капстоуна. `run.py` і `check.py` не рахуються — як на етапах 8 і 9.
OWN: tuple[str, ...] = ("seams.py", "assemble.py", "service.py", "scenarios.py", "arch.py")


@dataclass
class Assembly:
    """Що дав вимір: виконане по етапах і ціна перехідників."""

    executed: dict[str, int] = field(default_factory=dict)
    adapters: int = 0

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
            f"({self.ratio:.0%}); мовчать: {self.silent or 'жоден'}"
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


def adapter_lines() -> int:
    """Ціна складання: виконувані рядки самих перехідників, без решти капстоуна.

    Рахуються **тільки** функції, названі в `seams.ADAPTERS`. Увесь `seams.py` включив би
    оголошення швів — тобто прозу про ціну — у саму ціну.
    """
    tree = ast.parse((HERE / "seams.py").read_text(encoding="utf-8"))
    wanted = {function.__name__ for function in seams.ADAPTERS.values()}
    total = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in wanted:
            total += len(
                {
                    inner.lineno
                    for inner in ast.walk(node)
                    if isinstance(inner, ast.stmt)
                    and not isinstance(inner, (ast.Import, ast.ImportFrom, ast.FunctionDef))
                    and not (
                        isinstance(inner, ast.Expr)
                        and isinstance(getattr(inner.value, "value", None), str)
                    )
                }
            )
    return total


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
    with executed_lines(*packages) as seen:
        yield seen


def _by_stage(seen: set[tuple[str, int]]) -> dict[str, int]:
    """Розкласти виконані рядки по етапах за шляхом файлу."""
    counted = dict.fromkeys(PARTS, 0)
    for filename, _lineno in seen:
        parts = Path(filename).parts
        for name in PARTS:
            folder = _folder(name)
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
    return Assembly(executed=_by_stage(seen), adapters=adapter_lines())
