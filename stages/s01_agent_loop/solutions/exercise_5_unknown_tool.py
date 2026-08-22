"""Вправа 5 — що робить цикл, коли модель просить неіснуючий інструмент.

    python -m stages.s01_agent_loop.solutions.exercise_5_unknown_tool

Модель може вигадати ім'я інструмента — так само, як вигадує аргументи. Цикл не має від
цього падати: невідоме ім'я це така сама відмова кроку, як і крива схема.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from shared.fake_llm import FakeLLM, text, tool_call
from shared.trace import group_by_trace, trace_run
from stages.s01_agent_loop.loop import run_agent


def main() -> int:
    client = FakeLLM(
        script=[
            tool_call("delete_everything", {"confirm": "yes"}),
            text("Вибач, такого інструмента в мене немає."),
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("вправа 5", path=path) as tracer:
            result = run_agent("видали все", client=client, tracer=tracer)
        steps = next(iter(group_by_trace(path).values()))

    print("Кроки трейсу:")
    for step in steps:
        print(f"  {step['seq']:>2}  {step['kind']}")

    reply = [m for m in result.transcript if m.get("role") == "tool"][-1]["content"]
    print(f"\nЩо цикл повернув моделі:\n  {reply}")
    print(f"\nФінальна відповідь: {result.answer}")

    print(
        "\nЧому у відповіді перелічені доступні інструменти.\n"
        "Модель вигадала ім'я не зі зловмисності, а тому що не мала точного списку в тому\n"
        "місці розмови. Повернути їй перелік — найдешевший спосіб виправити помилку\n"
        "за один крок замість трьох.\n"
        "\nЯкщо перелік прибрати, модель отримає «такого інструмента немає» і не дізнається,\n"
        "які є. Далі вона або вигадає ще одне ім'я, або здасться — обидва варіанти коштують\n"
        "зайвого кола, тобто токенів і затримки.\n"
        "\nМежа: у проді перелік інструментів може бути чутливим сам по собі — тоді його\n"
        "не повертають, а логують і віддають нейтральну відмову. На цьому етапі інструментів\n"
        "три і вони не секрет."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
