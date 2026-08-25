"""Трасування кроків агента. Присутнє з ЕТАПУ 1, а не додається на етапі 8 (ADR-0005).

Це не передчасна оптимізація, а виконана порада статті 6: автор зізнається, що додав
трасування, коли система вже заплуталась, і шкодує про це. Тут воно є з першого кроку,
тож етап 8 (оцінка) читає готові траєкторії й не переписує жодного попереднього етапу.

    from shared.trace import trace_run

    with trace_run("демо етапу 1", stage="s01") as tr:
        tr.step("llm_call", model="fake", messages=2)
        tr.step("tool_call", name="get_weather", args={"city": "Kyiv"}, result="+28C")

Формат навмисне примітивний: один рядок JSON = один крок. Читається ``cat``-ом,
грепається, парситься трьома рядками. Складніша модель знадобиться, коли з'явиться
вкладеність глибша за два рівні — тоді формат треба переглядати свідомо.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from shared.config import ConfigError, settings


def new_trace_id() -> str:
    return f"trc_{uuid.uuid4().hex[:16]}"


def default_trace_path() -> Path:
    return settings.trace_dir / f"{date.today().isoformat()}.jsonl"


@dataclass
class Tracer:
    """Пише кроки одного прогону. Створюється через :func:`trace_run`."""

    name: str
    path: Path
    trace_id: str = field(default_factory=new_trace_id)
    meta: dict[str, Any] = field(default_factory=dict)
    _seq: int = field(default=0, init=False)
    _started: float = field(default_factory=time.perf_counter, init=False)

    def step(self, kind: str, **fields: Any) -> dict[str, Any]:
        """Записати один крок. ``kind`` — що сталося: llm_call, tool_call, route, error…"""
        self._seq += 1
        record = {
            "trace_id": self.trace_id,
            "seq": self._seq,
            "ts": time.time(),
            "elapsed_ms": round((time.perf_counter() - self._started) * 1000, 2),
            "name": self.name,
            "kind": kind,
            **self.meta,
            **fields,
        }
        self._append(record)
        return record

    @property
    def step_count(self) -> int:
        return self._seq

    def _append(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


@contextmanager
def trace_run(
    name: str,
    *,
    path: Path | str | None = None,
    **meta: Any,
) -> Iterator[Tracer]:
    """Обгорнути один прогін агента трейсом.

    :param path: куди писати. За замовчуванням ``traces/<дата>.jsonl``.
        Перевірки передають тимчасовий шлях, щоб не засмічувати робочий трейс.
    :param meta: поля, що додаються до КОЖНОГО кроку (наприклад ``stage="s01"``).
    """
    if settings.trace_sink != "jsonl":
        raise ConfigError(
            f"TRACE_SINK={settings.trace_sink!r} не реалізовано, і це рішення, а не борг. "
            "Вимогу до сховища сформулював той, хто трейси читає — оцінювання етапу 8, — і "
            "вона виявилась меншою за здогад: прочитати все одним проходом, групувати ключем "
            "на боці читача, дописувати без переписування, відновлювати порядок із `seq`, "
            "читатись `cat`-ом. JSONL дає всі пʼять; зовнішній стік не додає жодної "
            "(s08-eval, ADR-0009). Шоста вимога зʼявиться на іншому масштабі — тоді й "
            "переглядати."
        )

    target = Path(path) if path is not None else default_trace_path()
    tracer = Tracer(name=name, path=target, meta=meta)
    tracer.step("run_start")
    try:
        yield tracer
    except Exception as exc:
        tracer.step("run_error", error_type=type(exc).__name__, error=str(exc))
        raise
    else:
        tracer.step("run_end", status="ok")


# --- читання: цим користується етап 8 (оцінка) -------------------------------


def iter_steps(path: Path | str | None = None) -> Iterator[dict[str, Any]]:
    """Прочитати кроки з файлу трейсів, по одному."""
    target = Path(path) if path is not None else default_trace_path()
    if not target.exists():
        return
    with target.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def group_by_trace(path: Path | str | None = None) -> dict[str, list[dict[str, Any]]]:
    """Згрупувати кроки в траєкторії: ``{trace_id: [крок, крок, …]}``."""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for step in iter_steps(path):
        grouped[step["trace_id"]].append(step)
    for steps in grouped.values():
        steps.sort(key=lambda s: s["seq"])
    return dict(grouped)


def clear(path: Path | str | None = None) -> None:
    """Видалити файл трейсів. Потрібно перевіркам, щоб починати з чистого аркуша."""
    target = Path(path) if path is not None else default_trace_path()
    if target.exists():
        os.remove(target)
