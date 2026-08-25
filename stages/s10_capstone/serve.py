"""Точка входу зібраного сервісу — і **другий деплой** курсу (ADR-0009).

    uvicorn stages.s10_capstone.serve:app

**Тут немає власного HTTP-шару, і це головне.** Застосунок бере `create_app` етапу 6 —
той самий, що обслуговує етап 6, — і підставляє в нього зібраний `Capstone`. Написати
другий FastAPI-шар означало б переписати частину, а не зібрати її; а перевірка «капстоун
не має власних воротарів» тоді б проходила, поки поруч стояв би власний застосунок.

**Знахідка, яку це виявило.** `Reply` навмисно **не** зветься `Answer`, щоб не стати третім
класом із цим іменем. Але контракту, якого чекає `create_app`, він задовольняє повністю:
`ok`, `text`, `trace_id`, `branch`, `kind`. Тобто етапи 6 і 10 домовлені **формою**, а не
іменем — і саме тому підстановка коштує нуль перехідників.

**Що тут `НЕ ПЕРЕВІРЕНО`.** Прогін `deploy/smoke.sh` проти справжнього HTTPS-домену. Він
потребує піднятої машини, тож офлайн його відтворити неможливо — і перевірка каже це третім
станом, а не зеленим.
"""

from __future__ import annotations

import os
from pathlib import Path

from shared.config import settings
from shared.counters import get_counters
from shared.fake_llm import FakeLLM
from shared.llm import get_client
from shared.trace import trace_run
from stages.s06_platform.api import create_app
from stages.s06_platform.observe import Dependency, Health
from stages.s10_capstone.service import Capstone

TRACE_PATH = Path(os.environ.get("TRACE_DIR", "traces")) / "capstone.jsonl"
MEMORY_PATH = Path(os.environ.get("MEMORY_PATH", "capstone-memory.jsonl"))


def build() -> tuple[Capstone, Health]:
    """Сервіс і його стан. Повертає обидва — щоб точку входу можна було перевірити."""
    TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)
    counters = get_counters(settings)
    tracer = trace_run("s10", path=TRACE_PATH, stage="s10", case="serve").__enter__()

    service = Capstone(
        settings=settings,
        counters=counters,
        # Без справжнього провайдера — підробка, що відповідає на будь-який промпт.
        # Сценарій тут неможливий: запити пише користувач (ADR-0009 етапу 6).
        client=get_client() if settings.has_real_llm else FakeLLM(auto_reply=True),
        tracer=tracer,
        memory_path=MEMORY_PATH,
    )
    health = Health(
        provider="real" if settings.has_real_llm else "fake",
        dependencies=[
            Dependency(name="memory", probe=lambda: len(service.memory.all_facts()) >= 0),
            Dependency(
                name="counters", probe=lambda: counters.total("health", now=0.0, window=1.0)
            ),
            # База знань — теж залежність, і саме вона робить старт довгим: індекс
            # будується один раз, і поки він не готовий, сервіс відповідати не може.
            Dependency(name="knowledge", probe=lambda: service.base is not None),
        ],
    )
    return service, health


def create() -> object:
    """Застосунок етапу 6 навколо зібраного сервісу. Свого HTTP-шару капстоун не має."""
    service, health = build()
    return create_app(service, health)


app = create()
