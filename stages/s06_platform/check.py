"""Перевірки етапу 6.

    python -m stages.s06_platform.check

Працюють **офлайн і без контейнерів**. Те, що справді потребує Docker, позначається
`НЕ ПЕРЕВІРЕНО` — третій стан, і він не дорівнює зеленому.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from shared.check_runner import NotVerified, run_checks
from shared.config import LOCAL, Settings
from shared.counters import DAY, MINUTE, InMemory, Shared, get_counters
from shared.factstore import DatabaseStore, FileStore
from stages.s05_memory.facts import Fact
from stages.s06_platform.guards import (
    BUDGET_EXHAUSTED,
    OK,
    RATE_LIMITED,
    UNAUTHENTICATED,
    admit,
    charge,
    owner_of,
)
from stages.s06_platform.fake_store import FakeStore

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії.
BUDGET_SECONDS = 60

NEWLINE = chr(10)
NOW = 1_700_000_000.0
QUESTION = "куди доставляти замовлення"


def _fact(owner: str, topic: str, text: str, **kwargs) -> Fact:
    return Fact(owner=owner, topic=topic, text=text, stored_at=NOW, **kwargs)


def _shared_pair() -> tuple[Shared, Shared]:
    """Два лічильники на одному сховищі — модель двох воркерів на одному Redis."""
    data: dict[str, dict[str, float]] = {}
    return Shared(FakeStore(data)), Shared(FakeStore(data))


# --- контракт, спільний для обох реалізацій --------------------------------------------


def check_both_counters_answer_the_same_way_within_one_instance() -> None:
    """counters: обидві реалізації дають однакові числа в межах одного екземпляра"""
    for counter in (InMemory(), Shared(FakeStore())):
        assert counter.total("k", now=NOW, window=MINUTE) == 0.0, counter.name

        assert counter.add("k", 1, now=NOW, window=MINUTE) == 1.0, counter.name
        assert counter.add("k", 1, now=NOW + 1, window=MINUTE) == 2.0, counter.name
        assert counter.total("k", now=NOW + 2, window=MINUTE) == 2.0, counter.name

        # Ключі не змішуються.
        assert counter.add("other", 5, now=NOW, window=MINUTE) == 5.0, counter.name
        assert counter.total("k", now=NOW + 2, window=MINUTE) == 2.0, counter.name


def check_the_window_forgets_what_fell_out_of_it() -> None:
    """counters: подія, старіша за вікно, перестає рахуватись — в обох реалізаціях"""
    for counter in (InMemory(), Shared(FakeStore())):
        counter.add("k", 1, now=NOW, window=MINUTE)
        assert counter.total("k", now=NOW + MINUTE - 1, window=MINUTE) == 1.0, counter.name
        assert counter.total("k", now=NOW + MINUTE + 1, window=MINUTE) == 0.0, counter.name

        # Читання не змінює стан. Перша редакція чистила сховище прямо в `total`, і
        # питання про вікно, що вже минуло, стирало подію назавжди: наступний запит у
        # межах вікна бачив нуль. Метод із назвою «скільки» не має права видаляти.
        counter.add("w", 1, now=NOW, window=DAY)
        counter.total("w", now=NOW + DAY + 1, window=DAY)
        assert counter.total("w", now=NOW + 1, window=DAY) == 1.0, (
            f"{counter.name}: читання за межами вікна стерло подію — `total` змінює стан"
        )


def check_two_instances_on_one_store_see_one_number() -> None:
    """ВІДМОВА · головна перевірка етапу: два екземпляри бачать ОДИН лічильник"""
    first, second = _shared_pair()

    first.add("client", 1, now=NOW, window=MINUTE)
    seen = second.total("client", now=NOW, window=MINUTE)

    assert seen == 1.0, (
        f"другий екземпляр бачить {seen}, а не 1. Лічильник привʼязаний до процесу — і це "
        "означає, що ліміт у 30 запитів на хвилину при двох воркерах пропустить 60, а бюджет "
        "витратить удвічі більше. Помилки не буде ніде: межа просто означатиме інше"
    )

    # І назад: другий додає, перший бачить. Односторонній обмін — це не спільний стан.
    second.add("client", 2, now=NOW + 1, window=MINUTE)
    assert first.total("client", now=NOW + 1, window=MINUTE) == 3.0


def check_two_in_memory_counters_do_not_see_each_other() -> None:
    """ВІДМОВА · дзеркальна: процесо-локальний лічильник НЕ спільний — і це вправа, не вада"""
    first, second = InMemory(), InMemory()
    first.add("client", 1, now=NOW, window=MINUTE)

    assert second.total("client", now=NOW, window=MINUTE) == 0.0, (
        "два InMemory побачили одне число — тоді перевірка вище нічого не розрізняє, і "
        "твердження «спільне сховище спільне» стає тавтологією"
    )

    # Твердження не про ваду, а про **різницю** між реалізаціями. Без цього рядка перевірка
    # вище зелена й на двох реалізаціях, що обидві процесо-локальні.
    shared_first, shared_second = _shared_pair()
    shared_first.add("client", 1, now=NOW, window=MINUTE)
    assert shared_second.total("client", now=NOW, window=MINUTE) == 1.0


def check_time_is_passed_in_never_read_from_the_clock() -> None:
    """ВІДМОВА · counters: рішення про вікно не залежить від системного годинника"""
    import ast
    import inspect

    from shared import counters

    forbidden = {"now", "utcnow", "today", "time", "monotonic", "perf_counter"}
    called = set()
    for node in ast.walk(ast.parse(inspect.getsource(counters))):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            called.add(node.func.attr)
        elif isinstance(node.func, ast.Name):
            called.add(node.func.id)

    assert not (called & forbidden), (
        f"годинник усередині лічильника: {sorted(called & forbidden)} — перевірка ліміту "
        "проходитиме о 12:00:59 і падатиме о 12:01:00, і це мигтливість сервісу, а не тесту"
    )

    for name in ("add", "total"):
        signature = inspect.signature(getattr(InMemory, name))
        assert signature.parameters["now"].kind is inspect.Parameter.KEYWORD_ONLY, name


def check_the_factory_branches_on_profile_and_nothing_else() -> None:
    """ВІДМОВА · фабрика: розгалуження за профілем живе тут і більше ніде"""
    local = get_counters(Settings(profile=LOCAL))
    assert isinstance(local, InMemory), type(local)

    # Готовий клієнт переважає профіль: інакше перевірку контракту довелось би вмикати
    # змінною оточення, а це вже конфігурація тесту, а не тест.
    injected = get_counters(Settings(profile=LOCAL), client=FakeStore())
    assert isinstance(injected, Shared), type(injected)

    import ast
    from pathlib import Path

    # Розбір AST, а не пошук у тексті: перша редакція грепала свій же файл і червоніла
    # на власному твердженні про профіль. Перевірка про код має дивитись на код.
    #
    # `check.py` виключено навмисно: перевірки **мають** говорити про профілі — це їхня
    # робота. Правило стосується коду, що виконується у сервісі.
    names = {"profile", "PROD", "LOCAL"}
    for module in Path(__file__).parent.glob("*.py"):
        if module.name == "check.py":
            continue
        offenders = []
        for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Compare):
                continue
            parts = [node.left, *node.comparators]
            for part in parts:
                seen = getattr(part, "id", None) or getattr(part, "attr", None)
                if seen in names:
                    offenders.append(f"рядок {node.lineno}")
        assert not offenders, (
            f"{module.name}: розгалуження за профілем ({', '.join(offenders)}) — воно живе "
            "лише у фабриках shared/ (CONVENTIONS.md)"
        )


def check_the_shared_counter_needs_no_container_to_be_checked() -> None:
    """counters: контракт спільного сховища перевіряється офлайн"""
    # Не церемонія: без цього твердження найважливіша перевірка етапу існувала б лише там,
    # де є Docker, — тобто не існувала б ані в CI без extras, ані в читача до розгортання.
    store = FakeStore()
    counter = Shared(store)
    counter.add("k", 1.5, now=NOW, window=MINUTE)

    assert store.data, "підробка нічого не зберегла — перевірка контракту нічого не доводить"
    assert store.expirations, "термін життя ключа не встановлено — сховище ростиме вічно"


# --- сховище фактів: один контракт, дві реалізації -------------------------------------


def _database():
    """Зʼєднання з базою або `NotVerified`, якщо її немає.

    Третій стан замість падіння. Перевірка, що потребує контейнера, має сказати про це
    словами — інакше читач без Docker бачить червоне й не розуміє, чи він щось зламав.
    """
    settings = Settings.load()
    url = settings.database_url or "postgresql://agentic:agentic@127.0.0.1:5432/agentic"
    try:
        import psycopg
    except ImportError as error:
        raise NotVerified(f"psycopg не встановлено: {error}") from error
    try:
        return psycopg.connect(url, connect_timeout=2)
    except Exception as error:  # noqa: BLE001 — будь-яка відмова означає «бази немає»
        raise NotVerified(
            f"база недоступна ({type(error).__name__}). Підніми: "
            "docker compose -f deploy/docker-compose.yml up -d --wait"
        ) from error


def _fresh(connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("TRUNCATE facts")
    connection.commit()


def _both_stores(connection, tmp: str) -> list:
    return [FileStore(Path(tmp) / "m.jsonl"), DatabaseStore(connection)]


def check_both_fact_stores_answer_the_same_way() -> None:
    """ВІДМОВА · сховище: файл і база дають однакову відповідь на однакових даних"""
    with _database() as connection, tempfile.TemporaryDirectory() as tmp:
        _fresh(connection)
        for store in _both_stores(connection, tmp):
            store.remember(_fact("olena", "address", "Доставляти замовлення на Хрещатик 22"))
            store.remember(_fact("olena", "weather", "Учора був дощ"))

            context = store.context_for("olena", QUESTION, now=NOW)
            texts = [fact["text"] for fact in context.facts]

            assert texts == ["Доставляти замовлення на Хрещатик 22"], f"{store.name}: {texts}"
            reasons = [skip.reason for skip in context.skipped]
            assert any("оцінка" in reason for reason in reasons), f"{store.name}: {reasons}"


def check_the_owner_filter_is_a_query_condition_in_the_database() -> None:
    """ВІДМОВА · сховище: чужий рядок не залишає бази — фільтр у запиті, не в памʼяті"""
    with _database() as connection:
        _fresh(connection)
        store = DatabaseStore(connection)
        store.remember(_fact("olena", "address", "Доставляти замовлення на Хрещатик 22"))
        store.remember(_fact("petro", "address", "Куди доставляти замовлення — на Банкову 11"))

        mine = store._facts_of("olena")
        everyone = store.all_facts()

    assert len(everyone) == 2, everyone
    assert [f.owner for f in mine] == ["olena"], mine
    assert not any("Банков" in f.text for f in mine), (
        "чужий факт приїхав із бази. Файлова реалізація читає всі записи й фільтрує в "
        "памʼяті — це борг, названий в ADR-0004 етапу 5. База має закрити його умовою "
        "запиту, інакше переїзд не дав нічого, крім іншого файлу"
    )


def check_neither_store_leaks_and_both_still_answer() -> None:
    """ВІДМОВА · дзеркальна: чуже не дійшло І своє дійшло — на ОБОХ реалізаціях"""
    with _database() as connection, tempfile.TemporaryDirectory() as tmp:
        _fresh(connection)
        for store in _both_stores(connection, tmp):
            store.remember(_fact("olena", "address", "Доставляти замовлення на Хрещатик 22"))
            for i in range(3):
                store.remember(
                    _fact("petro", f"addr{i}", "Куди доставляти замовлення — на Банкову 11")
                )

            hers = [f["text"] for f in store.context_for("olena", QUESTION, now=NOW).facts]
            his = [f["text"] for f in store.context_for("petro", QUESTION, now=NOW).facts]

            assert not any("Банков" in text for text in hers), f"{store.name}: витік — {hers}"
            assert any("Хрещатик" in text for text in hers), (
                f"{store.name}: власний факт зник. Витоку немає; відповіді теж немає — "
                "це та сама вада, що на етапі 5, і вона не ловиться перевіркою на витік"
            )
            assert any("Банков" in text for text in his), f"{store.name}: {his}"


def check_the_database_refuses_two_active_facts_on_one_topic() -> None:
    """ВІДМОВА · міграція: правило «один активний факт на тему» тримає сховище, не код"""
    with _database() as connection:
        _fresh(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO facts (owner, topic, text, stored_at, status)"
                " VALUES (%s, %s, %s, %s, 'active')",
                ("olena", "address", "перший", NOW),
            )
        connection.commit()

        # Обхід сховища навмисно: перевіряється саме база, а не код, що її береже.
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO facts (owner, topic, text, stored_at, status)"
                    " VALUES (%s, %s, %s, %s, 'active')",
                    ("olena", "address", "другий", NOW + 1),
                )
            connection.commit()
        except Exception:  # noqa: BLE001 — саме на це й розраховано
            connection.rollback()
        else:
            raise AssertionError(
                "дві активні адреси одного власника лягли в базу. У файлі це тримався код; "
                "тут має тримати сховище — інакше правило переживе рівно до наступного "
                "автора запису"
            )


def check_the_database_refuses_a_replaced_fact_without_a_time() -> None:
    """ВІДМОВА · міграція: статус `replaced` без часу заміни відхиляється сховищем"""
    with _database() as connection:
        _fresh(connection)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO facts (owner, topic, text, stored_at, status)"
                    " VALUES (%s, %s, %s, %s, 'replaced')",
                    ("olena", "address", "без часу", NOW),
                )
            connection.commit()
        except Exception:  # noqa: BLE001
            connection.rollback()
        else:
            raise AssertionError(
                "запис `replaced` без `replaced_at` прийнято. На етапі 5 такий рядок валив "
                "`describe_skip` виключенням TypeError повз ValueError — тобто вимикав усю "
                "памʼять власника"
            )


def check_stage_five_is_untouched_by_the_move() -> None:
    """ВІДМОВА · переїзд не змінив жодного рядка етапу 5"""
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--name-only", "stage-05", "--", "stages/s05_memory"],
        cwd=Path(__file__).resolve().parent.parent.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise NotVerified(f"теґ stage-05 недоступний: {result.stderr.strip()}")

    changed = [line for line in result.stdout.splitlines() if line.strip()]
    assert not changed, (
        f"етап 5 змінено: {changed}. C-1 забороняє правки без ADR, а ADR-0004 обіцяв, що "
        "переїзд обійдеться без них. Якщо правка справді потрібна — це не деталь переїзду, "
        "а спростування тези етапу 5, і воно потребує запису"
    )


# --- три воротарі -----------------------------------------------------------------------

KEY = "test-key-0001"
OTHER_KEY = "test-key-0002"


def _settings(**kwargs) -> Settings:
    base = {"api_keys": [KEY, OTHER_KEY], "rate_limit_per_minute": 3, "budget_usd_per_day": 1.0}
    return Settings(**{**base, **kwargs})


def check_an_unknown_key_is_refused_before_anything_else() -> None:
    """ВІДМОВА · воротар: невпізнаний ключ відхиляється й не доходить до лічильників"""
    counters = InMemory()
    verdict = admit("не той ключ", counters, _settings(), now=NOW)

    assert not verdict.allowed and verdict.kind == UNAUTHENTICATED, verdict
    assert not verdict.owner, "невпізнаному ключу приписано власника"
    assert counters.total(f"rate:{owner_of('не той ключ')}", now=NOW, window=MINUTE) == 0.0, (
        "відхилений запит витратив квоту. Тоді анонім вичерпує ліміт того, ким він не є"
    )


def check_a_known_key_gets_through_and_carries_its_owner() -> None:
    """ВІДМОВА · дзеркальна: впізнаний ключ ДОХОДИТЬ — воротар не глухий"""
    verdict = admit(KEY, InMemory(), _settings(), now=NOW)

    assert verdict.allowed and verdict.kind == OK, verdict
    assert verdict.owner == owner_of(KEY), verdict
    # Без цього твердження воротар, що не пускає нікого, задовольняє перевірку вище
    # повністю — і при цьому зламаний. Курс ловив цю форму на етапах 1, 2, 3 і 5.


def check_the_key_never_appears_in_what_is_written_down() -> None:
    """ВІДМОВА · воротар: ключ не трапляється ні у вердикті, ні в ідентифікаторі власника"""
    verdict = admit(KEY, InMemory(), _settings(), now=NOW)
    written = f"{verdict.owner} {verdict.reason} {verdict.kind}"

    assert KEY not in written, f"ключ у тому, що записують: {written!r}"
    assert verdict.owner != KEY and len(verdict.owner) == 16, verdict.owner

    # Похідний ідентифікатор має бути стабільним і різним для різних ключів — інакше він
    # або не годиться як ключ лічильника, або зливає двох власників в одного.
    assert owner_of(KEY) == owner_of(KEY)
    assert owner_of(KEY) != owner_of(OTHER_KEY)


def check_the_refusal_does_not_say_whether_the_key_exists() -> None:
    """ВІДМОВА · воротар: відмова однакова для невідомого й для відкликаного ключа"""
    empty = admit(KEY, InMemory(), _settings(api_keys=[]), now=NOW)
    unknown = admit("зовсім інший", InMemory(), _settings(), now=NOW)

    assert empty.kind == unknown.kind and empty.reason == unknown.reason, (
        f"відмови різні: {empty.reason!r} проти {unknown.reason!r}. Різниця у відповіді — "
        "це оракул: перебирай, доки текст не зміниться"
    )


def check_the_rate_limit_refuses_before_the_model() -> None:
    """ВІДМОВА · воротар: понад ліміт — відмова з часом повтору, і вона не про автентифікацію"""
    counters = InMemory()
    settings = _settings()
    for _ in range(settings.rate_limit_per_minute):
        assert admit(KEY, counters, settings, now=NOW).allowed

    verdict = admit(KEY, counters, settings, now=NOW)
    assert not verdict.allowed and verdict.kind == RATE_LIMITED, verdict
    assert verdict.retry_after == MINUTE, verdict
    assert verdict.kind != UNAUTHENTICATED, "ліміт і автентифікація злилися в одну відмову"

    # Вікно минуло — той самий клієнт знову проходить. Ліміт, що не відпускає, це бан.
    assert admit(KEY, counters, settings, now=NOW + MINUTE + 1).allowed


def check_one_clients_limit_does_not_stop_another() -> None:
    """ВІДМОВА · воротар: лічильник на власника, а не на сервіс"""
    counters = InMemory()
    settings = _settings()
    for _ in range(settings.rate_limit_per_minute + 1):
        admit(KEY, counters, settings, now=NOW)

    assert admit(OTHER_KEY, counters, settings, now=NOW).allowed, (
        "другий клієнт відхилений через першого. Спільний лічильник задовольняє «понад "
        "ліміт відхилено» дослівно й робить одного клієнта здатним зупинити всіх"
    )


def check_an_exhausted_budget_stops_the_call_and_says_so() -> None:
    """ВІДМОВА · воротар: вичерпаний бюджет — окрема відмова, не ліміт і не автентифікація"""
    counters = InMemory()
    settings = _settings()
    charge(owner_of(KEY), counters, settings.budget_usd_per_day, now=NOW)

    verdict = admit(KEY, counters, settings, now=NOW)
    assert not verdict.allowed and verdict.kind == BUDGET_EXHAUSTED, verdict
    assert verdict.kind not in (RATE_LIMITED, UNAUTHENTICATED), verdict
    assert "$" in verdict.reason, verdict.reason
    assert verdict.retry_after is None, (
        "бюджет назвав час повтору. Вичерпані гроші не зʼявляються самі за хвилину, і "
        "порада «спробуй пізніше» тут неправдива"
    )


def check_spending_is_counted_or_the_guard_never_fires() -> None:
    """ВІДМОВА · дзеркальна: витрати зростають — запобіжник, що не рахує, не спрацює"""
    counters = InMemory()
    owner = owner_of(KEY)

    assert charge(owner, counters, 0.10, now=NOW) == 0.10
    assert charge(owner, counters, 0.15, now=NOW + 1) == 0.25
    assert counters.total(f"spend:{owner}", now=NOW + 2, window=DAY) == 0.25

    # І межа справді спрацьовує на накопиченому, а не на одному виклику.
    settings = _settings(budget_usd_per_day=0.20)
    assert not admit(KEY, counters, settings, now=NOW + 2).allowed


def check_the_guards_run_in_the_declared_order() -> None:
    """ВІДМОВА · воротар: порядок «хто -> скільки -> за чий рахунок» і є механізмом"""
    counters = InMemory()
    settings = _settings()
    # Вичерпані і ліміт, і бюджет — але ключ невідомий. Має перемогти автентифікація.
    charge(owner_of("чужий"), counters, 99.0, now=NOW)
    assert admit("чужий", counters, settings, now=NOW).kind == UNAUTHENTICATED

    # Вичерпані ліміт і бюджет одночасно в законного власника — має перемогти ліміт:
    # він дешевший і стоїть раніше.
    owner = owner_of(KEY)
    charge(owner, counters, 99.0, now=NOW)
    for _ in range(settings.rate_limit_per_minute):
        counters.add(f"rate:{owner}", 1, now=NOW, window=MINUTE)

    assert admit(KEY, counters, settings, now=NOW).kind == RATE_LIMITED, (
        "бюджет спрацював раніше за ліміт — тоді сервіс рахує витрати тих, кого однаково "
        "відхилить, і порядок воротарів перестає бути рішенням"
    )


CHECKS = [
    check_both_counters_answer_the_same_way_within_one_instance,
    check_the_window_forgets_what_fell_out_of_it,
    check_two_instances_on_one_store_see_one_number,
    check_two_in_memory_counters_do_not_see_each_other,
    check_time_is_passed_in_never_read_from_the_clock,
    check_the_factory_branches_on_profile_and_nothing_else,
    check_the_shared_counter_needs_no_container_to_be_checked,
    check_both_fact_stores_answer_the_same_way,
    check_the_owner_filter_is_a_query_condition_in_the_database,
    check_neither_store_leaks_and_both_still_answer,
    check_the_database_refuses_two_active_facts_on_one_topic,
    check_the_database_refuses_a_replaced_fact_without_a_time,
    check_stage_five_is_untouched_by_the_move,
    check_an_unknown_key_is_refused_before_anything_else,
    check_a_known_key_gets_through_and_carries_its_owner,
    check_the_key_never_appears_in_what_is_written_down,
    check_the_refusal_does_not_say_whether_the_key_exists,
    check_the_rate_limit_refuses_before_the_model,
    check_one_clients_limit_does_not_stop_another,
    check_an_exhausted_budget_stops_the_call_and_says_so,
    check_spending_is_counted_or_the_guard_never_fires,
    check_the_guards_run_in_the_declared_order,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 6 · Platform")


if __name__ == "__main__":
    raise SystemExit(main())
