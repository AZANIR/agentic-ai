"""Перевірки етапу 6.

    python -m stages.s06_platform.check

Працюють **офлайн і без контейнерів**. Те, що справді потребує Docker, позначається
`НЕ ПЕРЕВІРЕНО` — третій стан, і він не дорівнює зеленому.
"""

from __future__ import annotations

from shared.check_runner import run_checks
from shared.config import LOCAL, Settings
from shared.counters import DAY, MINUTE, InMemory, Shared, get_counters
from stages.s06_platform.fake_store import FakeStore

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії.
BUDGET_SECONDS = 60

NEWLINE = chr(10)
NOW = 1_700_000_000.0


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


CHECKS = [
    check_both_counters_answer_the_same_way_within_one_instance,
    check_the_window_forgets_what_fell_out_of_it,
    check_two_instances_on_one_store_see_one_number,
    check_two_in_memory_counters_do_not_see_each_other,
    check_time_is_passed_in_never_read_from_the_clock,
    check_the_factory_branches_on_profile_and_nothing_else,
    check_the_shared_counter_needs_no_container_to_be_checked,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 6 · Platform")


if __name__ == "__main__":
    raise SystemExit(main())
