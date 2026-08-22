"""Цикл ReAct — те місце, де рішення моделі перетворюється на виклик функції.

Уся «магія» агента вміщається в один while. Модель отримує історію розмови й список
інструментів; вона відповідає або текстом (тоді ми закінчили), або проханням викликати
інструмент (тоді ми його виконуємо й повертаємо результат у історію). Повторюємо.

Модель **нічого не виконує сама**. Вона повертає ім'я функції та рядок JSON з аргументами —
далі все робить цей код. Саме тому між її рішенням і викликом функції можна поставити
захист, і саме тому їх тут три:

1. **Ліміт кроків** — від нескінченного циклу.
2. **Валідація аргументів** — від вигаданих полів і типів.
3. **Гейт підтвердження** — від незворотної дії, зробленої «на всяк випадок».

Кожен захист стоїть на своєму місці в циклі; жоден не можна «випадково» обійти.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from shared.config import settings
from shared.trace import Tracer
from stages.s01_agent_loop.tools import REGISTRY, Tool, tool_schemas
from stages.s01_agent_loop.validate import validate_arguments

SYSTEM_PROMPT = (
    "You are a support assistant for NovaShop, an online store. "
    "Use the provided tools to answer. Never invent order data. "
    "When you have the answer, reply in Ukrainian."
)


@dataclass
class RunResult:
    """Чим завершився прогін. Порожня ``answer`` означає, що відповіді немає."""

    answer: str | None = None
    steps: int = 0
    stopped_by_limit: bool = False
    blocked_tool: str | None = None
    transcript: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.answer is not None


def run_agent(
    task: str,
    *,
    client: Any,
    tracer: Tracer,
    tools: dict[str, Tool] | None = None,
    model: str | None = None,
    max_steps: int | None = None,
    confirmed: bool = False,
) -> RunResult:
    """Виконати задачу циклом Plan -> Act -> Observe -> Decide.

    :param confirmed: чи дав Learner дозвіл на незворотні дії. Підтвердження приходить
        окремим повторним запуском, а не інтерактивним запитом (ADR-0002).
    """
    tools = REGISTRY if tools is None else tools
    limit = max_steps if max_steps is not None else settings.agent_max_steps
    schemas = [t.schema() for t in tools.values()] if tools is not REGISTRY else tool_schemas()

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    result = RunResult(transcript=messages)

    while result.steps < limit:
        result.steps += 1

        # --- Plan: питаємо модель, що робити далі ---------------------------
        response = client.chat.completions.create(
            model=model or settings.llm_model or "fake",
            messages=messages,
            tools=schemas,
            tool_choice="auto",
        )
        message = response.choices[0].message
        tracer.step(
            "llm_call",
            step=result.steps,
            tool_calls=[c.function.name for c in (message.tool_calls or [])],
            tokens=getattr(response.usage, "total_tokens", None),
        )

        # --- Decide: модель відповіла текстом => закінчили ------------------
        if not message.tool_calls:
            result.answer = message.content
            messages.append({"role": "assistant", "content": message.content})
            return result

        messages.append(_assistant_message(message))

        # --- Act: виконуємо те, що вона попросила ---------------------------
        for call in message.tool_calls:
            outcome = _execute(call, tools, tracer, confirmed=confirmed)
            messages.append({"role": "tool", "tool_call_id": call.id, "content": outcome.content})
            if outcome.blocked_tool:
                result.blocked_tool = outcome.blocked_tool
                result.answer = outcome.content
                return result

    # Ліміт вичерпано. Відповіді немає — і вигадувати її не можна: краще чесне «не впорався»,
    # ніж правдоподібний текст, за яким нічого не стоїть.
    result.stopped_by_limit = True
    tracer.step("run_limit", limit=limit)
    return result


@dataclass
class _Outcome:
    content: str
    blocked_tool: str | None = None


def _execute(call: Any, tools: dict[str, Tool], tracer: Tracer, *, confirmed: bool) -> _Outcome:
    """Один запит інструмента: розібрати, перевірити, за потреби зупинити, виконати."""
    name = call.function.name
    tool = tools.get(name)
    if tool is None:
        tracer.step("tool_unknown", tool=name)
        return _Outcome(f"Інструмента {name} не існує. Доступні: {', '.join(tools)}.")

    # ``arguments`` приходить РЯДКОМ JSON, не словником — так влаштований протокол.
    try:
        arguments = json.loads(call.function.arguments)
    except json.JSONDecodeError as exc:
        tracer.step("tool_rejected", tool=name, reason="broken json")
        return _Outcome(f"Аргументи не є коректним JSON: {exc}.")

    # Захист 2: аргументи не доходять до функції, поки не пройшли схему.
    ok, checked = validate_arguments(tool.parameters, arguments)
    if not ok:
        tracer.step("tool_rejected", tool=name, reason=checked)
        return _Outcome(checked)

    # Захист 3: незворотна дія не виконується без явного підтвердження.
    if tool.irreversible and not confirmed:
        tracer.step("tool_blocked", tool=name, args=checked)
        return _Outcome(
            f"Дію «{name}» не виконано: вона незворотна й потребує підтвердження. "
            f"Було б виконано з аргументами {_readable(checked)}. "
            f"Щоб підтвердити, запусти прогін ще раз із підтвердженням.",
            blocked_tool=name,
        )

    output = tool.func(**checked)
    tracer.step("tool_call", tool=name, args=checked, result=output)
    return _Outcome(output)


def _assistant_message(message: Any) -> dict[str, Any]:
    """Відповідь моделі у вигляді, придатному для повернення в історію."""
    return {
        "role": "assistant",
        "content": message.content,
        "tool_calls": [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.function.name, "arguments": c.function.arguments},
            }
            for c in message.tool_calls
        ],
    }


def _readable(arguments: dict[str, Any]) -> str:
    return ", ".join(f"{key}={value}" for key, value in arguments.items())
