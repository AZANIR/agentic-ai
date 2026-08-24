"""Планувальник окремим процесом. Рівно один екземпляр на розгортання.

    python -m stages.s06_platform.schedule

**Чому окремо** — ADR-0003. Планувальник усередині застосунку множиться разом із воркерами,
і задача виконується стільки разів, скільки процесів. Тут процес один за побудовою: не тому,
що так домовились, а тому, що більше його ніхто не запускає.

Прибирання ідемпотентне, і це **не** причина спокійно жити з подвоєнням: наступна задача в
цьому ж планувальнику надішле лист або спише гроші.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from shared.config import settings
from shared.factstore import get_fact_store
from stages.s06_platform.jobs import count_expired

INTERVAL_HOURS = float(os.environ.get("CLEANUP_INTERVAL_HOURS", "24"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s scheduler %(message)s")
log = logging.getLogger(__name__)


def tick() -> None:
    import time

    store = get_fact_store(settings, path=Path(os.environ.get("MEMORY_PATH", "memory.jsonl")))
    expired = count_expired(store, now=time.time())
    # Число в логу — те саме, що читач рахує у вправі. Формулювання «прибрано» без числа
    # зробило б подвоєння невидимим саме там, де його показують.
    log.info("звіт: протухлих %s", expired)


def main() -> int:
    scheduler = BlockingScheduler()
    scheduler.add_job(tick, "interval", hours=INTERVAL_HOURS, id="cleanup")
    log.info("планувальник запущено, інтервал %s год", INTERVAL_HOURS)
    scheduler.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
