"""Підключити граф етапу 3 до MCP, не змінивши в ньому жодного рядка.

Теза етапу — що протокол є **деталлю підключення**, а не новою архітектурою. Довести її
можна одним способом: прогнати той самий граф, ті самі шість запитів, і отримати ті самі
маршрути — при тому що інструменти тепер живуть в іншому процесі.

**Де саме шов.** `run_agent` етапу 1 приймає `tools=` і, коли його немає, бере глобальний
`REGISTRY` свого модуля (`loop.py`). Спеціаліст етапу 3 `tools=` не передає — отже, єдина
точка, де можна підмінити джерело реєстру, не торкаючись коду нижніх етапів, — цей самий
глобальний `REGISTRY`.

**Це названо межею, а не рішенням.** Підміна модульної глобалі — прийом для перевірки, а не
для продакшну. Правильно було б, щоб граф приймав реєстр параметром і хтось складав його
згори; така явна композиція з'явиться на етапі 6, коли з'явиться сервіс, якому є що
складати. Тут вона була б зміною етапу 3 — тобто рівно тим, чого етап не робить.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from stages.s01_agent_loop import loop as stage_one_loop
from stages.s04_mcp.bridge import registry


@contextmanager
def tools_from_mcp(*, access: str, tools: list[Any] | None = None, tracer: Any = None):
    """На час блоку інструменти етапу 1 беруться з MCP-сервера.

    Повертає складений реєстр — щоб виклик міг подивитись, що саме туди потрапило.
    """
    built = registry(tools, access=access, tracer=tracer)
    original = stage_one_loop.REGISTRY
    stage_one_loop.REGISTRY = {**original, **built}
    try:
        yield built
    finally:
        stage_one_loop.REGISTRY = original
