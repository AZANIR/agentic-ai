"""Та сама задача на Google ADK — **за прапорцем** (ADR-0006).

    pip install -e ".[adk]"
    S09_ADK=1 python -m stages.s09_frameworks.run

**Цей файл теж написано, але не прогнано**: ADK потребує чужих креденшелів, яких у автора
немає. Причина інша, ніж у CrewAI, і різниця має значення для читача:

    CrewAI   не встановлюється на цьому Python  -> лікується іншим інтерпретатором
    ADK      потребує креденшелів Google        -> лікується обліковим записом

**Прапорець мовчати не має.** Найтонше рішення етапу саме тут. Стан «не перевірено»
правильний для того, хто ADK не просив: базова установка лишається прохідною. Але для того,
хто **явно ввімкнув** прапорець, той самий стан був би брехнею — він попросив четвертий
рядок, отримав три й нічого про це не дізнався.

Тому дві різні події й дві різні реакції:

    прапорець вимкнено                 не перевірено, окремий рядок таблиці
    прапорець увімкнено, ключа немає   ГУЧНА відмова з назвою того, чого бракує

Вміст оточення при цьому не потрапляє ані в таблицю, ані у вивід: називається **ім'я**
змінної, а не її значення (spec §6.1).
"""

from __future__ import annotations

import os
from typing import Any

from shared.trace import trace_run
from stages.s09_frameworks import contract

NAME = "Google ADK"
PACKAGE = "google.adk"
COORDINATION = "явна (агент і його інструменти)"
WHY_SOURCE = "конфігурація агента плюс логи виконавця"

FLAG = "S09_ADK"
# Змінні, наявність будь-якої з яких означає «креденшели налаштовано». Перевіряється
# НАЯВНІСТЬ імені, значення не читається й нікуди не потрапляє.
CREDENTIALS = ("GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT")


class Demanded(RuntimeError):
    """Прапорець увімкнено, а виконати неможливо. Це помилка, а не третій стан."""


def wanted() -> bool:
    """Чи просив читач ADK. Порожній рядок і `0` — це «ні»."""
    return os.environ.get(FLAG, "").strip() not in ("", "0", "false", "no")


def unavailable_because() -> str:
    """Чому реалізацію не можна виконати. Порожньо — можна."""
    try:
        import google.adk  # noqa: F401, PLC0415
    except ImportError:
        return 'пакета немає — постав `pip install -e ".[adk]"`'
    if not any(name in os.environ for name in CREDENTIALS):
        return f"креденшелів немає — потрібна одна зі змінних: {', '.join(CREDENTIALS)}"
    return ""


def available() -> bool:
    return not unavailable_because()


def demand() -> None:
    """Гучно впасти, якщо прапорець увімкнено, а виконати неможливо.

    Викликається **до** побудови таблиці. Мовчазний прапорець гірший за його відсутність:
    читач, який попросив четвертий рядок і отримав три, не дізнається, що нічого не сталося.
    """
    if wanted() and (reason := unavailable_because()):
        raise Demanded(
            f"{FLAG} увімкнено, але {NAME} виконати неможливо: {reason}. "
            f"Прибери {FLAG} або дай те, чого бракує — мовчки пропустити не можу."
        )


def run(client: Any, *, tracer: Any = None) -> contract.Result:
    """Один агент з одним інструментом. Координація явна, але живе в конфігурації."""
    from google.adk.agents import Agent  # noqa: PLC0415

    used: list[str] = []

    def search_notes(query: str) -> str:
        """Знайти нотатки в базі знань NovaShop."""
        used.append(contract.TOOL)
        if tracer is not None:
            tracer.step("tool", tool=contract.TOOL)
        return contract.search_notes(query)

    agent = Agent(
        name="novashop_support",
        model=_model(client),
        instruction=contract.RESEARCH_PROMPT,
        tools=[search_notes],
    )
    if tracer is not None:
        tracer.step("agent", tools=1)
    answer = _ask(agent, contract.QUESTION)

    return contract.Result(
        name=NAME,
        asked=contract.QUESTION,
        answer=answer,
        tools_used=tuple(used),
        stopped_by=contract.ANSWERED if answer.strip() else contract.OUT_OF_BUDGET,
        model_calls=0,
        coordination=COORDINATION,
        why_source=WHY_SOURCE,
        steps=("agent",),
    )


def _model(client: Any) -> Any:
    """Наш клієнт у формі, яку розуміє ADK (ADR-0007).

    ADK узагалі не передбачає OpenAI-сумісного клієнта ззовні: він ходить до Gemini власним
    транспортом. Тому тут — обгортка через `LiteLlm`, задокументовану точку для чужих
    провайдерів. Це і є та сама «вмовляння бібліотеки», яку ADR-0007 називає ціною риштувань.
    """
    from google.adk.models.lite_llm import LiteLlm  # noqa: PLC0415

    return LiteLlm(model="openai/fake", client=client)


def _ask(agent: Any, question: str) -> str:
    """Один прогін агента. ADK віддає події, а не рядок, — беремо останній текст."""
    from google.adk.runners import InMemoryRunner  # noqa: PLC0415

    runner = InMemoryRunner(agent=agent, app_name="s09")
    said = ""
    for event in runner.run(user_id="learner", session_id="s09", new_message=question):
        for part in getattr(getattr(event, "content", None), "parts", []) or []:
            if text := getattr(part, "text", ""):
                said = text
    return said


def traced(client: Any, path: Any) -> contract.Result:
    with trace_run(NAME, path=path, stage="s09", case=NAME) as tracer:
        return run(client, tracer=tracer)
