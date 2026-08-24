"""Перевірки етапу 5.

    python -m stages.s05_memory.check

Офлайн, без ключа. **Час у перевірках подається явно** — ніде не береться з системного
годинника. Інакше перевірка TTL проходила б уночі й падала вдень, і це була б не мигтливість
тесту, а мигтливість самої пам'яті.
"""

from __future__ import annotations

from shared.check_runner import run_checks
from stages.s05_memory.facts import ACTIVE, REPLACED, Fact, is_active

DAY = 86_400.0
NOW = 1_700_000_000.0  # фіксована точка: усі «зараз» у перевірках рахуються від неї


def _fact(**overrides) -> Fact:
    base = {
        "owner": "olena",
        "topic": "address",
        "text": "Доставляти на Хрещатик 22",
        "stored_at": NOW,
        "ttl": None,
        "status": ACTIVE,
    }
    return Fact(**{**base, **overrides})


def check_a_fact_carries_everything_needed_to_judge_it() -> None:
    """facts: запис несе все, чим вирішується, чи брати його у контекст"""
    fact = _fact()
    assert fact.owner and fact.topic and fact.text
    assert fact.stored_at == NOW and fact.status == ACTIVE
    assert fact.ttl is None, "вічний факт не має терміну"
    assert is_active(fact, now=NOW + 365 * DAY), "вічний факт протух"


def check_time_is_passed_in_never_read_from_the_clock() -> None:
    """ВІДМОВА · facts: рішення про активність не залежить від системного годинника

    Перша редакція грепала текст модуля — і червоніла на власному docstring, де про
    `datetime.now()` саме застерігають. Перевірка про код має дивитись на код: розбір AST
    бачить виклики й не бачить прози.
    """
    import ast
    import inspect

    from stages.s05_memory import facts

    tree = ast.parse(inspect.getsource(facts))
    forbidden = {"now", "utcnow", "today", "time", "monotonic", "perf_counter"}
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not (called & forbidden), (
        f"годинник усередині логіки: {sorted(called & forbidden)} — перевірка TTL "
        "проходитиме вночі й падатиме вдень, і це мигтливість памʼяті, а не тесту"
    )

    signature = inspect.signature(facts.is_active)
    assert "now" in signature.parameters, "час має бути параметром"
    assert signature.parameters["now"].kind is inspect.Parameter.KEYWORD_ONLY, (
        "час має передаватись іменованим аргументом — позиційний легко переплутати"
    )


def check_an_expired_fact_stops_being_active() -> None:
    """ВІДМОВА · facts: факт із терміном перестає бути активним рівно після терміну"""
    perishable = _fact(topic="delivery", text="Замовлення в дорозі", ttl=7 * DAY)

    assert is_active(perishable, now=NOW + 6 * DAY), "протух раніше за термін"
    assert not is_active(perishable, now=NOW + 8 * DAY), "не протух після терміну"
    assert is_active(perishable, now=NOW + 7 * DAY - 1), "межа зсунута"
    assert not is_active(perishable, now=NOW + 7 * DAY + 1), "межа зсунута"


def check_a_replaced_fact_never_returns_to_the_context() -> None:
    """ВІДМОВА · facts: замінений факт не активний, скільки б часу не минуло"""
    old = _fact(status=REPLACED, replaced_at=NOW + DAY)

    assert not is_active(old, now=NOW + DAY), "замінений факт лишився активним"
    assert not is_active(old, now=NOW), "замінений факт активний у минулому"
    assert old.text, "текст має лишитись — історія заміни сама по собі цінна"
    assert old.replaced_at == NOW + DAY, "час заміни втрачено"


def check_a_fact_survives_a_round_trip_through_a_line() -> None:
    """facts: запис і читання рядка не змінюють жодного поля"""
    original = _fact(ttl=7 * DAY, topic="delivery")
    restored = Fact.from_line(original.to_line())

    assert restored == original, f"{restored} != {original}"
    assert "\n" not in original.to_line(), "рядок із переносом зламає файл на один-на-рядок"


def check_a_corrupted_line_is_named_not_guessed() -> None:
    """ВІДМОВА · facts: зіпсований рядок відхиляється, а не стає фактом із порожніми полями"""
    broken = [
        "",
        "{обірваний",
        '{"owner": "olena"}',
        '["не той тип"]',
        '{"owner": "olena", "topic": "address", "text": "", "stored_at": 1}',
    ]
    for line in broken:
        try:
            Fact.from_line(line)
        except ValueError:
            continue
        raise AssertionError(
            f"рядок {line[:40]!r} став фактом — порожні поля виглядають як справжня памʼять"
        )


CHECKS = [
    check_a_fact_carries_everything_needed_to_judge_it,
    check_time_is_passed_in_never_read_from_the_clock,
    check_an_expired_fact_stops_being_active,
    check_a_replaced_fact_never_returns_to_the_context,
    check_a_fact_survives_a_round_trip_through_a_line,
    check_a_corrupted_line_is_named_not_guessed,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 5 · Memory")


if __name__ == "__main__":
    raise SystemExit(main())
