"""Перевірки етапу 6.

    python -m stages.s06_platform.check

Працюють **офлайн і без контейнерів**. Те, що справді потребує Docker, позначається
`НЕ ПЕРЕВІРЕНО` — третій стан, і він не дорівнює зеленому.
"""

from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from shared.check_runner import (
    NotVerified,
    code_mentions,
    require_intact_source,
    run_checks,
)
from shared.config import LOCAL, ConfigError, Settings
from shared.counters import DAY, MINUTE, InMemory, Shared, get_counters
from shared.factstore import DatabaseStore, FileStore
from shared.fake_llm import FakeLLM, text
from shared.trace import iter_steps, trace_run
from stages.s05_memory.facts import Fact
from stages.s06_platform.app import Service
from stages.s06_platform.fake_store import FakeStore
from stages.s06_platform.guards import (
    BUDGET_EXHAUSTED,
    OK,
    RATE_LIMITED,
    UNAUTHENTICATED,
    admit,
    charge,
    owner_of,
)
from stages.s06_platform.intent import KNOWLEDGE, MATH, ORDERS, classify
from stages.s06_platform.jobs import (
    INSIDE,
    SEPARATE,
    Ledger,
    Scheduler,
    Worker,
    count_expired,
    run_interval,
)
from stages.s06_platform.observe import DOWN, UP, Dependency, Health, Metrics
from stages.s06_platform.run import main as demo_main

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії.
BUDGET_SECONDS = 60

NEWLINE = chr(10)
NOW = 1_700_000_000.0
QUESTION = "куди доставляти замовлення"


def _script_for(branch: str) -> list:
    """Сценарій підробки: класифікація плюс те, що робить обрана гілка."""
    if branch in (ORDERS, MATH):
        # Гілка йде в граф етапу 3: маршрут, спеціаліст, оцінка.
        return [
            text(branch),
            text(branch if branch != MATH else "math"),
            text("Відповідь спеціаліста."),
            text("так"),
        ]
    return [text(branch), text("Відповідь агента.")]


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

        # ТОЙ САМИЙ час і ТА САМА сума тричі. Дві події однієї миті — це дві події, і
        # реалізація на множині схильна вважати їх однією: перша редакція складала член
        # із часу й суми, тож шість запитів за мить проходили при межі три. Фікстура,
        # що щоразу збільшує час, цього не бачить — а продакшн бачить під навантаженням.
        for _ in range(3):
            counter.add("same", 1, now=NOW, window=MINUTE)
        assert counter.total("same", now=NOW, window=MINUTE) == 3.0, (
            f"{counter.name}: три однакові події за одну мить дали "
            f"{counter.total('same', now=NOW, window=MINUTE)} — лічильник недорахував"
        )


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
    """FAILURE · головна перевірка етапу: два екземпляри бачать ОДИН лічильник"""
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
    """FAILURE · дзеркальна: процесо-локальний лічильник НЕ спільний — і це вправа, не вада"""
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
    """FAILURE · counters: рішення про вікно не залежить від системного годинника"""
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
    """FAILURE · фабрика: розгалуження за профілем живе тут і більше ніде"""
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
    """FAILURE · сховище: файл і база дають однакову відповідь на однакових даних"""
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
    """FAILURE · сховище: чужий рядок не залишає бази — фільтр у запиті, не в памʼяті"""
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
    """FAILURE · дзеркальна: чуже не дійшло І своє дійшло — на ОБОХ реалізаціях"""
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
    """FAILURE · міграція: правило «один активний факт на тему» тримає сховище, не код"""
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
    """FAILURE · міграція: статус `replaced` без часу заміни відхиляється сховищем"""
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


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Правки етапу 5 після його теґа, кожна — з ADR, який її ухвалив. Порожній словник
# означає «жодної»; запис означає рішення, а не виняток.
RECORDED_EDITS: dict[str, str] = {
    # Переклад репозиторію англійською: маркер `ВІДМОВА ·` став `FAILURE ·` в один прохід,
    # бо його читають `check_runner`, перевірки покриття кожного етапу й `article_check`.
    # Тексту стало інакше, поведінки — ні.
    "stages/s05_memory/check.py": "docs/adr/0008-english-is-the-only-language-in-the-repository.md",
}


def check_stage_five_is_untouched_by_the_move() -> None:
    """FAILURE · переїзд не змінив жодного рядка етапу 5"""
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
    unrecorded = [name for name in changed if name not in RECORDED_EDITS]
    assert not unrecorded, (
        f"етап 5 змінено: {unrecorded}. C-1 забороняє правки без ADR, а ADR-0004 обіцяв, що "
        "переїзд обійдеться без них. Якщо правка справді потрібна — це не деталь переїзду, "
        "а спростування тези етапу 5, і воно потребує запису"
    )

    # Дозвіл видає не список, а ADR: файл, названий тут, мусить мати рішення, яке існує.
    # Інакше «записано» вироджується в «вписано в список», і перевірка втрачає зуби.
    for name, adr in RECORDED_EDITS.items():
        if name not in changed:
            continue
        assert (REPO_ROOT / adr).exists(), f"{name}: ADR {adr} не існує"


# --- три воротарі -----------------------------------------------------------------------

KEY = "test-key-0001"
OTHER_KEY = "test-key-0002"


def _settings(**kwargs) -> Settings:
    base = {"api_keys": [KEY, OTHER_KEY], "rate_limit_per_minute": 3, "budget_usd_per_day": 1.0}
    return Settings(**{**base, **kwargs})


def check_an_unknown_key_is_refused_before_anything_else() -> None:
    """FAILURE · воротар: невпізнаний ключ відхиляється й не доходить до лічильників"""
    counters = InMemory()
    verdict = admit("не той ключ", counters, _settings(), now=NOW)

    assert not verdict.allowed and verdict.kind == UNAUTHENTICATED, verdict
    assert not verdict.owner, "невпізнаному ключу приписано власника"
    assert counters.total(f"rate:{owner_of('не той ключ')}", now=NOW, window=MINUTE) == 0.0, (
        "відхилений запит витратив квоту. Тоді анонім вичерпує ліміт того, ким він не є"
    )


def check_a_known_key_gets_through_and_carries_its_owner() -> None:
    """FAILURE · дзеркальна: впізнаний ключ ДОХОДИТЬ — воротар не глухий"""
    verdict = admit(KEY, InMemory(), _settings(), now=NOW)

    assert verdict.allowed and verdict.kind == OK, verdict
    assert verdict.owner == owner_of(KEY), verdict
    # Без цього твердження воротар, що не пускає нікого, задовольняє перевірку вище
    # повністю — і при цьому зламаний. Курс ловив цю форму на етапах 1, 2, 3 і 5.


def check_the_key_never_appears_in_what_is_written_down() -> None:
    """FAILURE · воротар: ключ не трапляється ні у вердикті, ні в ідентифікаторі власника"""
    verdict = admit(KEY, InMemory(), _settings(), now=NOW)
    written = f"{verdict.owner} {verdict.reason} {verdict.kind}"

    assert KEY not in written, f"ключ у тому, що записують: {written!r}"
    assert verdict.owner != KEY and len(verdict.owner) == 16, verdict.owner

    # Похідний ідентифікатор має бути стабільним і різним для різних ключів — інакше він
    # або не годиться як ключ лічильника, або зливає двох власників в одного.
    assert owner_of(KEY) == owner_of(KEY)
    assert owner_of(KEY) != owner_of(OTHER_KEY)


