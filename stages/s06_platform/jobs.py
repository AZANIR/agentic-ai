"""Періодична задача — і пастка, заради якої існує половина цього етапу.

Задача проста: раз на добу прибрати протухле й звести витрати. Бібліотека планувальника вміє
запускатись **усередині застосунку** двома рядками, і саме так написано в більшості прикладів:

    scheduler = BackgroundScheduler()
    scheduler.add_job(cleanup, "interval", hours=24)

З одним воркером це працює. З двома — планувальників стає **два**, і задача виконується двічі
за інтервал. Помилки немає ніде: обидва процеси праві, кожен знає лише про себе.

**Чому це та сама вада, що з лічильниками.** Стан у пам'яті процесу перестає бути правдою,
щойно процесів більше одного. Планувальник — це стан «коли востаннє виконували», лічильник —
стан «скільки вже було». Причина одна, обличчя різні:

    планувальник   задача двічі        видно в логах — якщо туди дивитись
    лічильник      ліміт удвічі        не видно НІДЕ: сервіс поводиться нормально
    метрики        зріз одного воркера  не видно, доки числа не почнуть «майже сходитись»

**Друга половина важливіша за першу.** Подвоєну задачу помічають; подвоєний ліміт означає, що
межа тихо стала іншою.

**Пастка лишається під прапорцем, а не в коментарі** (ADR-0003). Вправа вмикає планувальник
усередині застосунку, читач бачить у власному логу число «2», вимикає прапорець і бачить «1».
Вада, описана прозою, не запам'ятовується.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

INSIDE = "inside-the-app"
SEPARATE = "separate-process"


@dataclass
class Ledger:
    """Скільки разів задача виконалась. Спільний на всі «воркери» — як справжній лог."""

    runs: list[str] = field(default_factory=list)

    def record(self, worker: str) -> None:
        self.runs.append(worker)

    def count(self) -> int:
        return len(self.runs)


@dataclass
class Worker:
    """Один процес сервісу. Знає лише про себе — і саме в цьому вся справа."""

    name: str
    ledger: Ledger
    mode: str = SEPARATE

    def tick(self, *, now: float, due_at: float) -> bool:
        """Настав час задачі. Повертає, чи цей воркер її виконав.

        У режимі `SEPARATE` воркер задачі не виконує взагалі: розклад живе в окремому
        процесі, і воркери про час не знають. У режимі `INSIDE` виконує кожен — бо кожен
        має власний планувальник і власну відповідь на питання «чи вже час».
        """
        if self.mode != INSIDE or now < due_at:
            return False
        self.ledger.record(self.name)
        return True


@dataclass
class Scheduler:
    """Планувальник окремим процесом. Рівно один екземпляр на розгортання."""

    ledger: Ledger
    name: str = "scheduler"

    def tick(self, *, now: float, due_at: float) -> bool:
        if now < due_at:
            return False
        self.ledger.record(self.name)
        return True


def run_interval(
    workers: list[Worker], scheduler: Scheduler | None, *, now: float, due_at: float
) -> int:
    """Один інтервал: усі воркери й планувальник дізнаються, що час настав.

    :returns: скільки разів задача виконалась. Число — і є урок.
    """
    for worker in workers:
        worker.tick(now=now, due_at=due_at)
    if scheduler is not None:
        scheduler.tick(now=now, due_at=due_at)
    return workers[0].ledger.count() if workers else 0


def cleanup(store: Any, *, now: float) -> int:
    """Сама задача: прибрати протухле. Ідемпотентна навмисно — але це не рятує.

    Прибирання, виконане двічі, справді нешкідливе. Небезпеку створює **не** ця задача, а
    правило «двічі — це нормально»: наступна задача в цьому ж планувальнику надішле лист,
    спише гроші або зробить резервну копію поверх свіжої. Ідемпотентність тут — властивість
    однієї функції, а не властивість механізму.
    """
    from stages.s05_memory.facts import is_active

    facts = store.all_facts()
    return sum(1 for fact in facts if not is_active(fact, now=now))
