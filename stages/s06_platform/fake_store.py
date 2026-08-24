"""Підробка спільного сховища: рівно ті операції, якими користується `shared/counters.py`.

Навіщо вона, якщо є контейнер. Контракт лічильників має перевірятись **офлайн** — інакше
найважливіше твердження етапу («два незалежні екземпляри бачать одне число») виконується лише
там, де є Docker, тобто не виконується у CI без extras і не виконується в читача, який ще не
дійшов до розгортання.

**Підробка не імітує Redis.** Вона реалізує п'ять операцій із тією семантикою, на яку
покладається `Shared`, і зберігає дані у словнику, що передається ззовні. Саме це «ззовні» і
робить її придатною: два лічильники, створені окремо на одному словнику, — це модель двох
воркерів на одному сховищі.

Межа названа: підробка не має ні мережі, ні атомарності, ні витіснення. Твердження про
**одночасні** записи вона довести не може, і жодна перевірка тут цього не стверджує.
"""

from __future__ import annotations

from typing import Any


class FakeStore:
    """Мінімальне сховище впорядкованих множин на переданому словнику."""

    def __init__(self, data: dict[str, dict[str, float]] | None = None) -> None:
        # Словник приходить ззовні навмисно: два FakeStore на одному словнику — це два
        # воркери на одному Redis, і саме цю пару стверджує перевірка контракту.
        self.data = data if data is not None else {}
        self.expirations: dict[str, int] = {}

    def zrangebyscore(self, name: str, low: float, high: Any) -> list[str]:
        """Читання діапазоном — без жодної зміни стану. Саме тому воно поза конвеєром."""
        bucket = self.data.get(name, {})
        top = float("inf") if high in ("+inf", float("inf")) else float(high)
        chosen = [m for m, score in bucket.items() if low <= score <= top]
        return sorted(chosen, key=lambda m: bucket[m])

    def pipeline(self) -> FakePipeline:
        return FakePipeline(self)


class FakePipeline:
    """Накопичує операції й виконує їх одним `execute`, як справжній конвеєр."""

    def __init__(self, store: FakeStore) -> None:
        self._store = store
        self._ops: list[tuple[str, tuple[Any, ...]]] = []

    def zadd(self, name: str, mapping: dict[str, float]) -> FakePipeline:
        self._ops.append(("zadd", (name, mapping)))
        return self

    def zremrangebyscore(self, name: str, low: float, high: float) -> FakePipeline:
        self._ops.append(("zrem", (name, low, high)))
        return self

    def zrange(self, name: str, start: int, stop: int) -> FakePipeline:
        self._ops.append(("zrange", (name, start, stop)))
        return self

    def expire(self, name: str, seconds: int) -> FakePipeline:
        self._ops.append(("expire", (name, seconds)))
        return self

    def execute(self) -> list[Any]:
        results: list[Any] = []
        for op, args in self._ops:
            results.append(getattr(self, f"_{op}")(*args))
        self._ops = []
        return results

    def _zadd(self, name: str, mapping: dict[str, float]) -> int:
        bucket = self._store.data.setdefault(name, {})
        added = sum(1 for member in mapping if member not in bucket)
        bucket.update(mapping)
        return added

    def _zrem(self, name: str, low: float, high: float) -> int:
        bucket = self._store.data.get(name, {})
        doomed = [m for m, score in bucket.items() if low <= score <= high]
        for member in doomed:
            del bucket[member]
        return len(doomed)

    def _zrange(self, name: str, start: int, stop: int) -> list[str]:
        bucket = self._store.data.get(name, {})
        members = sorted(bucket, key=lambda m: bucket[m])
        return members[start:] if stop == -1 else members[start : stop + 1]

    def _expire(self, name: str, seconds: int) -> bool:
        self._store.expirations[name] = seconds
        return True