def check_the_refusal_does_not_say_whether_the_key_exists() -> None:
    """FAILURE · воротар: відмова однакова для невідомого й для відкликаного ключа"""
    empty = admit(KEY, InMemory(), _settings(api_keys=[]), now=NOW)
    unknown = admit("зовсім інший", InMemory(), _settings(), now=NOW)

    assert empty.kind == unknown.kind and empty.reason == unknown.reason, (
        f"відмови різні: {empty.reason!r} проти {unknown.reason!r}. Різниця у відповіді — "
        "це оракул: перебирай, доки текст не зміниться"
    )


def check_the_key_is_compared_in_constant_time() -> None:
    """FAILURE · воротар: ключ звіряється сталим порівнянням, а не `==`"""
    import ast
    import inspect

    from stages.s06_platform import guards

    # Структурне твердження, а не часове. Заміряти час порівняння в перевірці означало б
    # писати мигтливий тест: різниця в наносекундах, а машина під навантаженням.
    # Тут стверджується наявність механізму — і цього досить, бо механізм або є, або ні.
    tree = ast.parse(inspect.getsource(guards.authenticate))
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    } | {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "compare_digest" in called, (
        f"звірка ключа не використовує сталого порівняння: {sorted(called)}. Звичайне "
        "`==` завершується на першому розбіжному байті, тобто час відповіді розповідає "
        "довжину спільного префікса — це підбір ключа по одному символу"
    )

    # І дзеркально: механізм не лише є, а й працює на не-ASCII ключі. `compare_digest`
    # на рядках із кирилицею кидає TypeError, тож порівнювати треба байти.
    verdict = admit("ключ кирилицею", InMemory(), _settings(), now=NOW)
    assert verdict.kind == UNAUTHENTICATED, verdict


def check_the_rate_limit_refuses_before_the_model() -> None:
    """FAILURE · воротар: понад ліміт — відмова з часом повтору, і вона не про автентифікацію"""
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
    """FAILURE · воротар: лічильник на власника, а не на сервіс"""
    counters = InMemory()
    settings = _settings()
    for _ in range(settings.rate_limit_per_minute + 1):
        admit(KEY, counters, settings, now=NOW)

    assert admit(OTHER_KEY, counters, settings, now=NOW).allowed, (
        "другий клієнт відхилений через першого. Спільний лічильник задовольняє «понад "
        "ліміт відхилено» дослівно й робить одного клієнта здатним зупинити всіх"
    )


def check_an_exhausted_budget_stops_the_call_and_says_so() -> None:
    """FAILURE · воротар: вичерпаний бюджет — окрема відмова, не ліміт і не автентифікація"""
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
    """FAILURE · дзеркальна: витрати зростають — запобіжник, що не рахує, не спрацює"""
    counters = InMemory()
    owner = owner_of(KEY)

    assert charge(owner, counters, 0.10, now=NOW) == 0.10
    assert charge(owner, counters, 0.15, now=NOW + 1) == 0.25
    assert counters.total(f"spend:{owner}", now=NOW + 2, window=DAY) == 0.25

    # І межа справді спрацьовує на накопиченому, а не на одному виклику.
    settings = _settings(budget_usd_per_day=0.20)
    assert not admit(KEY, counters, settings, now=NOW + 2).allowed


def check_the_guards_run_in_the_declared_order() -> None:
    """FAILURE · воротар: порядок «хто -> скільки -> за чий рахунок» і є механізмом"""
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


# --- класифікатор наміру ------------------------------------------------------------------

# Складені запити: кожен стосується ДВОХ гілок одночасно. Класифікатор обере одну, і друга
# половина питання лишиться без відповіді. Набір існує, щоб межу можна було назвати числом.
MIXED = (
    ("поверніть гроші за ord_4471 — і скільки днів це триває", {ORDERS, KNOWLEDGE}),
    ("статус ord_9001 і скільки я загалом витратив", {ORDERS, MATH}),
    ("скільки коштує доставка й чи входить вона в суму знижки", {KNOWLEDGE, MATH}),
)

SINGLE = (
    ("який статус замовлення ord_4471", ORDERS),
    ("скільки днів на повернення товару", KNOWLEDGE),
    ("скільки буде 1200 плюс 340", MATH),
)


def check_three_questions_take_three_branches() -> None:
    """intent: три різні запити дають три різні гілки"""
    seen = []
    for question, expected in SINGLE:
        client = FakeLLM(script=[text(expected)])
        intent = classify(question, client=client)
        assert intent.branch == expected, f"{question!r} -> {intent.branch}"
        assert intent.certain, intent
        seen.append(intent.branch)

    assert len(set(seen)) == 3, f"гілок вийшло {len(set(seen))}, а не три: {seen}"


def check_the_branch_reaches_the_trace_before_any_work() -> None:
    """intent: гілка потрапляє у крок трейсу разом із тим, що сказала модель"""
    intent = classify("який статус ord_4471", client=FakeLLM(script=[text("orders")]))
    step = intent.as_step()

    assert step["branch"] == ORDERS, step
    assert step["certain"] is True, step
    assert step["model_said"] == "orders", (
        "у трейсі немає того, ЩО сказала модель. Без цього неможливо відрізнити «модель "
        "обрала orders» від «ми не впізнали відповідь і взяли запасну гілку»"
    )


def check_a_wordy_answer_still_classifies() -> None:
    """intent: багатослівна відповідь моделі не стає відмовою"""
    for said in ("orders.", '"orders"', "Категорія: orders", "ORDERS"):
        intent = classify("статус ord_1", client=FakeLLM(script=[text(said)]))
        assert intent.branch == ORDERS and intent.certain, (said, intent)


def check_an_unrecognised_answer_falls_back_to_the_safest_branch() -> None:
    """FAILURE · intent: невпізнана відповідь — запасна гілка, а не виняток"""
    intent = classify("щось геть інше", client=FakeLLM(script=[text("гадки не маю")]))

    assert intent.branch == KNOWLEDGE, intent
    assert not intent.certain, (
        "невпізнану відповідь позначено як певну. Тоді трейс каже, що модель обрала "
        "knowledge, хоча вона не обирала нічого"
    )
    assert intent.said == "гадки не маю", intent


def check_the_mixed_question_limit_is_a_measured_number() -> None:
    """FAILURE · intent: межа класифікатора названа числом, а не словами"""
    # Модель відповідає першою з двох доречних гілок — саме так поводиться справжня:
    # вона обирає одну, бо її про одну й питали.
    missed = 0
    for question, applicable in MIXED:
        first = sorted(applicable)[0]
        intent = classify(question, client=FakeLLM(script=[text(first)]))
        assert intent.branch in applicable, (question, intent.branch)
        # Друга доречна гілка лишилась без відповіді — це і є ціна класифікатора.
        missed += len(applicable) - 1

    assert missed == len(MIXED), (
        f"складених запитів {len(MIXED)}, недоотриманих гілок {missed} — числа розійшлись"
    )
    assert len(MIXED) == 3, (
        "набір складених запитів змінився. Урок називає його розмір числом, тож набір і "
        "проза мають мінятись разом"
    )


def check_there_is_no_fallback_when_the_budget_is_gone() -> None:
    """FAILURE · intent: вичерпаний бюджет не вмикає класифікації без моделі"""
    import inspect

    from stages.s06_platform import intent as module

    # `code_mentions`, а не пошук у тексті: модуль **пише** про бюджет у docstring, бо
    # саме там пояснює, чому запасного шляху немає. Перевірка про код дивиться на код.
    found = code_mentions(inspect.getsource(module), {"budget", "бюджет", "spend"})
    assert not found, (
        f"класифікатор знає про бюджет: {found}. ADR-0001 відхилив запасний шлях: "
        "запобіжник, який у цьому стані відповідає, робить відмову мʼякою рівно там, "
        "де вона має бути жорсткою"
    )

    # І дзеркально: класифікація СПРАВДІ потребує моделі, тобто без неї вона не мовчазна.
    exhausted = FakeLLM(script=[])
    try:
        classify("будь-що", client=exhausted)
    except Exception as error:  # noqa: BLE001 — саме на це й розраховано
        assert "сценарій" in str(error).lower() or "script" in str(error).lower(), error
    else:
        raise AssertionError(
            "класифікація відбулась без виклику моделі — тоді гілка обирається чимось, "
            "чого немає в коді"
        )


# --- зшивання, стан і метрики -------------------------------------------------------------


def _service(tmp: str, tracer, *, script: list, settings=None):
    """Сервіс на файловому сховищі й підробленій моделі. Ні мережі, ні контейнерів."""
    return Service(
        settings=settings or _settings(),
        counters=InMemory(),
        store=FileStore(Path(tmp) / "m.jsonl"),
        tracer=tracer,
        client=FakeLLM(script=script),
    )


def _steps(path: Path, kind: str) -> list[dict]:
    return [step for step in iter_steps(path) if step["kind"] == kind]


def check_three_requests_take_three_branches() -> None:
    """integration · три різні запити йдуть трьома різними гілками"""
    asked = [
        ("який статус замовлення ord_4471", ORDERS),
        ("скільки днів на повернення товару", KNOWLEDGE),
        ("скільки буде 1200 плюс 340", MATH),
    ]
    branches = []
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        for question, expected in asked:
            with trace_run("s06", path=path, stage="s06") as tracer:
                service = _service(tmp, tracer, script=_script_for(expected))
                answer = service.ask(KEY, question, now=NOW)
            assert answer.ok, answer
            branches.append(answer.branch)
            assert answer.branch == expected, (question, answer.branch)

        intents = _steps(path, "intent")

    assert len(set(branches)) == 3, f"гілок {len(set(branches))}, а не три: {branches}"
    # Гілка видна у ТРЕЙСІ, а не лише у відповіді. Формулювання відповіді нічого не доводить:
    # три різні тексти можуть прийти однією гілкою.
    assert {step["branch"] for step in intents} == {ORDERS, KNOWLEDGE, MATH}, intents


def check_the_trace_names_every_step_and_its_reason() -> None:
    """integration · трейс несе кроки сервісу по порядку, і кожен із причиною"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("s06", path=path, stage="s06") as tracer:
            service = _service(tmp, tracer, script=_script_for(KNOWLEDGE))
            answer = service.ask(KEY, "скільки днів на повернення", now=NOW)
        recorded = list(iter_steps(path))

    mine = [step for step in recorded if step.get("trace_ref") == answer.trace_id]
    order = [step["kind"] for step in mine]

    assert order[:4] == ["received", "guard", "intent", "memory"], (
        f"порядок кроків {order}. Трейс має починатися з ПРИЙОМУ запиту, а не з рішення "
        "про нього: інакше зникає те, про що рішення ухвалене"
    )
    assert "done" in order, order

    received = next(step for step in mine if step["kind"] == "received")
    assert received["chars"] > 0, received

    guard = next(step for step in mine if step["kind"] == "guard")
    assert guard["verdict"] == OK and guard["owner"] == owner_of(KEY), (
        f"крок воротаря не каже, ЩО він вирішив: {guard}. Поле не можна назвати "
        "`kind` — воно вже зайняте родом самого кроку, і трейсер відхилить виклик"
    )
    memory = next(step for step in mine if step["kind"] == "memory")
    assert "skipped" in memory, (
        "у кроці памʼяті немає причин відкидання. Етап 5 їх повертає у Context.skipped і "
        "у трейс не пише — перенести їх має сервіс, бо це його рішення (ADR-0005)"
    )
    # Трейс знаходиться за ідентифікатором, а не «десь у файлі».
    assert answer.trace_id and len(mine) >= 4, (answer.trace_id, len(mine))


def check_a_refused_request_leaves_only_its_refusal() -> None:
    """FAILURE · integration · відхилений запит не лишає у трейсі нічого, крім відмови"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("s06", path=path, stage="s06") as tracer:
            service = _service(tmp, tracer, script=[])
            answer = service.ask("чужий ключ", "будь-що", now=NOW)
        recorded = list(iter_steps(path))

    assert not answer.ok and answer.kind == UNAUTHENTICATED, answer
    mine = [step for step in recorded if step.get("trace_ref") == answer.trace_id]
    assert [step["kind"] for step in mine] == ["received", "guard"], (
        f"у трейсі відхиленого запиту є зайве: {[s['kind'] for s in mine]}. Прийом і "
        "відмова — і нічого більше. Порожній сценарій моделі означає, що жодного виклику "
        "не сталося: інакше FakeLLM упав би"
    )


def check_the_key_never_reaches_the_trace_or_the_answer() -> None:
    """FAILURE · integration · ключ не трапляється ні у трейсі, ні у відповіді"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("s06", path=path, stage="s06") as tracer:
            service = _service(tmp, tracer, script=_script_for(KNOWLEDGE))
            answer = service.ask(KEY, "скільки днів на повернення", now=NOW)
        written = path.read_text(encoding="utf-8")

    assert KEY not in written, "ключ у файлі трейсу — тобто у файлі, який читає налагоджувач"
    assert KEY not in f"{answer.text} {answer.trace_id} {answer.branch}", answer
    assert owner_of(KEY) in written, (
        "у трейсі немає навіть похідного власника — тоді запит неможливо привʼязати ні до "
        "кого, і ключ прибрано ціною відповідальності"
    )


def check_two_owners_do_not_see_each_others_memory_through_the_service() -> None:
    """FAILURE · integration · два ключі — дві памʼяті; і кожна своя доходить"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        store = FileStore(Path(tmp) / "m.jsonl")
        store.remember(_fact(owner_of(KEY), "address", "Доставляти замовлення на Хрещатик 22"))
        store.remember(
            _fact(owner_of(OTHER_KEY), "address", "Куди доставляти замовлення — на Банкову 11")
        )

        seen = {}
        for key in (KEY, OTHER_KEY):
            with trace_run("s06", path=path, stage="s06") as tracer:
                service = Service(
                    settings=_settings(),
                    counters=InMemory(),
                    store=store,
                    tracer=tracer,
                    client=FakeLLM(script=_script_for(KNOWLEDGE)),
                )
                seen[key] = service.ask(key, QUESTION, now=NOW).facts_used

    assert any("Хрещатик" in text for text in seen[KEY]), seen[KEY]
    assert not any("Банков" in text for text in seen[KEY]), f"витік: {seen[KEY]}"
    assert any("Банков" in text for text in seen[OTHER_KEY]), (
        f"власна памʼять другого власника не дійшла: {seen[OTHER_KEY]}. Витоку немає; "
        "відповіді теж немає — і перевірка на витік цього не бачить"
    )


def check_health_names_each_dependency_separately() -> None:
    """FAILURE · стан: несправна залежність названа, і сервіс не рапортує «живий»"""

    def broken() -> None:
        raise ConnectionError("postgresql://agentic:agentic@10.0.0.1:5432/agentic")

    health = Health(
        dependencies=[
            Dependency(name="store", probe=lambda: None),
            Dependency(name="counters", probe=broken),
        ]
    )
    report = health.report()

    assert report["status"] == DOWN, report
    assert report["dependencies"]["store"]["status"] == UP, report
    assert report["dependencies"]["counters"]["status"] == DOWN, report

    # Причина — тип помилки, не її текст: текст несе адресу, користувача й порт, а стан
    # читає той, у кого ключа немає.
    written = str(report)
    assert "10.0.0.1" not in written and "agentic" not in written, (
        f"стан розкриває рядок підключення: {written}"
    )
    assert report["dependencies"]["counters"]["reason"] == "ConnectionError", report


def check_a_healthy_service_reports_healthy() -> None:
    """FAILURE · дзеркальна: справний сервіс каже «живий» — монітор не кричить завжди"""
    health = Health(
        dependencies=[
            Dependency(name="store", probe=lambda: None),
            Dependency(name="counters", probe=lambda: None),
        ]
    )
    report = health.report()

    assert report["status"] == UP, report
    assert all(d["status"] == UP for d in report["dependencies"].values()), report
    assert all(not d["reason"] for d in report["dependencies"].values()), report
    # Без цього твердження ендпоінт, зашитий у «зламано», задовольняє перевірку вище
    # повністю. Монітор, що кричить завжди, — та сама вада, що воротар, який нікого не пускає.


def check_metrics_tell_the_failure_kinds_apart() -> None:
    """FAILURE · метрики: типи відмов розрізняються, і успішні звіряються з трейсами"""
    metrics = Metrics()
    for kind in (OK, OK, UNAUTHENTICATED, RATE_LIMITED, BUDGET_EXHAUSTED):
        metrics.request(kind)
    metrics.trace_written()
    metrics.trace_written()

    rendered = metrics.render()
    for kind in (OK, UNAUTHENTICATED, RATE_LIMITED, BUDGET_EXHAUSTED):
        assert f'kind="{kind}"' in rendered, (
            f"у метриках немає роду {kind!r}. «3 % відхилено» однаково описує зламану "
            "автентифікацію, зловживання й вичерпаний бюджет — це три різні дії оператора"
        )

    assert 's06_requests_total{kind="ok"} 2' in rendered, rendered
    assert "s06_traces_total 2" in rendered, rendered
    # Звірка: успішних стільки ж, скільки трейсів. Стверджується для ОДНОГО воркера —
    # збирач процесо-локальний, і за N воркерів видача показує зріз одного з них.
    assert metrics.requests[OK] == metrics.traces, (metrics.requests, metrics.traces)


def check_the_service_survives_a_dependency_that_is_gone() -> None:
    """FAILURE · integration · недоступна залежність дає названу помилку, а не падіння"""

    class Exploding:
        name = "exploding"

        def context_for(self, *args, **kwargs):
            raise ConnectionError("сховище недоступне")

        def remember(self, fact):
            raise ConnectionError("сховище недоступне")

        def all_facts(self):
            raise ConnectionError("сховище недоступне")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("s06", path=path, stage="s06") as tracer:
            service = Service(
                settings=_settings(),
                counters=InMemory(),
                store=Exploding(),
                tracer=tracer,
                client=FakeLLM(script=_script_for(KNOWLEDGE)),
            )
            try:
                service.ask(KEY, "будь-що", now=NOW)
            except ConnectionError:
                raise AssertionError(
                    "сервіс упав разом із залежністю. Недоступне сховище має давати названу "
                    "відмову: один запит гірший за всі запити"
                ) from None
            except Exception as error:  # noqa: BLE001
                raise AssertionError(f"несподівана помилка: {type(error).__name__}") from error


# --- пастка двох воркерів: обидві половини ------------------------------------------------

DUE = NOW + 1.0


def _workers(mode: str, ledger: Ledger, count: int = 2) -> list:
    return [Worker(name=f"worker-{i}", ledger=ledger, mode=mode) for i in range(count)]


def check_two_workers_run_the_job_twice() -> None:
    """FAILURE · пастка: планувальник усередині застосунку виконує задачу ДВІЧІ"""
    ledger = Ledger()
    ran = run_interval(_workers(INSIDE, ledger), None, now=DUE, due_at=DUE)

    assert ran == 2, (
        f"задача виконалась {ran} раз(и), а не двічі. Пастка не відтворилась — тоді вправа "
        "показує читачеві правильну поведінку й називає її вадою"
    )
    assert sorted(ledger.runs) == ["worker-0", "worker-1"], ledger.runs


def check_one_scheduler_runs_the_job_once() -> None:
    """FAILURE · дзеркальна: винесений планувальник — один раз за тих самих двох воркерів"""
    ledger = Ledger()
    workers = _workers(SEPARATE, ledger)
    ran = run_interval(workers, Scheduler(ledger=ledger), now=DUE, due_at=DUE)

    assert ran == 1, f"задача виконалась {ran} раз(и), а не один: {ledger.runs}"
    assert ledger.runs == ["scheduler"], (
        f"задачу виконав воркер, а не планувальник: {ledger.runs}. Виправлення полягає саме "
        "в тому, що воркери про час не знають"
    )
    # Кількість воркерів більше ні на що не впливає — саме це й купується винесенням.
    for count in (1, 4, 8):
        many = Ledger()
        run_interval(_workers(SEPARATE, many, count), Scheduler(ledger=many), now=DUE, due_at=DUE)
        assert many.count() == 1, (count, many.runs)


def check_the_job_does_not_run_before_its_time() -> None:
    """FAILURE · пастка: до настання часу не виконує ніхто — інакше перевірки нічого не значать"""
    ledger = Ledger()
    run_interval(_workers(INSIDE, ledger), Scheduler(ledger=ledger), now=DUE - 1, due_at=DUE)

    assert ledger.count() == 0, (
        f"задача виконалась до свого часу: {ledger.runs}. Тоді «двічі» й «один раз» вище — "
        "це не про планувальник, а про те, що він спрацьовує завжди"
    )


def check_the_doubled_rate_limit_is_the_half_nobody_sees() -> None:
    """FAILURE · пастка: другий воркер подвоює ЛІМІТ — і цього не видно ніде"""
    settings = _settings()
    limit = settings.rate_limit_per_minute

    # Два воркери, у кожного свій процесо-локальний лічильник — саме те, що дає профіль local.
    first, second = InMemory(), InMemory()
    allowed = 0
    for i in range(limit * 2):
        counters = first if i % 2 == 0 else second
        if admit(KEY, counters, settings, now=NOW).allowed:
            allowed += 1

    assert allowed == limit * 2, (
        f"пропущено {allowed} із {limit * 2}. Пастка не відтворилась — а вона важливіша за "
        "подвоєну задачу: ту видно в логах, а подвоєний ліміт не видно НІДЕ. Сервіс "
        "поводиться нормально, просто межа означає вдвічі більше"
    )


def check_the_shared_store_fixes_the_half_nobody_sees() -> None:
    """FAILURE · дзеркальна: спільне сховище повертає лімітові його значення"""
    settings = _settings()
    limit = settings.rate_limit_per_minute
    first, second = _shared_pair()

    allowed = 0
    for i in range(limit * 2):
        counters = first if i % 2 == 0 else second
        if admit(KEY, counters, settings, now=NOW).allowed:
            allowed += 1

    assert allowed == limit, (
        f"пропущено {allowed} при межі {limit}. Спільне сховище не спільне — тоді переїзд "
        "у профіль prod не дав нічого, крім залежності"
    )


def check_the_scheduled_job_reports_what_actually_expired() -> None:
    """FAILURE · задача: число у звіті змінюється разом із протуханням, а не константа"""
    with tempfile.TemporaryDirectory() as tmp:
        store = FileStore(Path(tmp) / "m.jsonl")
        store.remember(_fact("olena", "promo", "Діє знижка", ttl=DAY))
        store.remember(_fact("olena", "name", "Звати Олена"))

        # Попередня редакція стверджувала лише `first == second` — тобто ідемпотентність
        # читання, яка є властивістю за побудовою й не могла стати хибною. Тепер
        # твердження про ЗВʼЯЗОК числа з часом: інакше задача могла б повертати сталу.
        before = count_expired(store, now=NOW)
        after = count_expired(store, now=NOW + DAY + 1)
        again = count_expired(store, now=NOW + DAY + 1)

    assert before == 0, f"до терміну протухлих {before}"
    assert after == 1, f"після терміну протухлих {after}, а не один"
    assert after == again, "два читання підряд дали різне — задача не ідемпотентна"


def check_the_scheduled_job_deletes_nothing() -> None:
    """FAILURE · задача читає, а не видаляє — інакше вона суперечить ADR-0003 етапу 5"""
    with tempfile.TemporaryDirectory() as tmp:
        store = FileStore(Path(tmp) / "m.jsonl")
        store.remember(_fact("olena", "promo", "Діє знижка", ttl=DAY))
        count_expired(store, now=NOW + DAY + 1)
        left = store.all_facts()

    assert len(left) == 1, (
        "задача видалила протухлий факт. Етап 5 вирішив, що протухле перевіряється при "
        "вибірці, а не видаленням при записі — видалення тут забрало б історію, заради "
        "якої те рішення й ухвалювалось (ADR-0003 етапу 5)"
    )

    # І дзеркально: планувальник не має незворотних дій. Подвоєння лишається вправою,
    # доки задача нічого не змінює.
    source = (Path(__file__).parent / "jobs.py").read_text(encoding="utf-8")
    assert not code_mentions(source, {"send", "delete", "charge", "remove"}), (
        "у планувальнику зʼявилась дія, що щось міняє — тоді подвоєння перестає "
        "бути безпечним, і вправа перетворюється на пастку для читача"
    )


# --- знайдене розгортанням ----------------------------------------------------------------

DEPLOY = Path(__file__).resolve().parent.parent.parent / "deploy"


def _compose() -> dict:
    """Розібрана продакшн-збірка. Без PyYAML — `НЕ ПЕРЕВІРЕНО`, а не пошук підрядків."""
    try:
        import yaml
    except ImportError as error:
        raise NotVerified(f"PyYAML не встановлено: {error}") from error

    raw = (DEPLOY / "docker-compose.prod.yml").read_text(encoding="utf-8")
    return yaml.safe_load(raw)


def check_a_failed_query_does_not_poison_the_connection() -> None:
    """FAILURE · сховище: невдалий запит не лишає зʼєднання в аварійному стані"""
    with _database() as connection:
        store = DatabaseStore(connection)
        try:
            store._query("SELECT з_неіснуючої_таблиці")
        except Exception:  # noqa: BLE001 — саме на це й розраховано
            pass

        # Наступний запит має працювати. Без відкату транзакція лишається аварійною, і
        # КОЖЕН наступний падає з InFailedSqlTransaction — включно з пробою стану. Сервіс
        # лишався мертвим уже після того, як причина зникла.
        facts = store.all_facts()

    assert isinstance(facts, list), facts


def check_the_prod_profile_refuses_a_fake_provider_by_default() -> None:
    """FAILURE · конфігурація: prod без справжнього провайдера не стартує"""
    base = {
        "APP_PROFILE": "prod",
        "API_KEYS": "k",
        "DATABASE_URL": "postgresql://x",
        "REDIS_URL": "redis://x",
        "OWNER_SALT": "s",
    }
    try:
        Settings.load(source=base)
    except ConfigError as error:
        assert "ALLOW_FAKE_LLM" in str(error), (
            f"відмова не каже, що робити: {error}. Сторож, який не називає виходу, "
            "спонукає прибрати сторожа"
        )
    else:
        raise AssertionError(
            "prod піднявся з підробкою без жодного дозволу — сервіс обслуговуватиме "
            "справжніх користувачів вигадками"
        )


def check_the_explicit_flag_lets_it_start_and_shows_up_in_health() -> None:
    """FAILURE · дзеркальна: явний дозвіл працює, і його ВИДНО у стані"""
    settings = Settings.load(
        source={
            "APP_PROFILE": "prod",
            "API_KEYS": "k",
            "DATABASE_URL": "postgresql://x",
            "REDIS_URL": "redis://x",
            "ALLOW_FAKE_LLM": "1",
            "OWNER_SALT": "s",
        }
    )
    assert settings.allow_fake_llm and not settings.has_real_llm, settings

    # Без цього твердження дозвіл лишався б невидимим ззовні — тихий виняток, який одного
    # дня стає інцидентом (ADR-0009).
    report = Health(dependencies=[], provider="fake").report()
    assert report["provider"] == "fake", report
    assert Health(dependencies=[], provider="real").report()["provider"] == "real"


def check_the_fake_answers_a_prompt_nobody_scripted() -> None:
    """FAILURE · підробка з auto_reply відповідає на будь-який промпт, а не падає"""
    client = FakeLLM(auto_reply=True)

    reply = client.chat.completions.create(
        model="x", messages=[{"role": "user", "content": "щось, чого ніхто не передбачав"}]
    )
    assert reply.choices[0].message.content, "порожня відповідь"

    # Форма розпізнається: промпт із переліком категорій дає категорію.
    categorised = client.chat.completions.create(
        model="x",
        messages=[{"role": "user", "content": "обери: orders, knowledge або math"}],
    )
    assert categorised.choices[0].message.content.strip() in (ORDERS, KNOWLEDGE, MATH)

    # І дзеркально: БЕЗ прапорця вичерпаний сценарій лишається помилкою.
    strict = FakeLLM(script=[])
    try:
        strict.chat.completions.create(model="x", messages=[])
    except Exception as error:  # noqa: BLE001
        assert "сценарій" in str(error).lower(), error
    else:
        raise AssertionError(
            "підробка без auto_reply відповіла на непередбачений промпт — тоді перевірки, "
            "що спираються на вичерпання сценарію, нічого не доводять"
        )


def check_the_deployment_files_exist_and_say_what_they_do() -> None:
    """FAILURE · розгортання: усі файли на місці, і смоук СПРАВДІ виконуваний"""
    for name in (
        "Dockerfile",
        "Caddyfile",
        "docker-compose.prod.yml",
        "smoke.sh",
        "RUNBOOK.md",
        ".env.prod.example",
    ):
        path = DEPLOY / name
        assert path.exists(), f"немає {name}"
        assert path.read_text(encoding="utf-8").strip(), f"{name} порожній"

    # Біт виконання — у git, а не на диску: у клона права беруться звідти. Docstring
    # обіцяв «виконуваний» і не перевіряв нічого, а файл лежав із 100644 — читач на
    # Linux виконував документовану команду й отримував Permission denied.
    import subprocess

    result = subprocess.run(
        ["git", "ls-files", "-s", "deploy/smoke.sh"],
        cwd=DEPLOY.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise NotVerified(f"git недоступний: {result.stderr.strip()}")
    assert result.stdout.startswith("100755"), (
        f"smoke.sh у git має права {result.stdout.split()[0]}, а не 100755. Читач "
        "після клону виконує документовану команду й отримує Permission denied"
    )


def check_the_smoke_script_runs_one_list_against_both_targets() -> None:
    """FAILURE · смоук: перелік перевірок не залежить від того, куди він дивиться"""
    source = (DEPLOY / "smoke.sh").read_text(encoding="utf-8")

    # Дві гілки з різними переліками означали б, що локальний прогін доводить не те, що
    # прогін на домені. Різниця дозволена рівно одна — довіра до сертифіката.
    # Твердження про **структуру**, а не про наявність слів. Попередня редакція
    # рахувала входження `$BASE` і шукала три слова — тож гілка «локально перевіряємо
    # менше» проходила всі чотири assert і робила рівно те, що заборонено.
    #
    # Єдина дозволена різниця — довіра до сертифіката. Її ім'я названо тут, і будь-яка
    # інша умова на `$INSECURE` робить перевірку червоною.
    guarded = [
        line.strip()
        for line in source.splitlines()
        if "$INSECURE" in line and line.strip().startswith(("if", "elif"))
    ]
    assert len(guarded) == 1, (
        f"гілок за $INSECURE {len(guarded)}: {guarded}. Дві означають, що локальний прогін "
        f"перевіряє не те, що доменний — і «здається, працює» повертається під іншою назвою"
    )
    assert source.count("$BASE") >= 5, "адреса не наскрізна — перелік залежить від цілі"
    assert "--insecure" in source and "INSECURE=1" in source, (
        "локальний самопідписаний сертифікат не оброблено явно"
    )
    assert "skip " in source and "не перевірено" in source, (
        "скрипт не має третього стану. Мовчазний --insecure — це зелений колір за "
        "неперевірене (spec AC-08)"
    )
    assert "exit 1" in source, "скрипт не падає на збої — тоді його вердикт нічого не значить"


def check_the_migration_runs_once_not_per_worker() -> None:
    """FAILURE · розгортання: міграції — окремий контейнер, а не крок у старті сервісу"""
    # Розбір структури, а не пошук підрядків. Попередня редакція стверджувала
    # `"migrate:" in compose` і `"service_completed_successfully" in compose` — тож
    # перенесення залежності з `api` у `caddy` давало рівно ту поломку, яку вона
    # називає, і лишалось зеленим: обидва підрядки на місці.
    compose = _compose()
    services = compose["services"]

    assert "migrate" in services, (
        "у збірці немає застосування міграцій. Розгортання без них дає сервіс, у якого "
        "перший же запит падає, а зʼєднання лишається аварійним"
    )
    # Кожен, хто торкається бази, має чекати на завершення міграцій — не «хтось».
    for name in ("api", "scheduler"):
        waits = services[name].get("depends_on", {})
        assert waits.get("migrate", {}).get("condition") == "service_completed_successfully", (
            f"{name} не чекає на завершення міграцій: {waits}. Старт стає перегонами, і перший "
            f"запит іде в неіснуючу таблицю"
        )
    # Всередині старту вони виконувались би стільки разів, скільки воркерів: та сама пастка,
    # що з планувальником, у місці, де ціна вища.
    serve = (Path(__file__).parent / "serve.py").read_text(encoding="utf-8")
    assert not code_mentions(serve, {"migrate", "migration"}), (
        "точка входу застосовує міграції — тоді два воркери змінюють схему одночасно"
    )


def check_the_service_waits_until_it_can_answer() -> None:
    """FAILURE · розгортання: проксі чекає на готовність сервісу, а не на «running»"""
    api = _compose()["services"]["api"]
    assert "healthcheck" in api, (
        "у `api` немає healthcheck. Тоді `caddy` стартує, щойно контейнер «running» — тобто до "
        "того, як uvicorn привʼязав порт, і перший смоук віддає 502 на справному сервісі"
    )
    assert "/healthz" in str(api["healthcheck"]), api["healthcheck"]


def check_the_domain_is_required_not_defaulted() -> None:
    """FAILURE · розгортання: домен обовʼязковий — дефолт мовчки ламає сертифікат"""
    raw = (DEPLOY / "docker-compose.prod.yml").read_text(encoding="utf-8")
    assert "SITE_ADDRESS: ${SITE_ADDRESS:?}" in raw, (
        "SITE_ADDRESS має дефолт. Забутий у .env.prod, він видає внутрішній сертифікат на "
        "справжньому домені: клієнти отримують помилку довіри, а смоук каже лише «curl не пройшов»"
    )
    assert "OWNER_SALT: ${OWNER_SALT:?}" in raw, (
        "OWNER_SALT має дефолт — тоді похідний власник несолений, і слабкий ключ "
        "відновлюється з трейсу словником"
    )


# --- e2e: демо ------------------------------------------------------------------------------


def check_the_demo_shows_seven_scenes_and_leaves_a_trace() -> None:
    """e2e · демо показує сім сцен, три різні гілки й обидві половини пастки"""
    buffer = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with redirect_stdout(buffer):
            code = demo_main(trace_path=path)
        recorded = list(iter_steps(path))
    output = buffer.getvalue()

    assert code == 0, code
    assert output.startswith("[FakeLLM]"), output.splitlines()[0]
    for number in range(1, 8):
        assert f"{NEWLINE}{number}. " in output, f"сцена {number} не надрукувалась"

    # Тіла сцен, а не заголовки. Урок етапу 5: заголовок доводить, що надрукувався заголовок.
    for branch in (ORDERS, KNOWLEDGE, MATH):
        assert branch in output, f"сцена 1 не показала гілки {branch}"
    for kind in (UNAUTHENTICATED, RATE_LIMITED, BUDGET_EXHAUSTED):
        assert kind in output, f"сцена 2 не показала відмови {kind}"

    assert "Хрещатик" in output and "Банков" in output, "сцена 4 не показала двох памʼятей"
    assert "ConnectionError" in output, "сцена 5 не показала несправної залежності"
    assert "secret" not in output and "10.0.0.1" not in output, (
        "у виводі рядок підключення — стан має називати ТИП помилки, не її текст"
    )

    # Обидві половини пастки — числами, а не словами.
    assert "виконалась 2 раз" in output, "сцена 6 не показала подвоєної задачі"
    assert "виконалась 1 раз" in output, "сцена 6 не показала виправлення"
    assert "пропущено 6 при межі 3" in output, (
        "сцена 6 не показала подвоєного ліміту — а це половина, важливіша за першу"
    )

    # Дзеркальна половина сцени 7: ключа немає, але похідний власник Є.
    assert "ключ у трейсі:     False" in output, "сцена 7 не довела відсутності ключа"
    assert "власник у трейсі:  '" in output, (
        "сцена 7 прибрала ключ і не показала, чим його замінено — тоді запит неможливо "
        "привʼязати ні до кого"
    )

    scenes = {step["kind"] for step in recorded}
    assert {"guard", "intent", "memory", "done", "trap"} <= scenes, scenes


def check_the_demo_needs_no_key_no_network_and_no_container() -> None:
    """FAILURE · демо: жодного справжнього провайдера, жодного контейнера"""
    import inspect

    from stages.s06_platform import run as module

    source = inspect.getsource(module)
    assert not code_mentions(source, {"psycopg", "redis", "docker", "localhost:5432"}), (
        "демо тягне контейнер. Правило курсу: усе працює офлайн — і найбільше це важить "
        "на етапі, де контейнери вперше зʼявляються"
    )
    assert "FakeLLM" in source, "демо не називає підробки явно"


# --- знахідки другого рев'ю --------------------------------------------------------------


def check_a_secret_is_neither_stored_nor_traced() -> None:
    """FAILURE · сервіс проходить чекліст етапу 5 цілком, а не одне правило з шести"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        store_path = Path(tmp) / "m.jsonl"
        with trace_run("s06", path=path, stage="s06") as tracer:
            service = Service(
                settings=_settings(),
                counters=InMemory(),
                store=FileStore(store_path),
                tracer=tracer,
                client=FakeLLM(auto_reply=True),
            )
            service.ask(KEY, "запамʼятай мій пароль — hunter2", now=NOW)
            service.ask(KEY, "запамʼятай: доставляти на Хрещатик 22", now=NOW)
            service.ask(KEY, QUESTION, now=NOW)

        written = path.read_text(encoding="utf-8")
        stored = store_path.read_text(encoding="utf-8")

    assert "hunter2" not in stored, (
        "пароль у памʼяті. Етап 5 навмисно ставить секрет ПЕРЕД проханням, бо «запамʼятай "
        "мій пароль» задовольняє обидва правила — сервіс має проходити чекліст, а не один if"
    )
    assert "hunter2" not in written, (
        "пароль у трейсі. Етап, чия теза «ключ у трейсі — це ключ у файлі», не має права "
        "писати туди секрет користувача"
    )
    # Дзеркальна половина: те, що зберігати МОЖНА, зберігається.
    assert "Хрещатик" in stored, "прохання запамʼятати адресу проігноровано"


def check_the_apostrophe_does_not_decide_what_is_remembered() -> None:
    """FAILURE · три форми апострофа розпізнаються однаково"""
    seen = []
    for word in ("запамʼятай", "запам'ятай", "запам’ятай"):
        with tempfile.TemporaryDirectory() as tmp:
            store = FileStore(Path(tmp) / "m.jsonl")
            with trace_run("s06", path=Path(tmp) / "t.jsonl", stage="s06") as tracer:
                service = Service(
                    settings=_settings(),
                    counters=InMemory(),
                    store=store,
                    tracer=tracer,
                    client=FakeLLM(auto_reply=True),
                )
                service.ask(KEY, f"{word}: доставляти на Хрещатик 22", now=NOW)
            seen.append(len(store.all_facts()))

    assert seen == [1, 1, 1], (
        f"збережено {seen} для трьох форм апострофа. U+2019 ставлять телефон і Word, і "
        "факт мовчки не зберігався: ані відмови, ані сліду"
    )


def check_the_rate_limit_is_one_atomic_call() -> None:
    """FAILURE · ліміт рахується одним викликом, а не парою читання-запис"""
    import ast
    import inspect

    from stages.s06_platform import guards

    tree = ast.parse(inspect.getsource(guards.within_rate))
    called = [
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    ]
    assert called.count("total") == 0 and called.count("add") == 1, (
        f"воротар кличе {called}. Пара `total` + `add` відкриває вікно між читанням і "
        "записом: тридцять один одночасний запит читає «двадцять девʼять», і всі проходять. "
        "Саме ці перегони закриває транзакція всередині `add`"
    )


def check_the_health_probe_reads_no_data() -> None:
    """FAILURE · проба стану не читає таблиці — ендпоінт відкритий без ключа"""
    import ast

    # Джерело читається файлом, а не імпортом: `serve.py` тягне веб-фреймворк, тож
    # імпорт робив би цю перевірку **червоною** на базовій установці замість
    # `НЕ ПЕРЕВІРЕНО`. Твердження структурне — джерела для нього досить.
    source = (Path(__file__).parent / "serve.py").read_text(encoding="utf-8")
    tree = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == "build"
    )
    # Збираються **всі** імена атрибутів, а не лише ті, що стоять у виклику: проба
    # передається як `store.ping` — тобто посилання на метод, яке ніхто тут не кличе.
    #
    # Перша редакція мала запасну умову `"ping" in str(node)`. Вона проходила локально
    # й падала на CI: у Python 3.13 представлення вузлів AST показує вміст, а раніше —
    # адресу обʼєкта. Перевірка спиралась на деталь реалізації інтерпретатора.
    seen = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "all_facts" not in seen, (
        "проба стану читає всі факти. Ендпоінт відкритий навмисно й воротарі до нього не "
        "доходять — тобто будь-хто без ключа замовляє повний скан стільки разів на секунду, "
        "скільки витримає мережа"
    )
    assert "ping" in seen, (
        f"проба стану не кличе `ping`: {sorted(seen)}. Дзеркальна половина: "
        "мало не читати таблицю — треба ще й справді торкнутися сховища"
    )


def check_traces_are_a_named_dependency() -> None:
    """FAILURE · стан знає про трейси — інакше їхня відмова валить кожен запит мовчки"""
    # Той самий привід читати файлом, а не імпортом: інакше базова установка дає
    # червоне там, де має бути «не перевірено».
    source = (Path(__file__).parent / "serve.py").read_text(encoding="utf-8")
    assert '"traces"' in source or "'traces'" in source, (
        "трейси не названі залежністю. Том повний або права зникли — і КОЖЕН запит падає "
        "пʼятисоткою, поки стан рапортує up"
    )


def check_the_owner_id_is_salted() -> None:
    """FAILURE · похідний власник солиться — слабкий ключ не відновлюється з трейсу"""
    plain = owner_of("change-me-too", salt="")
    salted = owner_of("change-me-too", salt="deployment-salt")

    assert plain != salted, "сіль ні на що не впливає"
    assert owner_of("k", salt="a") != owner_of("k", salt="b"), "різні солі дають те саме"

    # І дзеркально: у межах одного розгортання ідентифікатор стабільний, інакше лічильники
    # й трейси перестають звʼязуватись між собою.
    assert owner_of("k", salt="a") == owner_of("k", salt="a")


def check_a_zero_limit_is_refused_at_startup() -> None:
    """FAILURE · нуль і відʼємне в межах — помилка старту, а не «без ліміту»"""
    for key, value in (
        ("RATE_LIMIT_PER_MINUTE", "0"),
        ("RATE_LIMIT_PER_MINUTE", "-1"),
        ("BUDGET_USD_PER_DAY", "0"),
    ):
        try:
            Settings.load(source={key: value})
        except ConfigError as error:
            assert key in str(error), error
        else:
            raise AssertionError(
                f"{key}={value} прийнято мовчки. Нуль — найприродніший спосіб написати «без "
                "ліміту», а дає повну відмову в обслуговуванні при зеленому стані"
            )

    # Дзеркальна половина: розумні значення проходять.
    assert Settings.load(source={"RATE_LIMIT_PER_MINUTE": "30"}).rate_limit_per_minute == 30


# --- урок і матеріали читача ---------------------------------------------------------------


def check_the_failure_modes_are_at_least_a_third() -> None:
    """перевірки: режимів відмови не менше третини (NFR-4)"""
    labels = [(c.__doc__ or "").split(NEWLINE)[0] for c in CHECKS]
    failures = [d for d in labels if d.startswith("FAILURE")]
    assert len(failures) * 3 >= len(CHECKS), (
        f"режимів відмови {len(failures)} із {len(CHECKS)} — менше третини"
    )


def check_the_lesson_fits_the_reading_budget() -> None:
    """урок: ≤2500 слів (NFR-3)"""
    words = len((Path(__file__).parent / "README.md").read_text(encoding="utf-8").split())
    assert words <= 2500, f"урок розрісся до {words} слів"


def check_the_lesson_numbers_match_the_suite() -> None:
    """FAILURE · урок: числа в прозі збігаються з тим, що друкує команда"""
    total = len(CHECKS)
    failures = sum(1 for c in CHECKS if (c.__doc__ or "").startswith("FAILURE"))
    here = Path(__file__).parent
    for name, sentence in (
        ("README.md", f"перевірок: {total}, з них на режими відмови: {failures}"),
        ("CHECKLIST.md", f"перевірок: {total}, з них на режими відмови: {failures}"),
        ("README.en.md", f"{total} checks, {failures} of them on failure modes"),
    ):
        page = (here / name).read_text(encoding="utf-8")
        assert sentence in page, (
            f"{name} не містить рядка {sentence!r} — проза розійшлася з тим, що друкує "
            "команда, яку той самий урок наказує запустити"
        )


def check_the_lesson_line_counts_match_the_modules() -> None:
    """FAILURE · урок: розміри модулів у прозі — обчислені, а не переписані"""
    here = Path(__file__).parent
    lesson = (here / "README.md").read_text(encoding="utf-8")
    english = (here / "README.en.md").read_text(encoding="utf-8")

    for module, budget in (("app", 120), ("guards", 100)):
        require_intact_source(f"{module}.py")
        lines = _executable_lines(f"{module}.py")
        assert f"`{module}.py` — {lines} із {budget}" in lesson, (
            f"{module}.py має {lines} виконуваних рядків — урок називає інше число"
        )
        assert f"| {lines} / {budget} |" in english, f"README.en.md відстав: {module}"


def check_the_exercises_are_generated_from_the_pinned_mutations() -> None:
    """FAILURE · вправи: числа червоних беруться з mutations.json, а не пишуться"""
    here = Path(__file__).parent
    pinned = json.loads((here / "mutations.json").read_text(encoding="utf-8"))["mutations"]
    text_of = (here / "exercises.md").read_text(encoding="utf-8")

    for mutation in pinned:
        number = int(mutation["name"].split()[1])
        assert f"## Вправа {number} ·" in text_of, f"вправи {number} немає в прозі"
        assert f"**Червоних: {mutation['expect_failed']}.**" in text_of, (
            f"вправа {number}: у прозі не {mutation['expect_failed']} червоних — проза "
            "розійшлася з тим, що закріплено"
        )
        # І сам диф. Попередня редакція звіряла лише заголовок і число, тож вправа 1
        # друкувала читачеві `if client is not None:` як «було» і як «стало» — рядок,
        # що не змінюється. Виконати її за інструкцією було неможливо, і найважливіша
        # з шістнадцяти лишалась непрохідною.
        for side in ("old", "new"):
            for line in mutation[side].split(NEWLINE):
                assert line.strip() in text_of, (
                    f"вправа {number}: рядка {line.strip()!r} немає в прозі — читач не побачить, "
                    f"ЩО саме міняти"
                )

    assert text_of.count("## Вправа") == len(pinned), (
        f"вправ у прозі {text_of.count(chr(35) * 2 + ' Вправа')}, мутацій {len(pinned)}"
    )


def check_every_reader_file_exists() -> None:
    """матеріали: урок, карта, вправи, чеклісти й розвʼязок на місці"""
    here = Path(__file__).parent
    for name in (
        "README.md",
        "README.en.md",
        "exercises.md",
        "CHECKLIST.md",
        "DECISION.md",
        "solutions/exercise_1_two_workers.py",
        "solutions/README.md",
    ):
        path = here / name
        assert path.exists() and path.read_text(encoding="utf-8").strip(), name


def _executable_lines(name: str) -> int:
    """Виконувані рядки модуля: statement без docstring і без import."""
    import ast

    source = (Path(__file__).parent / name).read_text(encoding="utf-8")
    return len(
        {
            node.lineno
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.stmt)
            and not isinstance(node, (ast.Import, ast.ImportFrom))
            and not (
                isinstance(node, ast.Expr) and isinstance(getattr(node.value, "value", None), str)
            )
        }
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
    check_the_key_is_compared_in_constant_time,
    check_the_rate_limit_refuses_before_the_model,
    check_one_clients_limit_does_not_stop_another,
    check_an_exhausted_budget_stops_the_call_and_says_so,
    check_spending_is_counted_or_the_guard_never_fires,
    check_the_guards_run_in_the_declared_order,
    check_three_questions_take_three_branches,
    check_the_branch_reaches_the_trace_before_any_work,
    check_a_wordy_answer_still_classifies,
    check_an_unrecognised_answer_falls_back_to_the_safest_branch,
    check_the_mixed_question_limit_is_a_measured_number,
    check_there_is_no_fallback_when_the_budget_is_gone,
    check_three_requests_take_three_branches,
    check_the_trace_names_every_step_and_its_reason,
    check_a_refused_request_leaves_only_its_refusal,
    check_the_key_never_reaches_the_trace_or_the_answer,
    check_two_owners_do_not_see_each_others_memory_through_the_service,
    check_health_names_each_dependency_separately,
    check_a_healthy_service_reports_healthy,
    check_metrics_tell_the_failure_kinds_apart,
    check_the_service_survives_a_dependency_that_is_gone,
    check_two_workers_run_the_job_twice,
    check_one_scheduler_runs_the_job_once,
    check_the_job_does_not_run_before_its_time,
    check_the_doubled_rate_limit_is_the_half_nobody_sees,
    check_the_shared_store_fixes_the_half_nobody_sees,
    check_the_scheduled_job_reports_what_actually_expired,
    check_the_scheduled_job_deletes_nothing,
    check_a_failed_query_does_not_poison_the_connection,
    check_the_prod_profile_refuses_a_fake_provider_by_default,
    check_the_explicit_flag_lets_it_start_and_shows_up_in_health,
    check_the_fake_answers_a_prompt_nobody_scripted,
    check_the_deployment_files_exist_and_say_what_they_do,
    check_the_smoke_script_runs_one_list_against_both_targets,
    check_the_migration_runs_once_not_per_worker,
    check_the_service_waits_until_it_can_answer,
    check_the_domain_is_required_not_defaulted,
    check_the_demo_shows_seven_scenes_and_leaves_a_trace,
    check_the_demo_needs_no_key_no_network_and_no_container,
    check_the_failure_modes_are_at_least_a_third,
    check_the_lesson_fits_the_reading_budget,
    check_the_lesson_numbers_match_the_suite,
    check_the_lesson_line_counts_match_the_modules,
    check_the_exercises_are_generated_from_the_pinned_mutations,
    check_every_reader_file_exists,
    check_a_secret_is_neither_stored_nor_traced,
    check_the_apostrophe_does_not_decide_what_is_remembered,
    check_the_rate_limit_is_one_atomic_call,
    check_the_health_probe_reads_no_data,
    check_traces_are_a_named_dependency,
    check_the_owner_id_is_salted,
    check_a_zero_limit_is_refused_at_startup,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 6 · Platform")


if __name__ == "__main__":
    raise SystemExit(main())
