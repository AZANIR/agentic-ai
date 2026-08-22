"""Перевірка аргументів, які попросила модель, проти оголошеної схеми інструмента.

Це **межа довіри**. Усе, що приходить від моделі, вважається неперевіреним: модель не виконує
код і не знає, що станеться, — вона лише пропонує. Між пропозицією і виконанням має стояти
щось, що вміє сказати «ні».

Чому власний код, а не ``jsonschema``: бібліотека замінила б цих сорок рядків одним викликом,
після якого читач знав би, що «валідація якось відбувається», і не знав би, що саме там
перевіряється — на етапі, вся суть якого показати механіку (ADR-0003).

**Межа цієї реалізації:** підтримуються лише пласкі об'єкти з простими типами. Вкладені
об'єкти й масиви не перевіряються — для трьох інструментів етапу їх немає, а на етапі 6,
де валідація стає межею довіри публічного ендпоінта, тут має стояти справжня бібліотека.
"""

from __future__ import annotations

from typing import Any

# Відповідність типів JSON-схеми типам Python.
# bool стоїть окремо навмисне: у Python ``bool`` є підтипом ``int``, тож ``isinstance(True, int)``
# істинне. Для схеми це різні типи, і мовчазне ототожнення пропустило б ``True`` там, де
# очікується число.
_TYPES: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _type_matches(value: Any, expected: str) -> bool:
    python_type = _TYPES.get(expected)
    if python_type is None:
        return True  # невідомий тип у схемі не є приводом блокувати виклик
    if expected in ("integer", "number") and isinstance(value, bool):
        return False
    return isinstance(value, python_type)


def validate_arguments(
    schema: dict[str, Any],
    arguments: dict[str, Any],
) -> tuple[bool, Any]:
    """Перевірити аргументи проти схеми.

    Повертає ``(True, аргументи)``, коли все гаразд, або ``(False, пояснення)``, коли ні.

    Пояснення адресоване **двом читачам одразу**: людині, що дивиться у вивід, і моделі, якій
    воно повернеться як результат кроку. Тому це речення, а не дамп структури: модель має
    зрозуміти, що виправити, з тексту.

    Приведення типів не виконується свідомо. Рядок ``"3"`` там, де оголошено число, — це
    відмова, а не привід здогадуватись: мовчазне приведення сховало б помилку моделі саме
    там, де читач має її побачити.
    """
    properties: dict[str, Any] = schema.get("properties", {})
    required: list[str] = schema.get("required", [])

    # Збираємо ВСІ проблеми, а не першу-ліпшу. Якщо модель надіслала {"town": ...},
    # то бракує `city` І поле `town` невідоме — обидва факти потрібні їй одразу.
    # Повідомити лише про перший означає змусити її на ще один виклик, тобто ще
    # токени й ще затримку рівно за те, що ми вже знали.
    problems: list[str] = []

    missing = [name for name in required if name not in arguments]
    if missing:
        problems.append(f"не вистачає обов'язкових полів: {', '.join(missing)}")

    if schema.get("additionalProperties") is False:
        unknown = [name for name in arguments if name not in properties]
        if unknown:
            problems.append(f"невідомі поля: {', '.join(unknown)}")

    for name, value in arguments.items():
        expected = properties.get(name, {}).get("type")
        if expected and not _type_matches(value, expected):
            got = type(value).__name__
            problems.append(f"поле {name} має бути типу {expected}, а отримано {got}")

    if problems:
        return False, (
            f"Аргументи не підходять — {'; '.join(problems)}. "
            f"Типи не приводяться автоматично. Інструмент приймає: {', '.join(properties)}."
        )

    return True, arguments
