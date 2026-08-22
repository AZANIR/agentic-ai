"""Реєстр інструментів — єдине джерело правди про те, що агенту дозволено.

Інструмент — це звичайна функція плюс **опис її параметрів**, який іде до моделі. Модель не
бачить коду: вона обирає інструмент, читаючи ім'я й опис. Тому погана назва або розмитий опис
ламають вибір сильніше, ніж слабша модель — це найдешевший спосіб зіпсувати агента.

Познака ``irreversible`` живе тут, а не списком імен усередині циклу: додати четвертий
незворотний інструмент має бути можливо, не торкаючись циклу взагалі (ADR-0002).

Описи інструментів навмисне англійською — так пишуть у статтях-джерелах і в дикій природі,
і слабкі моделі на англійських описах помиляються помітно рідше. Пояснення для читача —
українською, в уроці.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data"


def _load(name: str) -> dict[str, Any]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Tool:
    """Одна дозволена дія: функція, опис її параметрів і познака незворотності."""

    name: str
    description: str
    parameters: dict[str, Any]
    func: Callable[..., str]
    irreversible: bool = field(default=False)

    def schema(self) -> dict[str, Any]:
        """Опис у тому форматі, який приймає ``tools=`` без жодних перетворень."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


# --- самі інструменти ---------------------------------------------------------


def get_weather(city: str) -> str:
    """Канонічний приклад зі статті-джерела. У проді тут був би виклик погодного API."""
    weather = _load("weather.json")
    return weather.get(city, f"Даних про погоду в місті {city} немає.")


def get_order_status(order_id: str) -> str:
    """Міст на наш домен: те саме, що погода, але вже про NovaShop."""
    order = _load("orders.json").get(order_id)
    if order is None:
        return f"Замовлення {order_id} не знайдено."
    return f"Замовлення {order_id}: {order['item']} — {order['status']}" + (
        f", очікується за {order['eta_days']} дн." if order["eta_days"] else "."
    )


def initiate_return(order_id: str, reason: str) -> str:
    """НЕЗВОРОТНИЙ. У проді це створює заявку, списує кошти й повідомляє склад.

    Саме такий інструмент має стояти за гейтом підтвердження: помилка тут коштує грошей
    і її не можна відкотити викликом «скасувати» (стаття 1, режим відмови 3).
    """
    order = _load("orders.json").get(order_id)
    if order is None:
        return f"Замовлення {order_id} не знайдено — повернення не створено."
    if not order["returnable"]:
        return f"Замовлення {order_id} поверненню не підлягає: {order['item']}."
    return f"Повернення для {order_id} створено. Причина: {reason}"


# --- реєстр -------------------------------------------------------------------
# Звичайний словник, а не декоратор. Декоратор сховав би реєстрацію саме там, де етап
# показує механіку: читач має бачити повний список дозволеного одним поглядом.

REGISTRY: dict[str, Tool] = {
    "get_weather": Tool(
        name="get_weather",
        description="Get the current weather for a city.",
        parameters={
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. 'Київ'."},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
        func=get_weather,
    ),
    "get_order_status": Tool(
        name="get_order_status",
        description="Get the delivery status of a NovaShop order by its identifier.",
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order id, e.g. 'ord_4471'."},
            },
            "required": ["order_id"],
            "additionalProperties": False,
        },
        func=get_order_status,
    ),
    "initiate_return": Tool(
        name="initiate_return",
        description=(
            "Start a return for a NovaShop order. This is irreversible: it charges a refund "
            "and notifies the warehouse."
        ),
        parameters={
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order id, e.g. 'ord_4472'."},
                "reason": {"type": "string", "description": "Why the customer returns it."},
            },
            "required": ["order_id", "reason"],
            "additionalProperties": False,
        },
        func=initiate_return,
        irreversible=True,
    ),
}


def tool_schemas() -> list[dict[str, Any]]:
    """Список описів для ``chat.completions.create(tools=...)``."""
    return [tool.schema() for tool in REGISTRY.values()]
