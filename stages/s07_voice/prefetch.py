"""Ранній виклик інструмента — з **обома** числами: купленим і змарнованим.

Повільний інструмент у голосі коштує дорого: людина чекає мовчки. Очевидна відповідь —
покликати його раніше, доки модель ще формулює відповідь.

Так само очевидно, що стаття про prefetch, яка закінчується словом «швидше», дає читачеві
оптимізацію без умов її застосування.

**Prefetch виконує виклик, який може не знадобитись.** Це запит до чужої системи, місце в
черзі, іноді гроші. Тому етап показує обидва числа, і рішення лишається читачеві (ADR-0005).

**Інструмент тут свідомо read-only.** Відкинутий виклик, що змінює стан, перетворив би
prefetch із оптимізації на пастку.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from stages.s07_voice.clock import Clock

WASTED = "марна робота"


@dataclass
class Outcome:
    """Що дав прогін: скільки тривав і чи знадобився ранній виклик."""

    millis: float
    used: bool
    note: str = ""


def synchronous(tool: Any, *, clock: Clock, needed: bool, tool_millis: float) -> Outcome:
    """Спершу думати, потім кликати. Затримка інструмента додається до відповіді."""
    start = clock.now()
    if needed:
        clock.sleep(tool_millis)
        tool()
    return Outcome(millis=clock.now() - start, used=needed)


def prefetched(
    tool: Any, *, clock: Clock, needed: bool, tool_millis: float, think_millis: float
) -> Outcome:
    """Кликати одразу, паралельно з роздумом. Купує рівно перекриття двох затримок.

    Модель підроблена: обидві затримки «йдуть одночасно», тож вартість — максимум із них,
    а не сума. Саме це перекриття prefetch і купує.
    """
    start = clock.now()
    tool()
    clock.sleep(max(tool_millis, think_millis))
    outcome = Outcome(millis=clock.now() - start, used=needed)
    if not needed:
        # Виклик відбувся й результат нікому не потрібен. Це не помилка — це ціна, і вона
        # має бути названа, інакше етап продає prefetch замість пояснювати його.
        outcome.note = f"{WASTED}: інструмент викликано, результат відкинуто"
    return outcome
