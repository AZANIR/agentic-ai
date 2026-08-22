"""Вправа 2 — чому bool просочується крізь перевірку цілого типу.

    python -m stages.s01_agent_loop.solutions.exercise_2_bool_leak

Показує обидві поведінки поруч: із виключенням ``bool`` і без нього. Другий випадок —
це те, що станеться, якщо прибрати два рядки з ``validate.py``.
"""

from __future__ import annotations

from typing import Any

from stages.s01_agent_loop.validate import validate_arguments

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"days": {"type": "integer", "description": "Delivery window in days."}},
    "required": ["days"],
    "additionalProperties": False,
}


def naive_type_check(value: Any, expected: str) -> bool:
    """Валідація «як здається очевидним» — без окремої гілки для bool."""
    types = {"string": str, "integer": int, "number": (int, float), "boolean": bool}
    python_type = types.get(expected)
    return python_type is None or isinstance(value, python_type)


def main() -> int:
    print("Схема очікує: days: integer\n")

    for value in (3, "3", True, 3.5):
        ok, detail = validate_arguments(SCHEMA, {"days": value})
        naive = naive_type_check(value, "integer")
        mark = "проходить" if ok else "відмова  "
        naive_mark = "проходить" if naive == True else "відмова  "  # noqa: E712
        print(f"  days={value!r:<6} {type(value).__name__:<5}  наш: {mark}   наївний: {naive_mark}")

    print(
        "\nРізниця лише на True. У Python bool є ПІДТИПОМ int:\n"
        f"  isinstance(True, int) -> {isinstance(True, int)}\n"
        f"  True == 1             -> {True == 1}\n"  # noqa: E712
        "\nТож наївна перевірка пропускає True там, де оголошено число, і функція\n"
        "отримує булеве значення. Далі воно поводиться як 1 — доки хтось не надрукує\n"
        "його користувачеві: «Вікно доставки: True дн.»\n"
        "\nТа сама пастка є в кожній мові, де булеве значення — це число.\n"
        "Друга така пастка в Python: рядок є послідовністю, тож перевірка «це послідовність?»\n"
        'пропускає "abc" там, де очікується список рядків.'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
