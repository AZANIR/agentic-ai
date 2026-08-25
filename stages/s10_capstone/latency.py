"""Затримка зібраного сервісу — і умови, за яких вона заміряна (ADR-0007).

Число без умов не є виміром. Етап 7 показав це на затримці голосу: числа були правильні, а
умови — ні, і читач переносив їх туди, де вони не діяли.

Тому умови тут — **дані**, а не примітка в прозі, і друкуються вони **перед** числом.
Перевірка стверджує саме цей порядок: припис, який ніхто не виконує, тримається рівно доти,
доки про нього хтось пам'ятає.

**Чого цей вимір не є.** Це не навантажувальний прогін і не характеристика продакшну:
модель підроблена, сервіс у тому самому процесі, машина одна. Справжні числа дає
`deploy/smoke.sh` проти піднятого сервісу, і в CI вони лишаються `НЕ ПЕРЕВІРЕНО`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

RUNS = 20

# Умови виміру. Кожна з них міняє число, і кожна названа до того, як число прозвучало.
CONDITIONS: tuple[str, ...] = (
    f"{RUNS} запитів поспіль",
    "підроблена модель (без мережі й без ключа)",
    "сервіс у тому самому процесі, без HTTP",
    "одна машина, без паралельного навантаження",
)

QUESTION = "Скільки днів на повернення товару?"


@dataclass(frozen=True)
class Took:
    """Заміряна затримка. `runs` — скільки запитів стоїть за числами."""

    runs: int
    p50: float
    p95: float
    slowest: float


def measure(service: Any, *, runs: int = RUNS) -> Took:
    """Прогнати `runs` однакових запитів і взяти процентилі.

    Питання одне навмисно: різні питання йдуть різними гілками, і змішані числа описували
    б не затримку сервісу, а склад набору питань.
    """
    from stages.s10_capstone import scenarios  # noqa: PLC0415

    marks = []
    for _ in range(runs):
        started = time.perf_counter()
        service.ask(scenarios.KEY, QUESTION, now=scenarios.NOW)
        marks.append((time.perf_counter() - started) * 1000)

    marks.sort()
    return Took(
        runs=runs,
        p50=marks[len(marks) // 2],
        p95=marks[min(len(marks) - 1, int(len(marks) * 0.95))],
        slowest=marks[-1],
    )


def report(took: Took) -> None:
    """Надрукувати умови, а **потім** числа. Порядок — частина твердження."""
    for condition in CONDITIONS:
        print(f"   · {condition}")
    print()
    print(
        f"   p50 {took.p50:.1f} мс   p95 {took.p95:.1f} мс   найповільніший {took.slowest:.1f} мс"
    )
