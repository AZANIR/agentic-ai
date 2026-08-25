"""Та сама задача **без жодного фреймворка** (ADR-0004).

Прочитавши цей файл, важко не помітити головного: **тут нічого немає**. Два виклики моделі,
один виклик інструмента, явна передача стану змінною. Це і є базова лінія, і її розмір —
перше число таблиці.

Граф етапу 3 сюди не переноситься навмисно. Там supervisor-роутер із маршрутизацією й циклом
ревізій; тут два послідовні кроки. Підігнати одне під інше означало б порівнювати задачу з
іншою задачею — рівно та помилка, від якої застерігає контракт.

**Координація тут явна до нудьги:** наступний крок написаний наступним рядком. Питання «чому
виконався цей крок» має відповідь довжиною в один погляд — і саме з цією ціною порівнюються
три наступні файли.
"""

from __future__ import annotations

import json
from typing import Any

from shared.trace import trace_run
from stages.s09_frameworks import contract

NAME = "без фреймворка"
COORDINATION = "явна"
WHY_SOURCE = "мій код: наступний крок — наступний рядок"


def unavailable_because() -> str:
    """Базову лінію виконати можна завжди: у неї немає залежностей, і в цьому вся суть."""
    return ""


def ask(client: Any, messages: list[dict[str, Any]], *, tools: bool = False) -> Any:
    """Один виклик моделі. Клієнт подається ззовні — власного тут немає (ADR-0007)."""
    payload: dict[str, Any] = {"model": "fake", "messages": messages}
    if tools:
        payload["tools"] = [contract.TOOL_SCHEMA]
    return client.chat.completions.create(**payload).choices[0].message


def run(client: Any, *, tracer: Any = None) -> contract.Result:
    """Research → writer. Обидва кроки видно, і обидва мої."""
    steps: list[str] = []
    used: list[str] = []
    stopped = contract.OUT_OF_BUDGET
    answer = ""

    # Крок 1 — research. Модель просить інструмент; ми його викликаємо.
    asked = ask(client, [{"role": "user", "content": contract.RESEARCH_PROMPT}], tools=True)
    steps.append("research")
    _step(tracer, "research", tools=len(asked.tool_calls or []))

    note = ""
    for call in asked.tool_calls or []:
        used.append(call.function.name)
        arguments = json.loads(call.function.arguments)
        note = contract.search_notes(arguments.get("query", ""))
        _step(tracer, "tool", tool=call.function.name)

    # Крок 2 — writer. Нотатка їде в промпт, який теж належить контракту.
    if note:
        written = ask(
            client,
            [{"role": "user", "content": contract.WRITER_PROMPT.format(note=note)}],
        )
        steps.append("writer")
        answer = written.content or ""
        stopped = contract.ANSWERED if answer.strip() else contract.OUT_OF_BUDGET
        _step(tracer, "writer", chars=len(answer))

    return contract.Result(
        name=NAME,
        asked=contract.QUESTION,
        answer=answer,
        tools_used=tuple(used),
        stopped_by=stopped,
        model_calls=0,  # заповнює лічильник: реалізація себе не рахує
        coordination=COORDINATION,
        why_source=WHY_SOURCE,
        steps=tuple(steps),
    )


def _step(tracer: Any, kind: str, **fields: Any) -> None:
    """Крок у трейс, якщо трасувальник подано. Ключ прогону ставить той, хто відкрив трейс."""
    if tracer is not None:
        tracer.step(kind, **fields)


def traced(client: Any, path: Any) -> contract.Result:
    """Прогін із власним трейсом. Ключ прогону — `case`, з першого рядка (ADR-0008)."""
    with trace_run(NAME, path=path, stage="s09", case=NAME) as tracer:
        return run(client, tracer=tracer)
