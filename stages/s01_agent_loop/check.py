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


CHECKS = [
    check_registry_has_three_tools,
    check_exactly_one_tool_is_irreversible,
    check_schemas_are_model_ready,
    check_tools_return_text_from_fixtures,
]

if __name__ == "__main__":
    raise SystemExit(run_checks(CHECKS, title="Етап 1 — цикл агента"))
