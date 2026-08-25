"""Та сама задача на CrewAI: **неявна** координація ролями й описами.

    pip install -e ".[s09]"      # на Python 3.10–3.13

**Цей файл написано, але жодного разу не прогнано в цьому репозиторії.** Причина не в лінощах
автора, і вона є найкориснішою знахідкою етапу: **CrewAI не встановлюється на Python 3.14.**
Жодна його версія — від 0.1.0 до 1.15 — не оголошує підтримки: усі вимагають `<3.14` або
`<=3.13`. Репозиторій працює на 3.14.

Це не збій і не привід сховати рядок. Обмеження інтерпретатора — теж обмеження, і воно
вирішує вибір **першим**, ще до питання про елегантність. Жодне порівняння фреймворків у
блогах цього не показує, бо всі вони написані на тій версії, де все встановилось.

Тому:

    прогнати тут          неможливо -> стан «не перевірено» з НАЗВАНОЮ причиною
    прогнати на 3.12      можливо   -> перевірка виконує контракт і червоніє, якщо я помилився
    приховати рядок       не можна  -> три рядки виглядали б як усі

**Де тут координація.** У полях `role`, `goal`, `backstory` і `description`. Порядок кроків
задає `Process.sequential`, але **чому** агент зробив саме це — у тексті опису, а не в коді.
Питання «чому виконався цей крок» вимагає прочитати чотири описи й уявити, як їх прочитала
модель.

**Що вона коштує.** Токени. Кожен опис їде до моделі на кожному кроці, і саме ця різниця
потрапляє в колонку «понад запит».

**Чого вона НЕ коштує.** Рядків опису графа: їх тут немає взагалі.

**Клієнт подається ззовні** через `BaseLLM` — задокументована точка розширення (ADR-0007).
Це найбільша частина файлу, і вона теж є знахідкою: рядки, витрачені на те, щоб не дати
бібліотеці піти в мережу власним шляхом, — теж ціна риштувань.
"""

from __future__ import annotations

import sys
from typing import Any

from shared.trace import trace_run
from stages.s09_frameworks import contract

NAME = "CrewAI"
PACKAGE = "crewai"
COORDINATION = "неявна"
WHY_SOURCE = "описи ролей: причину видно лише в тексті, який прочитала модель"

# Найвища версія Python, яку CrewAI оголошує підтримуваною. Перевіряється **до** імпорту:
# інакше «немає пакета» й «пакет неможливо встановити» злилися б в одну причину, а це різні
# події з різними діями читача.
MAX_PYTHON = (3, 13)


def unavailable_because() -> str:
    """Чому реалізацію не можна виконати тут. Порожньо — можна.

    Три стани, а не два. «Не встановлено» лікується встановленням; «не встановлюється»
    не лікується нічим, крім іншого інтерпретатора, і читач має знати, який саме випадок
    у нього.
    """
    if sys.version_info[:2] > MAX_PYTHON:
        got = ".".join(map(str, sys.version_info[:2]))
        top = ".".join(map(str, MAX_PYTHON))
        return f"CrewAI не підтримує Python {got}: остання підтримувана — {top}"
    try:
        import crewai  # noqa: F401, PLC0415
    except ImportError:
        return 'пакета немає — постав `pip install -e ".[s09]"`'
    return ""


def available() -> bool:
    return not unavailable_because()


def _llm(client: Any) -> Any:
    """Наш клієнт у формі, яку розуміє CrewAI. Точка розширення — `BaseLLM.call`."""
    from crewai import BaseLLM  # noqa: PLC0415

    class Counted(BaseLLM):
        def __init__(self) -> None:
            super().__init__(model="fake")
            self._client = client

        def call(
            self,
            messages: Any,
            tools: Any = None,
            callbacks: Any = None,
            available_functions: Any = None,
        ) -> str:
            if isinstance(messages, str):
                messages = [{"role": "user", "content": messages}]
            payload: dict[str, Any] = {"model": "fake", "messages": messages}
            if tools:
                payload["tools"] = tools
            message = self._client.chat.completions.create(**payload).choices[0].message
            for call in message.tool_calls or []:
                import json  # noqa: PLC0415

                name = call.function.name
                if available_functions and name in available_functions:
                    arguments = json.loads(call.function.arguments)
                    return str(available_functions[name](**arguments))
            return message.content or ""

        def supports_function_calling(self) -> bool:
            return True

        def get_context_window_size(self) -> int:
            return 8192

    return Counted()


def _tool(used: list[str], tracer: Any) -> Any:
    """Інструмент контракту у формі CrewAI. Той самий текст, той самий єдиний інструмент."""
    from crewai.tools import BaseTool  # noqa: PLC0415

    class Notes(BaseTool):
        name: str = contract.TOOL
        description: str = contract.TOOL_SCHEMA["function"]["description"]

        def _run(self, query: str = "") -> str:
            used.append(contract.TOOL)
            if tracer is not None:
                tracer.step("tool", tool=contract.TOOL)
            return contract.search_notes(query)

    return Notes()


def run(client: Any, *, tracer: Any = None) -> contract.Result:
    from crewai import Agent, Crew, Process, Task  # noqa: PLC0415

    used: list[str] = []
    llm, notes = _llm(client), _tool(used, tracer)

    researcher = Agent(
        role="дослідник бази знань NovaShop",
        goal="знайти нотатки, що відповідають на питання клієнта",
        backstory="Ти шукаєш у базі знань і не вигадуєш нічого понад знайдене.",
        tools=[notes],
        llm=llm,
        allow_delegation=False,
    )
    writer = Agent(
        role="автор відповіді підтримки NovaShop",
        goal="написати коротку відповідь, спираючись лише на знайдені нотатки",
        backstory="Ти пишеш стисло й не додаєш того, чого немає в нотатках.",
        llm=llm,
        allow_delegation=False,
    )

    crew = Crew(
        agents=[researcher, writer],
        tasks=[
            Task(
                description=contract.RESEARCH_PROMPT,
                expected_output="нотатки з бази знань",
                agent=researcher,
            ),
            Task(
                description=contract.WRITER_PROMPT.format(note=contract.NOTE),
                expected_output="коротка відповідь клієнту",
                agent=writer,
            ),
        ],
        process=Process.sequential,
    )
    if tracer is not None:
        tracer.step("crew", agents=2, tasks=2)
    answer = str(crew.kickoff())

    return contract.Result(
        name=NAME,
        asked=contract.QUESTION,
        answer=answer,
        tools_used=tuple(used),
        stopped_by=contract.ANSWERED if answer.strip() else contract.OUT_OF_BUDGET,
        model_calls=0,
        coordination=COORDINATION,
        why_source=WHY_SOURCE,
        steps=("research", "writer"),
    )


def traced(client: Any, path: Any) -> contract.Result:
    with trace_run(NAME, path=path, stage="s09", case=NAME) as tracer:
        return run(client, tracer=tracer)
