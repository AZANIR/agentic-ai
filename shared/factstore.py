"""Сховище фактів: файл етапу 5 або таблиця в базі — за одним набором методів.

**Тут перевіряється обіцянка етапу 5.** Він писав: «етап 6 замінить сховище тим самим
інтерфейсом — і саме тому інтерфейс тут вузький». Настав момент подивитись, чи це правда.

Вона правдива наполовину, і ADR-0004 записує це чесно. Вузьким виявився **набір методів**:

    all_facts()                    усі записи
    remember(fact)                 зберегти; новіший тієї ж теми витісняє старий
    context_for(owner, question)   що піде в промпт і чому решта не пішла

Трьох методів справді досить, щоб написати другу реалізацію. Але `Memory` приймає **шлях**, а
не сховище, і його перевірки будують клас напряму — тож підмінити реалізацію **всередині**
етапу 5 без правки неможливо. Тому фабрика стоїть **зовні**: файлову реалізацію бере як є,
базову пише сама, а контракт, спільний для обох, стверджує етап 6.

**Найважливіша різниця між реалізаціями — не швидкодія.** Файлова читає **всі** записи,
зокрема чужі, і фільтрує власника в пам'яті процесу. Базова робить це умовою запиту, тобто
чужий рядок не залишає сховища взагалі. Це закриває борг, названий в ADR-0004 етапу 5 у
розділі Negative — і саме тому ізоляція перевіряється **на обох** реалізаціях, а не на одній.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from shared.config import PROD, Settings
from shared.config import settings as default_settings
from stages.s05_memory.facts import ACTIVE, REPLACED, Fact, replace
from stages.s05_memory.long_term import Context, Memory


class FactStore(Protocol):
    """Спільний контракт. Сервіс знає лише його."""

    name: str

    def all_facts(self) -> list[Fact]: ...

    def ping(self) -> None: ...

    def remember(self, fact: Fact) -> Fact | None: ...

    def context_for(self, owner: str, question: str, *, now: float, limit: int = 3) -> Context: ...


class FileStore:
    """Файлова реалізація — це `Memory` етапу 5 без жодної зміни.

    Обгортка тут не декоративна: вона тримає межу. Етап 5 лишається недоторканим, а все, що
    сервісу від нього треба, названо трьома методами вище.
    """

    name = "file"

    def __init__(self, path: Path) -> None:
        self._memory = Memory(path)

    def all_facts(self) -> list[Fact]:
        return self._memory.all_facts()

    def ping(self) -> None:
        """Чи доступне сховище. **Не читає даних** — див. `DatabaseStore.ping`."""
        self._memory.path.parent.mkdir(parents=True, exist_ok=True)

    def remember(self, fact: Fact) -> Fact | None:
        return self._memory.remember(fact)

    def context_for(self, owner: str, question: str, *, now: float, limit: int = 3) -> Context:
        return self._memory.context_for(owner, question, now=now, limit=limit)


class DatabaseStore:
    """Реалізація на базі: власник — умова запиту, а не фільтр у пам'яті.

    Вибірка й ранжування лишаються тими самими, що на етапі 5, — це навмисно. Перенести їх у
    запит було б швидше й забрало б властивість, заради якої етап 5 писався: причина, з якої
    факт **не** дійшов, лишається видимою у `Context.skipped`. Оптимізація приходить на етапі
    8, після вимірювання.
    """

    name = "database"

    def __init__(
        self, connection: Any, *, retrieval: Any = None, threshold: float | None = None
    ) -> None:
        self._connection = connection
        self._retrieval = retrieval
        self._threshold = threshold

    def all_facts(self) -> list[Fact]:
        rows = self._query(
            "SELECT owner, topic, text, stored_at, ttl, status, replaced_at FROM facts"
            " ORDER BY stored_at"
        )
        return [_from_row(row) for row in rows]

    def _facts_of(self, owner: str) -> list[Fact]:
        """Лише свої — умовою запиту. Чужий рядок не залишає сховища."""
        rows = self._query(
            "SELECT owner, topic, text, stored_at, ttl, status, replaced_at FROM facts"
            " WHERE owner = %s ORDER BY stored_at",
            (owner,),
        )
        return [_from_row(row) for row in rows]

    def remember(self, fact: Fact) -> Fact | None:
        existing = [
            f for f in self._facts_of(fact.owner) if f.topic == fact.topic and f.status == ACTIVE
        ]
        retired = None
        for old in existing:
            # Хто старіший, той і йде в історію — те саме правило, що в етапі 5.
            if fact.stored_at < old.stored_at:
                fact = replace(fact, at=old.stored_at)
                continue
            retired = replace(old, at=fact.stored_at)
            self._execute(
                "UPDATE facts SET status = %s, replaced_at = %s"
                " WHERE owner = %s AND topic = %s AND stored_at = %s",
                (REPLACED, retired.replaced_at, old.owner, old.topic, old.stored_at),
            )
        self._execute(
            "INSERT INTO facts (owner, topic, text, stored_at, ttl, status, replaced_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                fact.owner,
                fact.topic,
                fact.text,
                fact.stored_at,
                fact.ttl,
                fact.status,
                fact.replaced_at,
            ),
        )
        return retired

    def context_for(self, owner: str, question: str, *, now: float, limit: int = 3) -> Context:
        # Ранжувальник створюється **на запит**, а не тримається полем. Спільний
        # екземпляр тримав би власника у `self`, і два одночасні запити читали б
        # памʼять одне одного: між `self._owner = owner` і читанням є вікно, а
        # синхронний ендпоінт FastAPI виконується в пулі потоків.
        #
        # Витоку це не давало — фільтр етапу 5 рятував, — але **своя відповідь
        # зникала**. Тобто рівно та вада, яку курс називає гіршою за витік, і яку
        # перевірка на витік не бачить.
        ranker = _DatabaseMemory(
            self._facts_of, owner, retrieval=self._retrieval, threshold=self._threshold
        )
        return ranker.context_for(owner, question, now=now, limit=limit)

    def ping(self) -> None:
        """Чи доступна база. Один тривіальний запит, без жодного рядка даних.

        Перша редакція проби читала `all_facts()` — тобто **повний скан таблиці без
        межі**. Ендпоінт стану відкритий навмисно (його читає монітор без ключа), і
        воротарі до нього не доходять: будь-хто замовляв повний скан стільки разів на
        секунду, скільки витримає мережа. Дешева проба — не оптимізація, а межа.
        """
        self._query("SELECT 1")

    def _query(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(sql, params)
                return list(cursor.fetchall())
        except Exception:
            # Відкат ОБОВʼЯЗКОВИЙ. Невдалий запит лишає транзакцію в
            # аварійному стані, і кожен наступний — включно з пробою стану —
            # падає з `InFailedSqlTransaction`, навіть коли причина зникла.
            # Знайдено розгортанням: таблиці ще не було, і сервіс лишався
            # мертвим після її появи.
            self._connection.rollback()
            raise

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute(sql, params)
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise


class _DatabaseMemory(Memory):
    """`Memory` етапу 5, у якого читання йде в базу.

    Підклас, а не підміна методу. Спокуса написати `store.all_facts = lambda: ...` була
    коротшою на два рядки й лишала б обʼєкт, поведінка якого не читається з його класу —
    рівно те, що о третій ночі розбирають найдовше.

    Успадковується саме **ранжування**: чотири умови, поріг, ліміт і причини відкидання.
    База замінює лише читання, і це та межа, яку етап 5 назвав вузькою.
    """

    def __init__(self, fetch: Any, owner: str, **kwargs: Any) -> None:
        # Шлях не використовується: `all_facts` перевизначено. Імʼя каже це вголос,
        # щоб ніхто не шукав файл, якого немає.
        super().__init__(Path("unused-the-store-is-a-database"), **kwargs)
        self._fetch = fetch
        self._owner = owner

    def all_facts(self) -> list[Fact]:
        return self._fetch(self._owner)


def _from_row(row: tuple[Any, ...]) -> Fact:
    owner, topic, text, stored_at, ttl, status, replaced_at = row
    return Fact(
        owner=owner,
        topic=topic,
        text=text,
        stored_at=float(stored_at),
        ttl=None if ttl is None else float(ttl),
        status=status,
        replaced_at=None if replaced_at is None else float(replaced_at),
    )


def get_fact_store(
    settings: Settings | None = None, *, path: Path | None = None, connection: Any = None
) -> FactStore:
    """Сховище за конфігурацією. Розгалуження за профілем живе тут і більше ніде.

    :param connection: готове зʼєднання. Перевірки передають підробку, щоб стверджувати
        контракт без контейнера.
    """
    settings = settings or default_settings
    if connection is not None:
        return DatabaseStore(connection)
    if settings.profile != PROD:
        return FileStore(path or Path("memory.jsonl"))

    import psycopg  # noqa: PLC0415 — залежність лише профілю prod

    return DatabaseStore(psycopg.connect(settings.database_url))
