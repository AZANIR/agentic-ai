"""Гейт підтвердження незворотних дій — третій захист.

Винесений з ``loop.py`` окремим модулем після рев'ю: гейт має працювати на рівні **кроку**,
а не окремого виклику, і ця логіка більше не вміщається в цикл, не роздуваючи його понад
ліміт у 120 рядків. Мітигація була записана заздалегідь (`sad.md` §11).

Чому крок, а не виклик. Модель може попросити кілька інструментів **однією відповіддю**.
Якщо перевіряти їх по одному, виходить ось що:

    без підтвердження  -> блокуємо на першому незворотному; про решту Learner не дізнається
    з підтвердженням   -> виконуємо ВСІ, включно з тими, яких він ніколи не бачив

Тобто підтвердження стає бланкетним дозволом на все, що модель попросить наступного разу, —
а урок обіцяє протилежне: «прогін показує, що саме сталося б; підтверджувати наосліп — не
підтвердження». Тому гейт дивиться на весь крок одразу, перелічує **всі** незворотні дії з
аргументами й зупиняє прогін, доки їх не підтвердять разом.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from stages.s01_agent_loop.tools import Tool


@dataclass(frozen=True)
class BlockedStep:
    """Крок, зупинений гейтом: які саме дії чекають на підтвердження."""

    names: tuple[str, ...]
    message: str


def _readable(arguments: Any) -> str:
    if isinstance(arguments, dict):
        return ", ".join(f"{key}={value}" for key, value in arguments.items())
    return str(arguments)


def _describe(call: Any) -> str:
    try:
        arguments = json.loads(call.function.arguments)
    except json.JSONDecodeError:
        arguments = call.function.arguments
    return f"  · {call.function.name}({_readable(arguments)})"


def screen(tool_calls: list[Any], tools: dict[str, Tool], *, confirmed: bool) -> BlockedStep | None:
    """Перевірити ВЕСЬ крок перед виконанням хоч чогось.

    Повертає ``None``, якщо крок можна виконувати, або :class:`BlockedStep` із переліком
    усіх незворотних дій. Порядок важливий: спершу дивимось на всі виклики кроку, і лише
    потім виконуємо перший — інакше частина дій уже сталася б до того, як ми вирішили питати.
    """
    if confirmed:
        return None

    irreversible = [
        c for c in tool_calls if (tool := tools.get(c.function.name)) and tool.irreversible
    ]
    if not irreversible:
        return None

    listed = "\n".join(_describe(call) for call in irreversible)
    # Узгодження за числом робимо цілими фразами, а не склеюванням закінчень: склеювання
    # дає «незворотну дію, які потребують» — рівно ту помилку, яку легко не помітити
    # англійською й неможливо не помітити українською.
    many = len(irreversible) > 1
    what = "незворотні дії, які потребують" if many else "незворотну дію, яка потребує"
    nothing = "Жодної з них не виконано." if many else "Її не виконано."
    return BlockedStep(
        names=tuple(c.function.name for c in irreversible),
        message=(
            f"Крок зупинено: він містить {what} підтвердження.\n"
            f"Було б виконано:\n{listed}\n"
            f"{nothing} Щоб підтвердити — запусти прогін ще раз із підтвердженням."
        ),
    )
