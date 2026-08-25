"""Та сама задача на LangGraph: **явна** координація вузлами й ребрами.

    pip install -e ".[s09]"

Модуль **необов'язковий**: без встановленої бібліотеки рядок таблиці стає «не перевірено», а
етап проходиться до кінця (ADR-0006).

Читати варто **після** `baseline.py`, і заради впізнавання: тут ті самі три кроки під іншими
назвами.

    послідовність рядків   ->  add_edge між вузлами
    локальна змінна `note` ->  поле в TypedDict, що їде між вузлами
    кінець функції         ->  END

**Де тут координація.** У ребрах, і тільки в них. Прочитавши `_wire()`, ти знаєш увесь
можливий порядок кроків, не читаючи жодного вузла. Це і є явна координація, і це її головна
властивість: питання «чому виконався цей крок» має відповідь в одному місці.

**Що вона коштує.** Рядки. Ті самі три кроки описані двічі — раз як функції, раз як граф, — і
поверх цього треба оголосити тип стану, бо ним переносяться значення.

**Чого вона НЕ коштує.** Токенів. LangGraph вирішує **порядок**, а не зміст: до моделі їде
рівно те, що склав автор. Надбавка нульова, і це не дрібниця — це показує, що «фреймворк
дорожчий у токенах» не є законом, а є властивістю **конкретного** фреймворка.

**Клієнт подається ззовні** й їде в стані (ADR-0007). Це найбільша частина файлу, і вона теж
є знахідкою: рядки, витрачені на те, щоб не дати бібліотеці зробити по-своєму, — теж ціна
риштувань, і вони чесно потрапляють у колонку «мої рядки».
"""

from __future__ import annotations

from typing import Any, TypedDict

from shared.llm import get_model
from shared.trace import trace_run
from stages.s09_frameworks import contract

NAME = "LangGraph"
PACKAGE = "langgraph"
COORDINATION = "явна"
WHY_SOURCE = "граф: увесь порядок видно в одному місці"


class Carried(TypedDict, total=False):
    """Те, що LangGraph переносить між вузлами. Клієнт їде тут — власного бібліотека не бачить."""

    client: Any
    tracer: Any
    note: str
    answer: str
    used: list[str]
    steps: list[str]


def ask(client: Any, messages: list[dict[str, Any]], *, tools: bool = False) -> Any:
    """Той самий виклик моделі — і навмисно **свій**, а не запозичений у базової лінії.

    Спільний хелпер робив колонку «мої рядки» несиметричною: базова лінія несла ці пʼять
    рядків у своїх, а LangGraph діставав їх безкоштовно. Помилка йшла в бік «фреймворк
    дешевший» — рівно той бік, від якого застерігає розвʼязок вправи 3.

    Етапи цього курсу й так навмисно дублюють ідеї замість ділитися кодом; тут дублювання
    ще й обовʼязкове, бо інакше вимір бреше на пʼять рядків.
    """
    payload: dict[str, Any] = {"model": get_model(), "messages": messages}
    if tools:
        payload["tools"] = [contract.TOOL_SCHEMA]
    return client.chat.completions.create(**payload).choices[0].message


def unavailable_because() -> str:
    """Чому реалізацію не можна виконати тут. Порожньо — можна.

    Той самий протокол, що в решти трьох. Перша редакція мала лише `available()`, і збірка
    таблиці її не питала — тож на установці без пакета реалізація не пропускалась, а падала
    вже всередині `_wire()`. Різні імена для одного питання — і одне з них ніхто не кликав.
    """
    try:
        import langgraph.graph  # noqa: F401, PLC0415
    except ImportError:
        return 'пакета немає — постав `pip install -e ".[s09]"`'
    return ""


def available() -> bool:
    return not unavailable_because()


def _research(carried: Carried) -> Carried:
    message = ask(
        carried["client"],
        [{"role": "user", "content": contract.RESEARCH_PROMPT}],
        tools=True,
    )
    _step(carried, "research", tools=len(message.tool_calls or []))
    used, note = list(carried.get("used", [])), ""
    for call in message.tool_calls or []:
        import json  # noqa: PLC0415

        used.append(call.function.name)
        note = contract.search_notes(json.loads(call.function.arguments).get("query", ""))
        _step(carried, "tool", tool=call.function.name)
    return {**carried, "used": used, "note": note, "steps": [*carried.get("steps", []), "research"]}


def _writer(carried: Carried) -> Carried:
    written = ask(
        carried["client"],
        [{"role": "user", "content": contract.WRITER_PROMPT.format(note=carried["note"])}],
    )
    answer = written.content or ""
    _step(carried, "writer", chars=len(answer))
    return {**carried, "answer": answer, "steps": [*carried.get("steps", []), "writer"]}


def _step(carried: Carried, kind: str, **fields: Any) -> None:
    if (tracer := carried.get("tracer")) is not None:
        tracer.step(kind, **fields)


def _wire() -> Any:
    """Увесь порядок кроків — тут. Саме це й означає «явна координація»."""
    from langgraph.graph import END, START, StateGraph  # noqa: PLC0415

    graph = StateGraph(Carried)
    graph.add_node("research", _research)
    graph.add_node("writer", _writer)
    graph.add_edge(START, "research")
    graph.add_edge("research", "writer")
    graph.add_edge("writer", END)
    return graph.compile()


def run(client: Any, *, tracer: Any = None) -> contract.Result:
    final: Carried = _wire().invoke({"client": client, "tracer": tracer, "used": [], "steps": []})
    answer = final.get("answer", "")
    return contract.Result(
        name=NAME,
        asked=contract.QUESTION,
        answer=answer,
        tools_used=tuple(final.get("used", [])),
        stopped_by=contract.ANSWERED if answer.strip() else contract.OUT_OF_BUDGET,
        model_calls=0,
        coordination=COORDINATION,
        why_source=WHY_SOURCE,
        steps=tuple(final.get("steps", [])),
    )


def traced(client: Any, path: Any) -> contract.Result:
    with trace_run(NAME, path=path, stage="s09", case=NAME) as tracer:
        return run(client, tracer=tracer)
