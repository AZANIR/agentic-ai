"""Запис факту й чотири умови, за яких він потрапляє у контекст.

Факт плаский навмисно: власник, тема, текст, час, термін придатності, статус. Ані звʼязків
між фактами, ані вкладеності — граф знань це окрема задача з окремою ціною (SAD §3).

**Чотири умови активності зібрані тут, в одному місці.** Розкидані по місцях використання
вони перестають читатися як одне правило, і тоді дуже легко забути одну з них у новому
місці — а забута умова в памʼяті означає або витік, або мовчазне зникнення відповіді:

    власник     факт належить тому, хто питає
    статус      факт не замінений новішим
    термін      факт не протух
    поріг       факт достатньо релевантний питанню   (це вже у `retrieval`)

Перші три перевіряються тут; четверта потребує питання, тож живе у вибірці.

**Час подається параметром і ніде не береться з годинника.** Це не зручність для тестів.
Функція, що читає `datetime.now()` усередині, робить памʼять недетермінованою: та сама
памʼять із тим самим питанням дає різні відповіді залежно від того, котра зараз година —
і перевірка TTL проходить уночі й падає вдень. Явний час робить протухання відтворюваним:
подав час на день пізніше — побачив, що факт зник, у ту саму секунду (ADR етапу 0003).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

ACTIVE = "active"
REPLACED = "replaced"
STATUSES = frozenset({ACTIVE, REPLACED})

_REQUIRED = ("owner", "topic", "text", "stored_at")


@dataclass(frozen=True)
class Fact:
    """Один запис памʼяті. Незмінний: заміна створює новий, а не править старий."""

    owner: str
    topic: str
    text: str
    stored_at: float
    ttl: float | None = None
    status: str = ACTIVE
    replaced_at: float | None = field(default=None)

    def expires_at(self) -> float | None:
        """Коли факт протухне. ``None`` означає «ніколи»."""
        return None if self.ttl is None else self.stored_at + self.ttl

    def to_line(self) -> str:
        """Один рядок файлу. Без переносів: файл читається по рядку на запис."""
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_line(cls, line: str) -> Fact:
        """Прочитати запис. Зіпсований рядок — це помилка, а не факт із порожніми полями.

        :raises ValueError: якщо рядок не розбирається або в ньому бракує обовʼязкового.
        """
        try:
            data = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"рядок не розбирається: {error}") from error

        if not isinstance(data, dict):
            raise ValueError(f"очікували обʼєкт, отримали {type(data).__name__}")
        missing = [name for name in _REQUIRED if not data.get(name)]
        if missing:
            raise ValueError(f"бракує обовʼязкових полів: {', '.join(missing)}")
        if data.get("status", ACTIVE) not in STATUSES:
            raise ValueError(f"невідомий статус {data.get('status')!r}")

        known = {name: data.get(name) for name in cls.__dataclass_fields__}
        return cls(**known)


def is_active(fact: Fact, *, now: float) -> bool:
    """Чи бере факт участь у вибірці станом на вказаний момент.

    Три умови з чотирьох. Четверта — релевантність питанню — потребує самого питання й
    живе у `retrieval`.
    """
    if fact.status != ACTIVE:
        return False
    expires = fact.expires_at()
    return expires is None or now <= expires


def replace(old: Fact, *, at: float) -> Fact:
    """Позначити факт заміненим. Текст лишається: історія заміни сама по собі цінна."""
    return Fact(**{**asdict(old), "status": REPLACED, "replaced_at": at})


def describe_skip(fact: Fact, *, now: float) -> str | None:
    """Чому факт не взяли — словами. ``None``, якщо взяли б.

    Причина потрібна у трейсі: «факт не потрапив у контекст» без причини неможливо ні
    налагодити, ні пояснити користувачеві, чому система «забула».
    """
    if fact.status == REPLACED:
        return f"замінено о {fact.replaced_at}"
    expires = fact.expires_at()
    if expires is not None and now > expires:
        return f"протух о {expires}"
    return None


def as_context_line(fact: Fact) -> dict[str, Any]:
    """Факт у вигляді, придатному для промпту й трейсу. Власника тут немає навмисно."""
    return {"topic": fact.topic, "text": fact.text, "stored_at": fact.stored_at}
