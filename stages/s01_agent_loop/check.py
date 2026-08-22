"""Перевірки етапу 1. Офлайн, без API-ключа, детерміновано.

Запуск: ``python -m stages.s01_agent_loop.check``

Перевірки з префіксом ``ВІДМОВА ·`` перевіряють режими відмови — те, що станеться, коли піде
не так. Саме заради них існує підробний клієнт: на справжній моделі «ліміт кроків спрацював»
перевірити неможливо, бо вона недетермінована.
"""

from __future__ import annotations

import json

from shared.check_runner import run_checks
from stages.s01_agent_loop.tools import REGISTRY, tool_schemas
from stages.s01_agent_loop.validate import validate_arguments

# --- T1 · реєстр інструментів -------------------------------------------------


def check_registry_has_three_tools() -> None:
    """tools: у реєстрі рівно три інструменти з очікуваними іменами"""
    assert set(REGISTRY) == {"get_weather", "get_order_status", "initiate_return"}, sorted(REGISTRY)
    for name, tool in REGISTRY.items():
        assert tool.name == name, f"{name}: ім'я в записі не збігається з ключем"
        assert callable(tool.func), f"{name}: не має виконуваної функції"
        assert tool.description.strip(), f"{name}: порожній опис — модель не зможе обрати"


def check_exactly_one_tool_is_irreversible() -> None:
    """tools: незворотним позначено рівно один інструмент — оформлення повернення"""
    irreversible = {name for name, tool in REGISTRY.items() if tool.irreversible}
    assert irreversible == {"initiate_return"}, irreversible


def check_schemas_are_model_ready() -> None:
    """tools: схеми придатні до передачі в tools= без жодних перетворень"""
    schemas = tool_schemas()
    assert len(schemas) == 3
    for schema in schemas:
        assert schema["type"] == "function"
        fn = schema["function"]
        assert fn["name"] in REGISTRY
        assert fn["description"].strip()
        params = fn["parameters"]
        assert params["type"] == "object"
        assert params["properties"], f"{fn['name']}: немає жодного параметра"
        assert isinstance(params["required"], list)
        for field in params["required"]:
            assert field in params["properties"], f"{fn['name']}: {field} не описаний"
    # схема має бути серіалізовною — інакше SDK впаде вже на відправці
    json.dumps(schemas)


def check_tools_return_text_from_fixtures() -> None:
    """tools: інструменти читають фікстури й не ходять у мережу"""
    # Свідомо НЕ перевіряємо входження назви міста у відповідь: українська її відмінює
    # («Київ» -> «у Києві»), і така перевірка падала б на робочому коді. Перевіряємо вміст.
    weather = REGISTRY["get_weather"].func(city="Київ")
    assert isinstance(weather, str) and "+28" in weather, weather

    status = REGISTRY["get_order_status"].func(order_id="ord_4471")
    assert isinstance(status, str) and "ord_4471" in status, status

    unknown = REGISTRY["get_order_status"].func(order_id="ord_нема")
    assert "не знайдено" in unknown.lower(), unknown

    # незворотний інструмент теж лишається чистою функцією над фікстурами
    refused = REGISTRY["initiate_return"].func(order_id="ord_4473", reason="передумав")
    assert "не підлягає" in refused, refused


# --- T2 · валідація аргументів ------------------------------------------------

WEATHER_SCHEMA = REGISTRY["get_weather"].parameters
RETURN_SCHEMA = REGISTRY["initiate_return"].parameters


def check_valid_arguments_pass() -> None:
    """validate: коректні аргументи проходять без змін"""
    ok, result = validate_arguments(WEATHER_SCHEMA, {"city": "Львів"})
    assert ok, result
    assert result == {"city": "Львів"}, result

    ok, result = validate_arguments(RETURN_SCHEMA, {"order_id": "ord_4472", "reason": "малий"})
    assert ok, result


def check_missing_required_field_is_rejected() -> None:
    """ВІДМОВА · validate: відсутнє обов'язкове поле не проходить"""
    ok, reason = validate_arguments(RETURN_SCHEMA, {"order_id": "ord_4472"})
    assert not ok
    assert "reason" in reason, reason
    assert "обов" in reason.lower(), reason


def check_unknown_field_is_rejected() -> None:
    """ВІДМОВА · validate: зайве поле не проходить мовчки"""
    ok, reason = validate_arguments(WEATHER_SCHEMA, {"city": "Львів", "units": "metric"})
    assert not ok
    assert "units" in reason, reason


def check_wrong_type_is_never_coerced() -> None:
    """ВІДМОВА · validate: тип не приводиться — рядок замість числа це відмова"""
    schema = {
        "type": "object",
        "properties": {"days": {"type": "integer"}},
        "required": ["days"],
        "additionalProperties": False,
    }
    ok, reason = validate_arguments(schema, {"days": "3"})
    assert not ok, "рядок '3' не має тихо стати числом 3"
    assert "days" in reason and "integer" in reason, reason

    # булеве значення в Python є підтипом int — але для схеми це різні типи
    ok, reason = validate_arguments(schema, {"days": True})
    assert not ok, "True не має вважатися цілим числом"


def check_rejection_reason_is_human_readable() -> None:
    """validate: пояснення відмови — речення, а не дамп структури"""
    _, reason = validate_arguments(RETURN_SCHEMA, {})
    assert len(reason) > 20, reason
    assert reason.endswith("."), f"не схоже на речення: {reason}"
    # Апостроф як індикатор дампу не годиться: «обов'язкових» — звичайне українське слово.
    # Перевіряємо те, що справді має значення — дужки структури й імена відсутніх полів.
    assert not set(reason) & set("{}[]"), f"схоже на дамп структури: {reason}"
    assert "order_id" in reason and "reason" in reason, f"не названо, чого бракує: {reason}"


CHECKS = [
    check_registry_has_three_tools,
    check_exactly_one_tool_is_irreversible,
    check_schemas_are_model_ready,
    check_tools_return_text_from_fixtures,
    check_valid_arguments_pass,
    check_missing_required_field_is_rejected,
    check_unknown_field_is_rejected,
    check_wrong_type_is_never_coerced,
    check_rejection_reason_is_human_readable,
]

if __name__ == "__main__":
    raise SystemExit(run_checks(CHECKS, title="Етап 1 — цикл агента"))
