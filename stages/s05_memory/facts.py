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
from datetime import UTC, datetime
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
        # ПРИСУТНІСТЬ, а не істинність. `not data.get(name)` оголошував зіпсованим
        # запис зі `stored_at = 0.0` — тобто факт, записаний рівно в епоху, читався
        # як биття. Нуль, порожній рядок і False — це значення, а не відсутність.
        missing = [name for name in _REQUIRED if name not in data or data[name] == ""]
        if missing:
            raise ValueError(f"бракує обовʼязкових полів: {', '.join(missing)}")
        # Дефолт стоїть ОДИН раз і використовується обома перевірками нижче. Дві копії
        # цього рядка — з дефолтом у валідації й без нього у складанні — і дали запис
        # зі `status=None`: валідація бачила ACTIVE, у поле лягало None, факт мовчки
        # переставав бути активним. Витоку немає; відповідь зникла.
        data.setdefault("status", ACTIVE)
        if data["status"] not in STATUSES:
            raise ValueError(f"невідомий статус {data['status']!r}")

        # Числа з чужого файлу — числа, а не «щось». Рядок у `ttl` проходив аж до
        # `stored_at + ttl` і валив TypeError назовні: `long_term` ловить ValueError,
        # тож одного зіпсованого рядка вистачало, щоб уся памʼять перестала читатись.
        for name in ("stored_at", "ttl", "replaced_at"):
            value = data.get(name)
            if value is not None and not isinstance(value, (int, float)):
                raise ValueError(f"{name} має бути числом, а не {type(value).__name__}")

        if data["status"] == REPLACED and data.get("replaced_at") is None:
            raise ValueError("статус replaced без часу заміни — запис неповний")

        known = {name: data.get(name) for name in cls.__dataclass_fields__}
        return cls(**known)


def _when(moment: float) -> str:
    """Мить у читабельному вигляді. Годинник не читається — форматується подане."""
    return datetime.fromtimestamp(moment, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")


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
        return f"замінено {_when(fact.replaced_at)}"
    expires = fact.expires_at()
    if expires is not None and now > expires:
        return f"протух {_when(expires)}"
    return None


def one_line(value: str) -> str:
    """Схлопнути будь-який пробільний символ у звичайний пробіл.

    `str.split()` без аргументів розділяє за U+2028, U+2029, U+0085 і рештою того, що
    Python вважає пробільним, — тобто саме за тими символами, які `json.dumps` НЕ
    екранує, а `str.splitlines()` при читанні вважає межею рядка. Один такий символ у
    тексті факту розривав запис JSONL надвоє, і факт зникав з обох половин.

    Він приїжджає не з екзотики: текст, скопійований із PDF або Word, несе U+2028
    регулярно, а текст факту пише користувач.
    """
    return " ".join(value.split())


def as_context_line(fact: Fact) -> dict[str, Any]:
    """Факт у вигляді, придатному для промпту й трейсу. Власника тут немає навмисно."""
    return {"topic": one_line(fact.topic), "text": one_line(fact.text), "stored_at": fact.stored_at}
