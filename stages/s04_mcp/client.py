"""stdio-клієнт: підняти сервер, спитати, що він уміє, викликати, погасити.

Уся робота з протоколом асинхронна, але етапи 1–3 синхронні — і переписувати їх заради
транспорту було б рівно тим, чого етап уникає. Тому назовні модуль дає **синхронні** функції,
а `asyncio.run` живе всередині. Ціна названа: один виклик — одне підняття процесу.

**Головне в цьому файлі — не виклик, а те, як він ламається.** Функція, яку ти імпортував,
могла кинути виняток. Процес може не запуститись зовсім, замовкнути посеред відповіді або
відповісти те, у чому нема даних. Це **три різні події**, і плутати їх дорого:

    startup   сервер не піднявся      -> неправильна команда, зламане оточення, немає пакета
    call      піднявся й замовк       -> тайм-аут; сервер живий, але відповіді не буде
    parse     відповів, даних немає   -> сервер працює, контракт розійшовся

З тексту винятку вони часто невідрізненні, а виправляються по-різному. Тому фаза — **поле
результату**, а не рядок у повідомленні.

**Тайм-аут обов'язковий.** Без нього «замовк посеред виклику» перетворюється на зависання, а
зависання — це та сама помилка, що нічого не ламає: жодного винятку, жодного логу, просто
процес, який стоїть.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from stages.s04_mcp.parse import NoPayload, describe_failure, extract_payload

SERVER_MODULE = "stages.s04_mcp.server"
TIMEOUT = 20.0


@dataclass
class ToolInfo:
    """Інструмент так, як його оголосив сервер. Схема — те, що піде моделі."""

    name: str
    description: str
    schema: dict[str, Any]


@dataclass
class CallResult:
    """Чим завершився виклик. Порожній `payload` із заповненою `failure` — теж результат."""

    payload: Any = None
    raw: str = ""
    failure: dict[str, str] | None = field(default=None)

    @property
    def ok(self) -> bool:
        return self.failure is None


def _params(module: str = SERVER_MODULE, *, broken: bool = False) -> Any:
    from mcp import StdioServerParameters

    args = ["-c", "import sys; sys.exit(3)"] if broken else ["-m", module]
    return StdioServerParameters(command=sys.executable, args=args)


@asynccontextmanager
async def _session(params: Any, errlog: Any) -> AsyncIterator[Any]:
    """Сесія як контекстний менеджер, а не як асинхронний генератор.

    Перша версія була генератором, і `async for ...: return` лишав його незакритим: anyio
    виходив зі свого cancel scope уже в іншій задачі, під час збирання сміття, і в stderr
    летіло `Attempted to exit cancel scope in a different task`. Виклик при цьому **успішно
    повертав дані** — тобто помилка нічого не ламала, лише шуміла. Рівно той клас, про який
    написаний етап 3.
    """
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    # errlog — справжній файл, а не буфер у пам'яті: підпроцес отримує дескриптор, і
    # `io.StringIO` тут дає `AttributeError: fileno`. Викидати stderr теж не можна —
    # часто це єдине, що пояснює, чому процес не піднявся.
    async with (
        stdio_client(params, errlog=errlog) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        yield session


async def _list(params: Any, errlog: Any) -> list[ToolInfo]:
    async with _session(params, errlog) as session:
        listed = await session.list_tools()
        return [ToolInfo(t.name, t.description or "", t.input_schema) for t in listed.tools]


async def _call(params: Any, errlog: Any, name: str, arguments: dict[str, Any]) -> str:
    async with _session(params, errlog) as session:
        result = await session.call_tool(name, arguments)
        if result.is_error:
            raise RuntimeError(f"сервер відхилив виклик {name!r}")
        return chr(10).join(getattr(item, "text", "") for item in result.content)


def list_tools(*, module: str = SERVER_MODULE, broken: bool = False) -> list[ToolInfo]:
    """Спитати сервер, що він уміє. Саме цей виклик робить інтеграцію дискаверабельною."""
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errlog:
        return asyncio.run(asyncio.wait_for(_list(_params(module, broken=broken), errlog), TIMEOUT))


def call_tool(
    name: str,
    arguments: dict[str, Any],
    *,
    module: str = SERVER_MODULE,
    broken: bool = False,
    timeout: float = TIMEOUT,
    tracer: Any = None,
) -> CallResult:
    """Викликати інструмент і розібрати відповідь. Кожна фаза відмови названа окремо."""
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errlog:
        try:
            raw = asyncio.run(
                asyncio.wait_for(
                    _call(_params(module, broken=broken), errlog, name, arguments), timeout
                )
            )
        except TimeoutError as error:
            return _traced(
                CallResult(failure=describe_failure(error, phase="call")), name, arguments, tracer
            )
        except Exception as error:  # noqa: BLE001 — процес не піднявся; причин десятки, наслідок один
            failure = describe_failure(error, phase="startup")
            failure["reason"] = _with_stderr(failure["reason"], errlog)
            return _traced(CallResult(failure=failure), name, arguments, tracer)

    try:
        payload = extract_payload(raw)
    except NoPayload as error:
        return _traced(
            CallResult(raw=raw, failure=describe_failure(error, phase="parse")),
            name,
            arguments,
            tracer,
        )
    return _traced(CallResult(payload=payload, raw=raw), name, arguments, tracer)


def _with_stderr(reason: str, errlog: Any) -> str:
    """Додати останній рядок stderr сервера — часто це єдине пояснення."""
    errlog.seek(0)
    noise = errlog.read().strip()
    return f"{reason} | сервер написав: {noise.splitlines()[-1]}" if noise else reason


def _traced(result: CallResult, name: str, arguments: dict[str, Any], tracer: Any) -> CallResult:
    """Виклик без сліду не існує як стан (AC-08b)."""
    if tracer is not None:
        tracer.step(
            "mcp_call",
            server=SERVER_MODULE,
            tool=name,
            arguments=arguments,
            ok=result.ok,
            phase=(result.failure or {}).get("phase"),
        )
    return result
