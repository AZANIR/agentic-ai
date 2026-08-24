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
from stages.s06_platform.jobs import INSIDE, SEPARATE
from stages.s06_platform.observe import Dependency, Health

SCHEDULER_MODE = INSIDE if os.environ.get("SCHEDULER_INSIDE") == "1" else SEPARATE
TRACE_PATH = Path(os.environ.get("TRACE_DIR", "traces")) / "service.jsonl"


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
            Dependency(name="store", probe=lambda: store.all_facts()),
            Dependency(
                name="counters", probe=lambda: counters.total("health", now=0.0, window=1.0)
            ),
        ],
    )
    return service, health, tracer


service, health, _tracer = build()
app = create_app(service, health)
