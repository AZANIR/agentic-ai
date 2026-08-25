"""Кроки трейсу — у траєкторії. Ключ групування подається параметром (ADR-0001).

**Чому не фіксоване поле.** Два етапи групують по-різному, і обидва праві:

    етап 1   один `trace_run` на сценарій   -> траєкторія = `trace_id`
    етап 6   один `trace_run` на процес     -> траєкторія = `trace_ref` запиту

Групування по `trace_id` дало б на сервісі етапу 6 **одну** траєкторію на весь час життя
процесу. Групування по `trace_ref` на етапі 1 не дало б нічого. Фіксувати одне означало б
оголосити другий етап зламаним — і переписати його, порушивши обмеження C-2.

Тому знання про формат живе тут, в одному модулі, а рівні оцінювання бачать `Trajectory` і
про джерело не знають нічого.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shared.trace import iter_steps

# Кроки, що обрамляють прогін. Вони не є роботою агента, і рівні мають бачити різницю:
# траєкторія з двох кроків, обидва з яких — обрамлення, це порожній прогін, а не короткий.
START = "run_start"
END = "run_end"
ERROR = "run_error"
FRAME = frozenset({START, END, ERROR})

# Кроки, у яких говорить МОДЕЛЬ. Поле `text` є і в результатів інструментів, тож без
# цього переліку «остання відповідь» була б останнім рядком будь-якого походження.
SPEAKING = frozenset({"llm_call", "answered", "say", "speak", "think"})

# Поля, якими етапи позначають «який це прогін». Перелік **вимірюється**, а не
# оголошується: `survey_run_keys()` шукає їх у джерелах, і саме її число потрапляє в урок.
RUN_KEYS = ("scenario", "scene", "trace_ref", "run", "case")

Key = Callable[[dict[str, Any]], str | None]


def by_trace_id(step: dict[str, Any]) -> str | None:
    """Одна траєкторія на прогін. Так пишуть етапи 1–5 і 7."""
    return step.get("trace_id")


def by_ref(step: dict[str, Any]) -> str | None:
    """Одна траєкторія на запит. Так пише сервіс етапу 6.

    Кроки **без** `trace_ref` повертають `None` і в жодну траєкторію не потрапляють: це
    обрамлення процесу, а не запиту. Відкат на `trace_id` виглядав би безпечнішим і дав би
    зайву траєкторію з двох кроків, яку кожен рівень мусив би окремо ігнорувати.
    """
    return step.get("trace_ref")


@dataclass
class Trajectory:
    """Впорядковані кроки одного прогону агента."""

    key: str
    steps: list[dict[str, Any]] = field(default_factory=list)

    @property
    def length(self) -> int:
        """Скільки кроків зробив агент. Обрамлення не рахується."""
        return sum(1 for step in self.steps if step["kind"] not in FRAME)

    def of_kind(self, *kinds: str) -> list[dict[str, Any]]:
        return [step for step in self.steps if step["kind"] in kinds]

    def tools(self) -> list[str]:
        """Інструменти в порядку виклику, включно з відхиленими й невідомими.

        Відхилений виклик — теж рішення агента, і саме воно найцікавіше для траєкторії:
        перелік, який показує лише вдалі виклики, показує відредаговану історію.
        """
        called = self.of_kind("tool_call", "tool_rejected", "tool_error", "tool_unknown")
        return [step["tool"] for step in called if "tool" in step]

    def outcome(self) -> str | None:
        """Чим скінчився прогін, якщо це записано."""
        for step in reversed(self.steps):
            if step["kind"] == END:
                return str(step.get("status", "ok"))
            if step["kind"] == ERROR:
                return "error"
        return None

    def answer(self) -> str | None:
        """Остання відповідь **моделі**, або `None`, якщо агент не сказав нічого.

        Вид кроку обмежений `SPEAKING`: результат інструмента з полем `text` теж рядок, і
        без обмеження він став би «останньою відповіддю», визначивши вердикт e2e. Правило
        приписування каже «e2e про ОСТАННЮ ВІДПОВІДЬ і ні про що інше».

        `None` і `""` — різні факти, і рівень оцінювання розрізняє їх: перше означає, що
        агент не відповідав, друге — що відповів порожньо.
        """
        for step in reversed(self.steps):
            if step["kind"] not in SPEAKING:
                continue
            for name in ("answer", "text", "reply"):
                if isinstance(step.get(name), str):
                    return step[name]
        return None


def extract(path: Path | str, *, key: Key = by_trace_id) -> list[Trajectory]:
    """Витягнути траєкторії з файлу трейсів.

    Порядок кроків — за `seq`, а не за порядком у файлі: два процеси, що пишуть в один
    файл, чергують рядки, і читання «як лежить» дало б перемішану історію.
    """
    grouped: dict[str, Trajectory] = {}
    for step in iter_steps(path):
        name = key(step)
        if name is None:
            continue
        grouped.setdefault(name, Trajectory(key=name)).steps.append(step)
    for trajectory in grouped.values():
        trajectory.steps.sort(key=lambda step: step.get("seq", 0))
    return list(grouped.values())


def survey_run_keys(stages: Path | str) -> dict[str, str | None]:
    """Яким полем кожен етап позначає прогін — **виміряно з джерел**, а не з памʼяті.

    Це і є відповідь на питання, яке етап 6 двічі відклав сюди (ADR-0008). Вона мусить
    обчислюватись, а не стояти числом у прозі: попередня редакція називала чотири поля й
    два етапи без ключа, і помилялась двічі — рахувала фазу відмови етапу 4 за ключ
    прогону й забула про етап 7.

    :returns: ``{"s01": "scenario", "s02": None, …}`` — `None` означає «ключа немає».
    """
    found: dict[str, str | None] = {}
    for package in sorted(Path(stages).glob("s[0-9][0-9]_*")):
        name = package.name[:3]
        if name >= "s08":  # оцінювання не міряє себе
            continue
        written: set[str] = set()
        for path in sorted(package.glob("*.py")):
            if path.name == "check.py":  # перевірки не є прогоном етапу
                continue
            written |= _traced_fields(path.read_text(encoding="utf-8"))
        found[name] = next((key for key in RUN_KEYS if key in written), None)
    return found


def _traced_fields(source: str) -> set[str]:
    """Іменовані аргументи, що доїжджають у трейс: `.step(...)` і `trace_run(...)`.

    Греп по `"scenario="` дав би хибний вимір: у етапі 7 є `whole(run=run)` — параметр
    функції, а не поле кроку. Помилка того самого роду, що й зарахування фази відмови
    етапу 4 за ключ прогону, і саме вона зробила попереднє число неправдою.
    """
    fields: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        named = callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", "")
        if named not in ("step", "trace_run"):
            continue
        fields |= {word.arg for word in node.keywords if word.arg}
    return fields
