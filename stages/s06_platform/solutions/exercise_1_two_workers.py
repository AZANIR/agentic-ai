"""Два воркери поруч на одних даних — три обличчя однієї причини.

    python -m stages.s06_platform.solutions.exercise_1_two_workers

Червона перевірка каже «другий екземпляр бачить не те число». Вона не показує, **як саме** це
виглядає з боку клієнта, і саме тому вправа 1 найважливіша й найменш переконлива: код
працює, відмови приходять, метрики рахуються.

Тут три механізми поставлені поруч на однакових даних, і різниця — числом.
"""

from __future__ import annotations

from dataclasses import dataclass

from shared.config import Settings
from shared.counters import InMemory, Shared
from stages.s06_platform.fake_store import FakeStore
from stages.s06_platform.guards import admit
from stages.s06_platform.jobs import INSIDE, SEPARATE, Ledger, Scheduler, Worker, run_interval
from stages.s06_platform.observe import Metrics

NOW = 1_700_000_000.0
KEY = "solution-key"
LIMIT = 3
REQUESTS = 12


@dataclass
class Result:
    name: str
    number: int
    note: str


def process_local_counters() -> Result:
    """Профіль local: у кожного воркера власний лічильник."""
    settings = Settings(api_keys=[KEY], rate_limit_per_minute=LIMIT)
    workers = [InMemory(), InMemory()]
    passed = sum(
        1 for i in range(REQUESTS) if admit(KEY, workers[i % 2], settings, now=NOW).allowed
    )
    return Result("лічильник у процесі", passed, "межа означає вдвічі більше")


def shared_counters() -> Result:
    """Профіль prod: один лічильник на всіх."""
    settings = Settings(api_keys=[KEY], rate_limit_per_minute=LIMIT)
    data: dict[str, dict[str, float]] = {}
    workers = [Shared(FakeStore(data)), Shared(FakeStore(data))]
    passed = sum(
        1 for i in range(REQUESTS) if admit(KEY, workers[i % 2], settings, now=NOW).allowed
    )
    return Result("лічильник спільний", passed, "межа означає те, що написано")


def scheduler_inside() -> Result:
    ledger = Ledger()
    run_interval(
        [Worker(f"worker-{i}", ledger, INSIDE) for i in range(2)], None, now=NOW, due_at=NOW
    )
    return Result("планувальник усередині", ledger.count(), "видно в логах")


def scheduler_outside() -> Result:
    ledger = Ledger()
    run_interval(
        [Worker(f"worker-{i}", ledger, SEPARATE) for i in range(2)],
        Scheduler(ledger=ledger),
        now=NOW,
        due_at=NOW,
    )
    return Result("планувальник окремо", ledger.count(), "виправлено")


def metrics_per_process() -> Result:
    """Третє обличчя: збирач метрик теж процесо-локальний."""
    workers = [Metrics(), Metrics()]
    for i in range(REQUESTS):
        workers[i % 2].request("ok")
    # Монітор питає **один** воркер — той, до якого потрапив запит через проксі.
    return Result("метрики одного воркера", workers[0].requests["ok"], f"а сталося {REQUESTS}")


def main() -> int:
    print(f"Запитів: {REQUESTS}, межа ліміту: {LIMIT}, воркерів: 2")
    print()

    print("Ліміт частоти")
    for result in (process_local_counters(), shared_counters()):
        print(f"  {result.name:<26} пропущено {result.number:>3}   {result.note}")
    print()

    print("Фонова задача")
    for result in (scheduler_inside(), scheduler_outside()):
        print(f"  {result.name:<26} виконано  {result.number:>3}   {result.note}")
    print()

    print("Метрики")
    result = metrics_per_process()
    print(f"  {result.name:<26} показує   {result.number:>3}   {result.note}")
    print()

    # Числа беруться з прогону, а не пишуться в текст. Проза, що називає число окремо,
    # розходиться з ним при першій же зміні — і саме це сталося з першою редакцією.
    leaked = process_local_counters().number
    print("Що тут читати:")
    print("  Усі три рядки — **одна причина**: стан у памʼяті процесу. Різні лише наслідки.")
    print()
    print("  Задачу, виконану двічі, помічають: вона лишає два рядки в логу. Ліміт, що")
    print(f"  пропустив {leaked} при межі {LIMIT}, не лишає нічого — сервіс поводиться")
    print("  так само, як мав би, просто число означає інше.")
    print()
    print("  Метрики гірші за обидва: вони не брешуть, а показують правду **одного з двох**.")
    print("  Числа майже сходяться, і саме «майже» робить пошук причини довгим.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
