"""Демонстрація етапу 1: чотири сценарії підряд.

    python -m stages.s01_agent_loop.run

Працює **без API-ключа**: без налаштованого провайдера відповіді дає підробка за записаним
сценарієм, і перший рядок виводу про це прямо каже. Заповни ``LLM_*`` у ``.env`` — і та сама
команда піде до справжньої моделі, не змінивши жодного рядка коду.

Кожен сценарій ілюструє свій критерій приймання:

    1. вибір між інструментами   AC-01
    2. криві аргументи           AC-03
    3. зупинка лімітом кроків    AC-02
    4. гейт підтвердження        AC-04
"""

from __future__ import annotations

import sys
from pathlib import Path

from shared.config import settings
from shared.fake_llm import text, tool_call
from shared.llm import banner, get_client, is_fake
from shared.trace import trace_run
from stages.s01_agent_loop.loop import RunResult, run_agent

SCENARIO_TITLES = [
    "1. Модель обирає між інструментами",
    "2. Модель просить інструмент із кривими аргументами",
    "3. Модель не може завершити — спрацьовує ліміт кроків",
    "4. Модель просить незворотну дію — спрацьовує гейт підтвердження",
]

# Сценарії підробленої моделі. Це не «заглушки»: тут записано, ЩО САМЕ має зробити модель,
# тож сценарій читається як специфікація її поведінки. Зі справжнім провайдером ці рядки
# ігноруються — модель вирішує сама.
SCRIPTS = [
    [
        tool_call("get_order_status", {"order_id": "ord_4471"}),
        text("Ваше замовлення ord_4471 у дорозі, очікується за 2 дні."),
    ],
    [
        tool_call("get_weather", {"town": "Київ"}),
        tool_call("get_weather", {"city": "Київ"}),
        text("У Києві +28°C, мінлива хмарність."),
    ],
    [tool_call("get_order_status", {"order_id": "ord_4471"})],  # repeat_last -> нескінченно
    [
        tool_call("initiate_return", {"order_id": "ord_4472", "reason": "завеликий розмір"}),
        # Другий крок потрібен саме для вправи 1: коли читач вимкне гейт, прогін піде далі,
        # і перевірка впаде на ассерті «дію виконано без підтвердження», а не на вичерпаному
        # сценарії підробки. Тест має червоніти від порушення інваріанта, не від службової помилки.
        text("Повернення оформлено."),
    ],
]

TASKS = [
    "Де моє замовлення ord_4471?",
    "Яка погода в Києві?",
    "Розкажи все, що знаєш, і ніколи не зупиняйся.",
    "Оформи повернення для ord_4472, він завеликий.",
]


def _print_run(result: RunResult) -> None:
    for message in result.transcript:
        role = message.get("role")
        if role == "assistant" and message.get("tool_calls"):
            for call in message["tool_calls"]:
                fn = call["function"]
                print(f"    -> модель просить {fn['name']}({fn['arguments']})")
        elif role == "tool" and not result.blocked_tools:
            # Для заблокованого кроку той самий текст уже друкується нижче — двічі не треба.
            print(f"    <- {message['content']}")

    if result.stopped_by_limit:
        print(f"    !! зупинено лімітом кроків після {result.steps} кроків, відповіді немає")
    elif result.blocked_tools:
        print(f"    !! крок заблоковано гейтом: {', '.join(result.blocked_tools)}")
        for line in (result.answer or "").splitlines():
            print(f"       {line}")
    else:
        print(f"    =  {result.answer}")


def main(*, confirmed: bool = False, trace_path: Path | str | None = None) -> int:
    """Прогнати всі чотири сценарії. Повертає код виходу.

    :param confirmed: дозвіл на незворотні дії. Приходить окремим запуском
        (``python -m stages.s01_agent_loop.run --confirm``), а не питанням у консолі —
        ADR етапу 0002.

    :param trace_path: куди писати трейс. За замовчуванням — робочий файл ``traces/``,
        який потім читає етап 8. Перевірка передає тимчасовий шлях: тест, що засмічує
        робочі дані, рано чи пізно зіпсує саме той прогін, який ти хотів роздивитись.
    """
    print(banner(get_client(demo_script=[])))
    print()

    for index, (task, script) in enumerate(zip(TASKS, SCRIPTS, strict=True)):
        title = SCENARIO_TITLES[index]
        print(title)
        print("-" * len(title))
        print(f"    користувач: {task}")

        client = get_client(demo_script=script)
        # Третій сценарій має крутитися, доки не спрацює ліміт — саме це й перевіряємо.
        if is_fake(client) and index == 2:
            client.repeat_last = True

        with trace_run(
            SCENARIO_TITLES[index], path=trace_path, stage="s01", scenario=index + 1
        ) as tracer:
            result = run_agent(
                task,
                client=client,
                tracer=tracer,
                max_steps=3 if index == 2 else settings.agent_max_steps,
                confirmed=confirmed,
            )
        _print_run(result)
        print()

    if not confirmed:
        print("Щоб підтвердити незворотну дію зі сценарію 4:")
        print("    python -m stages.s01_agent_loop.run --confirm")
        print()
    if trace_path is None:
        print("Трейси прогонів: traces/ — їх читатиме етап 8.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(confirmed="--confirm" in sys.argv))
