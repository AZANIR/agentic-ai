"""Кейси оцінювання: опис того, ЩО робив агент, і породжений із нього справжній трейс.

**Чому не фікстури** (ADR-0005). Записані файли трейсів переживуть зміну формату **мовчки**,
і етап оцінюватиме формат, якого вже немає. Опис проганяється крізь той самий
`shared.trace`, що й усі етапи, тож трейс справжній — і зміна формату ламає породження
гучно, разом з усіма етапами.

**Крайність не оголошується, а виводиться.** Мітка `edge: true` задовольняє NFR-7
перемиканням прапорця, і набір із двадцяти щасливих шляхів лишається зеленим. Тут крайність
читається зі **спостережної** властивості: у трейсі є крок відмови, ліміту чи невідомого
інструмента, або відповіді немає взагалі.

**Еталонний шлях — частина кейса.** Без нього «траєкторія провалена» не має проти чого
вимірюватись, і рівень зводиться до евристики «кроків забагато».
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.trace import trace_run

# Види кроків, наявність яких робить кейс крайнім. Це **спостережна** властивість трейсу,
# а не думка автора про власний кейс.
EDGE_KINDS = frozenset(
    {"tool_error", "tool_rejected", "tool_unknown", "run_limit", "step_blocked", "refused"}
)


@dataclass(frozen=True)
class Act:
    """Один крок, який зробив агент. Стає рядком трейсу без перекладу."""

    kind: str
    fields: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Case:
    """Задача, еталон і те, що агент зробив насправді."""

    name: str
    task: str
    expected_tools: tuple[str, ...]
    budget: int
    answer: str
    expected_answer: str
    acts: tuple[Act, ...]
    status: str = "ok"

    @property
    def edge(self) -> bool:
        """Крайній випадок — за трейсом, не за міткою."""
        kinds = {act.kind for act in self.acts}
        return bool(kinds & EDGE_KINDS) or not self.answer.strip() or self.status != "ok"

    def tools(self) -> tuple[str, ...]:
        return tuple(a.fields["tool"] for a in self.acts if "tool" in a.fields)


def _order(tool: str, order_id: str = "ord_4471") -> Act:
    return Act("tool_call", {"tool": tool, "args": {"order_id": order_id}, "result": "в дорозі"})


def _say(text: str) -> Act:
    return Act("llm_call", {"tool_calls": [], "tokens": 80, "answer": text})


def _want(tool: str) -> Act:
    return Act("llm_call", {"tool_calls": [tool], "tokens": 60})


DELIVERY = "Замовлення в дорозі, доставка завтра."
RETURN_RULE = "Повернення можливе протягом чотирнадцяти днів."

CASES: list[Case] = [
    Case(
        "прямий шлях",
        "де моє замовлення",
        ("get_order_status",),
        4,
        DELIVERY,
        "замовлення в дорозі завтра",
        (_want("get_order_status"), _order("get_order_status"), _say(DELIVERY)),
    ),
    Case(
        "та сама відповідь через відновлення",
        "де моє замовлення",
        ("get_order_status",),
        4,
        DELIVERY,
        "замовлення в дорозі завтра",
        (
            _want("search_policy"),
            Act("tool_rejected", {"tool": "search_policy", "reason": "не той інструмент"}),
            _want("get_order_status"),
            _order("get_order_status"),
            _say(DELIVERY),
        ),
    ),
    Case(
        "правильна відповідь після циклу",
        "де моє замовлення",
        ("get_order_status",),
        4,
        DELIVERY,
        "замовлення в дорозі завтра",
        (
            _want("get_order_status"),
            _order("get_order_status"),
            _want("get_order_status"),
            _order("get_order_status"),
            _want("get_order_status"),
            _order("get_order_status"),
            _say(DELIVERY),
        ),
    ),
    Case(
        "правильний інструмент, хибна відповідь",
        "де моє замовлення",
        ("get_order_status",),
        4,
        "Замовлення скасовано.",
        "замовлення в дорозі завтра",
        (_want("get_order_status"), _order("get_order_status"), _say("Замовлення скасовано.")),
    ),
    Case(
        "щаслива випадковість: не той інструмент, та сама відповідь",
        "де моє замовлення",
        ("get_order_status",),
        4,
        DELIVERY,
        "замовлення в дорозі завтра",
        (_want("search_policy"), _order("search_policy"), _say(DELIVERY)),
    ),
    Case(
        "викликано неіснуючий інструмент",
        "де моє замовлення",
        ("get_order_status",),
        4,
        "Не вдалося перевірити.",
        "замовлення в дорозі завтра",
        (
            _want("track_parcel"),
            Act("tool_unknown", {"tool": "track_parcel", "known": ["get_order_status"]}),
            _say("Не вдалося перевірити."),
        ),
    ),
    Case(
        "інструмент відмовив, агент здався",
        "де моє замовлення",
        ("get_order_status",),
        4,
        "Сервіс недоступний.",
        "замовлення в дорозі завтра",
        (
            _want("get_order_status"),
            Act("tool_error", {"tool": "get_order_status", "error": "TimeoutError"}),
            _say("Сервіс недоступний."),
        ),
    ),
    Case(
        "інструмент відмовив, агент повторив і дійшов",
        "де моє замовлення",
        ("get_order_status", "get_order_status"),
        5,
        DELIVERY,
        "замовлення в дорозі завтра",
        (
            _want("get_order_status"),
            Act("tool_error", {"tool": "get_order_status", "error": "TimeoutError"}),
            _want("get_order_status"),
            _order("get_order_status"),
            _say(DELIVERY),
        ),
    ),
    Case(
        "уперся в ліміт кроків",
        "де моє замовлення",
        ("get_order_status",),
        4,
        "",
        "замовлення в дорозі завтра",
        (
            _want("get_order_status"),
            _order("get_order_status"),
            _want("get_order_status"),
            Act("run_limit", {"limit": 3, "made": 3}),
        ),
        status="limit",
    ),
    Case(
        "крок зупинено воротарем",
        "оформити повернення",
        ("start_return",),
        4,
        "Потрібне підтвердження.",
        "повернення чотирнадцять днів",
        (
            _want("start_return"),
            Act("step_blocked", {"tool": "start_return", "reason": "потрібне підтвердження"}),
            _say("Потрібне підтвердження."),
        ),
    ),
    Case(
        "порожня відповідь",
        "де моє замовлення",
        ("get_order_status",),
        4,
        "",
        "замовлення в дорозі завтра",
        (_want("get_order_status"), _order("get_order_status"), _say("")),
    ),
    Case(
        "відповідь переказує питання",
        "де моє замовлення",
        ("get_order_status",),
        4,
        "Ви питаєте, де ваше замовлення.",
        "замовлення в дорозі завтра",
        (
            _want("get_order_status"),
            _order("get_order_status"),
            _say("Ви питаєте, де ваше замовлення."),
        ),
    ),
    Case(
        "пошук нижче порога, агент відмовився вигадувати",
        "яка гарантія на цей товар",
        ("search_policy",),
        5,
        "Не знайшов у політиці — уточніть у підтримки.",
        # Еталон описує ПРАВИЛЬНУ ПОВЕДІНКУ, а не бажаний зміст. Якщо база не має
        # відповіді, успіх — це відмова, а не текст про гарантію. Еталон, що вимагає
        # змісту, якого немає, карає за єдину правильну поведінку.
        "не знайшов уточніть підтримки",
        (
            _want("search_policy"),
            Act("tool_call", {"tool": "search_policy", "result": "нічого певного"}),
            Act("search", {"best": 0.21, "threshold": 0.35}),
            Act("refused", {"reason": "нижче порога"}),
            _say("Не знайшов у політиці — уточніть у підтримки."),
        ),
    ),
    Case(
        "пошук нижче порога, агент вигадав",
        "яка гарантія на цей товар",
        ("search_policy",),
        4,
        "Гарантія становить п'ять років.",
        # Той самий еталон, що й у сусіднього кейса: обидва питали те саме й база
        # не знала. Цей вигадав — і саме тому провалює e2e, а сусід ні.
        "не знайшов уточніть підтримки",
        (
            _want("search_policy"),
            Act("tool_call", {"tool": "search_policy", "result": "нічого певного"}),
            Act("search", {"best": 0.21, "threshold": 0.35}),
            _say("Гарантія становить п'ять років."),
        ),
    ),
    Case(
        "памʼять узята доречно",
        "коли моє звичне замовлення",
        ("get_order_status",),
        4,
        DELIVERY,
        "замовлення в дорозі завтра",
        (
            Act("memory", {"taken": ["улюблений розмір"], "skipped": []}),
            _want("get_order_status"),
            _order("get_order_status"),
            _say(DELIVERY),
        ),
    ),
    Case(
        "памʼять відкинула секрет",
        "запамʼятай мій пароль",
        (),
        3,
        "Паролі я не запамʼятовую.",
        # Третій кейс поспіль, де еталон мусив описувати ПОВЕДІНКУ, а не зміст:
        # правильна відповідь тут — відмова запамʼятати, і саме її має вимагати еталон.
        "паролі не запамʼятовую",
        (
            Act("memory", {"taken": [], "skipped": ["схоже на секрет"]}),
            _say("Паролі я не запамʼятовую."),
        ),
    ),
    Case(
        "маршрут до потрібного фахівця",
        "оформити повернення",
        ("start_return",),
        4,
        RETURN_RULE,
        "повернення чотирнадцять днів",
        (
            Act("route", {"chosen": "returns", "known": ["orders", "returns"]}),
            _want("start_return"),
            _order("start_return"),
            _say(RETURN_RULE),
        ),
    ),
    Case(
        "маршрут не туди, відновився",
        "оформити повернення",
        ("start_return",),
        4,
        RETURN_RULE,
        "повернення чотирнадцять днів",
        (
            Act("route", {"chosen": "orders", "known": ["orders", "returns"]}),
            Act("specialist_failed", {"node": "orders", "error": "не мій випадок"}),
            Act("route", {"chosen": "returns", "known": ["orders", "returns"]}),
            _want("start_return"),
            _order("start_return"),
            _say(RETURN_RULE),
        ),
    ),
    Case(
        "два інструменти в правильному порядку",
        "поверніть замовлення 4471",
        ("get_order_status", "start_return"),
        6,
        RETURN_RULE,
        "повернення чотирнадцять днів",
        (
            _want("get_order_status"),
            _order("get_order_status"),
            _want("start_return"),
            _order("start_return"),
            _say(RETURN_RULE),
        ),
    ),
    Case(
        "два інструменти в хибному порядку",
        "поверніть замовлення 4471",
        ("get_order_status", "start_return"),
        6,
        RETURN_RULE,
        "повернення чотирнадцять днів",
        (
            _want("start_return"),
            _order("start_return"),
            _want("get_order_status"),
            _order("get_order_status"),
            _say(RETURN_RULE),
        ),
    ),
    Case(
        "прогін без жодного кроку",
        "де моє замовлення",
        ("get_order_status",),
        4,
        "",
        "замовлення в дорозі завтра",
        (),
        status="empty",
    ),
]


def write(path: Path | str, cases: list[Case] | None = None) -> dict[str, Case]:
    """Породити трейс кейсів і повернути відображення `trace_id -> кейс`.

    Один `trace_run` на кейс: так пише етап 1, і так траєкторія дорівнює прогону.
    """
    made: dict[str, Case] = {}
    for case in cases if cases is not None else CASES:
        with trace_run(case.name, path=path, stage="s08") as tracer:
            for act in case.acts:
                tracer.step(act.kind, **act.fields)
            made[tracer.trace_id] = case
    return made
