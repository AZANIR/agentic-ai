"""Точка входу: зібрати сервіс із конфігурації й віддати застосунок.

    uvicorn stages.s06_platform.serve:app --workers 2

**Усе розгалуження за профілем — у фабриках `shared/`.** Цей модуль лише запитує в них
готові адаптери; про те, файл там чи база, памʼять чи Redis, він не знає й знати не має.

**Планувальник тут не запускається.** Він окремий процес (ADR-0003), і саме тому воркери
про час не знають. Прапорець `SCHEDULER_INSIDE=1` вмикає пастку для вправи — вона лишається
в репозиторії навмисно, під прапорцем, а не в коментарі.
"""

from __future__ import annotations

import os
from pathlib import Path

from shared.config import settings
from shared.counters import get_counters
from shared.factstore import get_fact_store
from shared.fake_llm import FakeLLM
from shared.llm import get_client
from shared.trace import trace_run
from stages.s06_platform.api import create_app
from stages.s06_platform.app import Service
from stages.s06_platform.jobs import count_expired
from stages.s06_platform.observe import Dependency, Health

SCHEDULER_INSIDE = os.environ.get("SCHEDULER_INSIDE") == "1"
TRACE_PATH = Path(os.environ.get("TRACE_DIR", "traces")) / "service.jsonl"


def _probe_traces(path: Path) -> None:
    """Чи можна писати трейси. Створює каталог і торкається файлу — і нічого більше."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8"):
        pass


def build():
    """Сервіс, стан і трейсер. Повертає все три — щоб точку входу можна було перевірити."""
    counters = get_counters(settings)
    store = get_fact_store(settings, path=Path(os.environ.get("MEMORY_PATH", "memory.jsonl")))
    tracer = trace_run("s06", path=TRACE_PATH, stage="s06").__enter__()

    service = Service(
        settings=settings,
        counters=counters,
        store=store,
        tracer=tracer,
        # Без справжнього провайдера — підробка, що відповідає на будь-який промпт.
        # Сценарій тут неможливий: запити пише користувач. Відповіді беззмістовні за
        # побудовою, і стан кричить про це полем `provider` (ADR-0009).
        client=get_client() if settings.has_real_llm else FakeLLM(auto_reply=True),
    )
    provider = "real" if settings.has_real_llm else "fake"
    health = Health(
        provider=provider,
        dependencies=[
            # Проба має бути дешевою й справжньою. `all_facts` читає сховище насправді —
            # перевірка «обʼєкт існує» рапортувала б «живий» на недоступній базі.
            # Проба має бути дешевою й справжньою: `ping` торкається сховища й не
            # читає даних. Читання `all_facts()` тут було повним сканом на кожен опит
            # монітора — і на кожен запит будь-кого, бо стан відкритий.
            Dependency(name="store", probe=store.ping),
            Dependency(
                name="counters", probe=lambda: counters.total("health", now=0.0, window=1.0)
            ),
            # Трейс — теж залежність, і донедавна єдина, про яку стан мовчав. Її
            # відмова (том повний, права, ФС лише для читання) валила КОЖЕН запит
            # п'ятисоткою, а стан лишався `up`. Проба пише в той самий каталог.
            Dependency(name="traces", probe=lambda: _probe_traces(TRACE_PATH)),
        ],
    )
    return service, health, tracer


def _start_the_trap(store) -> None:
    """Увімкнути пастку: планувальник **усередині** кожного воркера.

    Це і є вправа ADR-0003, і вона має бути відтворювана на живому сервісі, а не лише
    в моделі `jobs.py`. Кожен воркер — окремий процес, тож два воркери дають два
    планувальники, і рядок у логу зʼявляється двічі за інтервал:

        SCHEDULER_INSIDE=1 uvicorn stages.s06_platform.serve:app --workers 2

    Прапорець прибирає рівно одне — винесення в окремий процес. Усе інше лишається
    тим самим, і саме тому різницю видно числом, а не поясненням.
    """
    import logging
    import time

    from apscheduler.schedulers.background import BackgroundScheduler

    log = logging.getLogger("s06.trap")
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: log.warning(
            "ПАСТКА · pid %s · протухлих %s", os.getpid(), count_expired(store, now=time.time())
        ),
        "interval",
        seconds=float(os.environ.get("CLEANUP_INTERVAL_SECONDS", "60")),
        id="trap",
    )
    scheduler.start()


service, health, _tracer = build()
if SCHEDULER_INSIDE:
    _start_the_trap(service.store)
app = create_app(service, health)
