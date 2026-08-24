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


class ServerUnreachable(Exception):
    """Сервер не піднявся. Причина вже розгорнута з групи винятків і має слова."""


class ServerRefused(Exception):
    """Сервер живий і відповів — відмовою. Це не «не піднявся».

    Без окремого типу цей випадок ловився широким `except` і ставав фазою `startup`:
    справний сервер, який просто не знає такого інструмента, діагностувався як зламане
    оточення. Рівно та підміна, проти якої написаний увесь модуль.
    """


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
            raise ServerRefused(f"сервер відхилив виклик {name!r}")
        return "\n".join(getattr(item, "text", "") for item in result.content)


def list_tools(
    *, module: str = SERVER_MODULE, broken: bool = False, tracer: Any = None
) -> list[ToolInfo]:
    """Спитати сервер, що він уміє. Саме цей виклик робить інтеграцію дискаверабельною.

    Відмови обробляються так само, як у `call_tool`. Перша редакція лишала їх голими, і
    `list_tools(broken=True)` кидав `ExceptionGroup: unhandled errors in a TaskGroup` —
    дослівно той рядок, який урок цього ж етапу наводить як приклад повідомлення, що
    виглядає поясненням і ним не є.
    """
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errlog:
        try:
            tools = asyncio.run(
                asyncio.wait_for(_list(_params(module, broken=broken), errlog), TIMEOUT)
            )
        except Exception as error:  # noqa: BLE001 — причин десятки, наслідок один
            failure = describe_failure(error, phase="startup")
            failure["reason"] = _with_stderr(failure["reason"], errlog)
            _step(tracer, "mcp_list", ok=False, phase=failure["phase"], count=0)
            raise ServerUnreachable(failure["reason"]) from error
    _step(tracer, "mcp_list", ok=True, phase=None, count=len(tools))
    return tools


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
        except Exception as error:  # noqa: BLE001 — причин десятки, фаз три
            failure = describe_failure(error, phase=_phase_of(error))
            if failure["phase"] == "startup":
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


def _phase_of(error: BaseException) -> str:
    """Фаза за РОЗГОРНУТОЮ причиною, а не за типом того, що прилетіло назовні.

    Тайм-аут і відмова сервера означають одне: процес живий, відповіді по суті немає.
    Але `anyio` загортає виняток із задачі у `BaseExceptionGroup`, тож `except
    ServerRefused` його не бачить — і жива, справна відмова діагностувалась як «процес
    не піднявся». Та сама група, що ховала й текст причини.
    """
    while isinstance(error, BaseExceptionGroup) and error.exceptions:
        error = error.exceptions[0]
    return "call" if isinstance(error, TimeoutError | ServerRefused) else "startup"


def _step(tracer: Any, kind: str, **fields: Any) -> None:
    """Крок у трейс, якщо трейсер є. Один спосіб — щоб жоден виклик не лишився без сліду."""
    if tracer is not None:
        tracer.step(kind, server=SERVER_MODULE, **fields)


def _with_stderr(reason: str, errlog: Any) -> str:
    """Додати останній рядок stderr сервера — часто це єдине пояснення."""
    errlog.seek(0)
    noise = errlog.read().strip()
    return f"{reason} | сервер написав: {noise.splitlines()[-1]}" if noise else reason


def _traced(result: CallResult, name: str, arguments: dict[str, Any], tracer: Any) -> CallResult:
    """Виклик без сліду не існує як стан (AC-08b)."""
    # AC-02 вимагає у трейсі ОБИДВІ сторони: що надіслали й що отримали. Перша редакція
    # писала лише відправлення й булеве `ok` — за таким записом неможливо сказати, чим
    # виклик завершився насправді.
    _step(
        tracer,
        "mcp_call",
        tool=name,
        arguments=arguments,
        ok=result.ok,
        phase=(result.failure or {}).get("phase"),
        result=str(result.payload)[:200] if result.ok else (result.failure or {}).get("reason"),
    )
    return result
