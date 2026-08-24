"""Лічильники з вікном: скільки разів за хвилину, скільки витрачено за добу.

Ліміт частоти й бюджетний запобіжник — **та сама механіка** з різним змістом: обидва питають
«скільки набралося у вікні» й обидва мають межу. Тому реалізація одна, а вікон два.

**Де живе число — головне питання цього модуля, а не як воно рахується.**

Найпростіша реалізація тримає лічильники у словнику в пам'яті процесу: нуль залежностей,
миттєвий доступ, працює бездоганно. Рівно доти, доки процес один. Другий воркер робить кожен
лічильник неправдою **мовчки**: ліміт у 30 запитів на хвилину пропускає 60, бюджет у п'ять
доларів витрачає десять, і жодної помилки в логах немає.

Тому реалізацій дві, і вибір між ними — у фабриці (ADR-0002):

    InMemory   профіль local; процесо-локальний **навмисно** — це вправа етапу
    Shared     профіль prod; спільний для всіх воркерів

**Один ключ — одне вікно.** Прибирання застарілого робить `add`, і робить його за тим
вікном, з яким його викликали. Ключ, який питають двома різними вікнами, отримав би
прибирання за вужчим із них — тобто ширше вікно мовчки втратило б дані. Ліміт частоти й
бюджет живуть у різних ключах саме тому, а не випадково.

**`total` нічого не змінює.** Перша редакція чистила сховище прямо в читанні, і два різні
вікна на одному ключі знищували одне одного: спитав про хвилину — доба спорожніла. Метод
із назвою «скільки» не має права видаляти.

Локальна реалізація не є поступкою. Читач запускає два воркери й бачить, що подвоївся не лише
планувальник, а й ліміт — причому подвоєну задачу видно в логах, а подвоєний ліміт **не видно
ніде**: сервіс поводиться нормально, просто межа означає вдвічі більше.

**Час подається параметром і ніде не береться з годинника** — урок етапу 5. Вікно, що читає
годинник усередині, робить перевірку ліміту такою, що проходить о 12:00:59 і падає о 12:01:00.
"""

from __future__ import annotations

from typing import Any, Protocol
from uuid import uuid4

from shared.config import PROD, Settings
from shared.config import settings as default_settings

MINUTE = 60.0
DAY = 86_400.0


class Counters(Protocol):
    """Спільний контракт. Воротарі знають лише його.

    Дві реалізації — дві поведінки, тож перевірка має стверджувати те, що **спільне**.
    Найважливіше твердження контракту: два незалежні екземпляри бачать одне число. Воно
    зелене на спільному сховищі й червоне на процесо-локальному — тобто саме воно їх і
    розрізняє, і саме воно робить `InMemory` вправою, а не альтернативою.
    """

    name: str

    def add(self, key: str, amount: float, *, now: float, window: float) -> float:
        """Додати до вікна й повернути суму, що набралася в ньому. Повертає **після** додавання."""
        ...

    def total(self, key: str, *, now: float, window: float) -> float:
        """Скільки набралося у вікні. **Нічого не змінює** — ні даних, ні вікна."""
        ...


class InMemory:
    """Процесо-локальний лічильник. Правда рівно для одного процесу.

    Зберігає окремі події з мітками часу, а не суму: інакше «вікно» доводилось би зсувати
    здогадом. Пам'ять обмежена самим вікном — усе старіше викидається при кожному дотику.
    """

    name = "in-memory"

    def __init__(self) -> None:
        self._events: dict[str, list[tuple[float, float]]] = {}

    def add(self, key: str, amount: float, *, now: float, window: float) -> float:
        events = self._prune(key, now=now, window=window)
        events.append((now, amount))
        return sum(value for _, value in events)

    def total(self, key: str, *, now: float, window: float) -> float:
        return sum(value for at, value in self._events.get(key, []) if now - at < window)

    def _prune(self, key: str, *, now: float, window: float) -> list[tuple[float, float]]:
        events = [(at, value) for at, value in self._events.get(key, []) if now - at < window]
        self._events[key] = events
        return events


class Shared:
    """Лічильник у спільному сховищі: один на всі воркери.

    Вікно — відсортована множина за міткою часу: додати подію, викинути старіші за вікно,
    підсумувати те, що лишилось. Операції виконуються однією транзакцією, інакше два воркери
    між читанням і записом побачать одне й те саме й обидва пропустять запит.
    """

    name = "shared"

    def __init__(self, client: Any, *, prefix: str = "s06") -> None:
        self._client = client
        self._prefix = prefix

    def add(self, key: str, amount: float, *, now: float, window: float) -> float:
        name = f"{self._prefix}:{key}"
        pipe = self._client.pipeline()
        # Унікальний член: час, **випадковий токен**, сума. Перша редакція складала член
        # із часу й суми — і дві події тієї самої миті з тією самою вартістю ставали
        # одним членом множини, бо множина за визначенням не тримає дублікатів.
        #
        # Наслідок був тихий і однобічний: ліміт **недо**раховував. Шість запитів за одну
        # мить проходили при межі три. У `InMemory` цього не було — там події лягають у
        # список, який дублікатів не помічає. Дві реалізації розійшлися саме там, де
        # контракт їх не звіряв: фікстура щоразу збільшувала час.
        member = f"{now:.6f}:{uuid4().hex[:8]}:{amount}"
        pipe.zadd(name, {member: now})
        pipe.zremrangebyscore(name, 0, now - window)
        pipe.zrange(name, 0, -1)
        pipe.expire(name, int(window) + 1)
        added = pipe.execute()
        return _sum_members(added[2])

    def total(self, key: str, *, now: float, window: float) -> float:
        name = f"{self._prefix}:{key}"
        return _sum_members(self._client.zrangebyscore(name, now - window, "+inf"))


def _sum_members(members: list[Any]) -> float:
    """Підсумувати суми з членів. Член має вигляд ``<час>:<токен>:<сума>``."""
    total = 0.0
    for member in members:
        raw = member.decode() if isinstance(member, bytes) else str(member)
        total += float(raw.rsplit(":", 1)[1])
    return total


def get_counters(settings: Settings | None = None, *, client: Any = None) -> Counters:
    """Лічильники за конфігурацією. Розгалуження за профілем живе тут і більше ніде.

    :param client: готовий клієнт сховища. Перевірки передають підробку, щоб стверджувати
        контракт без контейнера.
    """
    settings = settings or default_settings
    if client is not None:
        return Shared(client)
    if settings.profile != PROD:
        return InMemory()

    import redis  # noqa: PLC0415 — залежність лише профілю prod

    return Shared(redis.Redis.from_url(settings.redis_url))
