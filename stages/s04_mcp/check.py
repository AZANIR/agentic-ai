"""Перевірки етапу 4.

    python -m stages.s04_mcp.check

Офлайн, без ключа. Частина перевірок потребує **справжнього сервера в підпроцесі** — без
встановленого пакета MCP вони позначаються `НЕ ПЕРЕВІРЕНО`, а не проходять: різниця між
«збіглося» і «не перевіряли» має лишатись видимою (урок етапу 3).

Розбір відповіді перевіряється **без сервера** навмисно. Це половина уроку етапу, і вимагати
для неї підпроцесу означало б зробити найважливіші перевірки найповільнішими.
"""

from __future__ import annotations

import ast
import tempfile
import time
from pathlib import Path

from shared.check_runner import NotVerified, run_checks
from shared.trace import iter_steps, trace_run
from stages.s01_agent_loop.tools import REGISTRY
from stages.s02_rag.documents import INTERNAL, PUBLIC
from stages.s04_mcp.client import call_tool, list_tools
from stages.s04_mcp.parse import NoPayload, describe_failure, extract_payload

# Реальна форма відповіді MCP-сервера, який любить поговорити. Проза до, проза після.
CHATTY = """Ось що я знайшов у системі замовлень. Зверніть увагу, що дані актуальні
на момент запиту й можуть змінитися.

```json
{"order_id": "ord_4471", "status": "in_transit", "eta_days": 2}
```

Якщо потрібна історія змін, скористайтеся окремим інструментом.
"""

CLEAN = '{"order_id": "ord_4471", "status": "in_transit", "eta_days": 2}'

PROSE_ONLY = """На жаль, я не зміг обробити цей запит: система замовлень не відповідає.
Спробуйте пізніше або зверніться до підтримки.
"""

EMPTY_LIST = """Пошук виконано.

```json
[]
```
"""


def check_payload_survives_prose_around_it() -> None:
    """ВІДМОВА · parse: дані дістаються з відповіді, обгорнутої прозою"""
    payload = extract_payload(CHATTY)
    assert payload == {"order_id": "ord_4471", "status": "in_transit", "eta_days": 2}, payload


def check_a_clean_response_still_parses() -> None:
    """parse: відповідь без прози розбирається тим самим кодом"""
    assert extract_payload(CLEAN)["order_id"] == "ord_4471"


def check_no_payload_is_named_not_guessed() -> None:
    """ВІДМОВА · parse: відсутність даних — окремий стан, не порожній результат"""
    try:
        extract_payload(PROSE_ONLY)
    except NoPayload as error:
        assert "не відповідає" in str(error) or "система замовлень" in str(error), (
            "повідомлення має нести текст сервера — інакше діагностувати нічим"
        )
    else:
        raise AssertionError(
            "проза без даних розібралась — «сервер нічого не повернув» злилось із "
            "«сервер повернув порожнє»"
        )


def check_an_empty_result_is_not_a_missing_one() -> None:
    """ВІДМОВА · parse: порожній перелік — це результат, а не відсутність даних"""
    payload = extract_payload(EMPTY_LIST)
    assert payload == [], payload


def check_prose_that_merely_looks_like_data_is_not_taken() -> None:
    """ВІДМОВА · parse: приклад у прозі не приймається за дані"""
    tricky = """Формат відповіді такий: {"order_id": "...", "status": "..."} — але
зараз даних немає, бо замовлення не знайдено.
"""
    try:
        extract_payload(tricky)
    except NoPayload:
        pass
    else:
        raise AssertionError(
            "приклад із пояснення взято за дані — так парсер одного дня поверне "
            "фрагмент документації замість відповіді"
        )


def check_failure_description_names_the_phase() -> None:
    """parse: опис відмови називає фазу, а не лише текст винятку"""
    described = describe_failure(NoPayload("сервер нічого не повернув"), phase="parse")
    assert described["phase"] == "parse", described
    assert "нічого не повернув" in described["reason"]
    assert set(described) == {"phase", "reason"}, described


# --- T3, T4 · сервер і клієнт у справжньому процесі ------------------------------


def mcp_available() -> bool:
    """Чи встановлений пакет. Викликається перед усім, що піднімає процес."""
    try:
        import mcp  # noqa: F401
    except ImportError:
        return False
    return True


def _require_mcp() -> None:
    if not mcp_available():
        raise NotVerified('MCP не встановлено — pip install -e ".[s04]"')


def check_list_tools_returns_every_tool_with_a_usable_schema() -> None:
    """integration · list_tools дає всі інструменти зі схемами, придатними для моделі"""
    _require_mcp()
    tools = {t.name: t for t in list_tools()}
    assert set(tools) == {"get_order_status", "initiate_return", "search_knowledge_base"}, sorted(
        tools
    )
    for tool in tools.values():
        assert len(tool.description) > 30, f"{tool.name}: опис надто короткий для вибору"
        schema = tool.schema
        assert schema["type"] == "object", schema
        assert schema.get("properties"), f"{tool.name}: схема без параметрів"
        assert isinstance(schema.get("required"), list), f"{tool.name}: немає required"


def check_no_field_is_lost_crossing_the_process_boundary() -> None:
    """ВІДМОВА · межа процесу не спрощує контракт: параметри доїжджають усі"""
    _require_mcp()
    tools = {t.name: t for t in list_tools()}
    expected = {
        "get_order_status": {"order_id"},
        "initiate_return": {"order_id", "reason"},
        "search_knowledge_base": {"query", "access"},
    }
    for name, params in expected.items():
        got = set(tools[name].schema["properties"])
        assert got == params, (
            f"{name}: через межу процесу доїхали параметри {sorted(got)}, "
            f"а оголошені {sorted(params)}"
        )


def check_calling_a_tool_returns_the_same_shape_as_the_local_function() -> None:
    """integration · виклик через протокол дає те саме значення, що й локальна функція"""
    _require_mcp()
    result = call_tool("get_order_status", {"order_id": "ord_4471"})
    assert result.ok, result.failure
    assert result.payload["order_id"] == "ord_4471"
    local = REGISTRY["get_order_status"].func("ord_4471")
    assert result.payload["answer"] == local, "через межу значення змінилось"


def check_the_search_response_carries_prose_around_the_data() -> None:
    """integration · сервер говорить навколо даних — і саме тому парсер потрібен"""
    _require_mcp()
    result = call_tool(
        "search_knowledge_base", {"query": "скільки днів на повернення", "access": PUBLIC}
    )
    assert result.ok, result.failure
    assert result.payload["hits"], "нічого не знайшлося — фікстура зламалась"
    assert "Знайшов" in result.raw, "сира відповідь без прози — розбирати нічого"
    assert result.raw.strip().startswith("Знайшов"), (
        "проза має бути ДО даних: саме на цьому ламається json.loads на всій відповіді"
    )


def check_access_level_travels_in_the_payload() -> None:
    """ВІДМОВА · рівень доступу їде в payload і обмежує видачу на тому боці"""
    _require_mcp()
    bait = {"query": "яка сума автоматичного повернення"}
    shopper = call_tool("search_knowledge_base", {**bait, "access": PUBLIC})
    operator = call_tool("search_knowledge_base", {**bait, "access": INTERNAL})

    assert shopper.ok and operator.ok
    shopper_sources = [h["source"] for h in shopper.payload["hits"]]
    operator_sources = [h["source"] for h in operator.payload["hits"]]
    assert not any("internal" in s for s in shopper_sources), shopper_sources
    assert any("internal-refund-thresholds" in s for s in operator_sources), operator_sources


def check_a_server_that_fails_to_start_is_named() -> None:
    """ВІДМОВА · сервер не піднявся — названа фаза, а не зависання"""
    _require_mcp()
    result = call_tool("get_order_status", {"order_id": "ord_4471"}, broken=True)
    assert not result.ok, "виклик до мертвого сервера вдався — цього не може бути"
    assert result.failure["phase"] == "startup", result.failure
    assert result.failure["reason"], "причина порожня — діагностувати нічим"


def check_a_server_that_never_answers_times_out() -> None:
    """ВІДМОВА · сервер замовк — тайм-аут за скінченний час, фаза інша ніж startup"""
    _require_mcp()
    started = time.perf_counter()
    result = call_tool(
        "get_order_status", {"order_id": "ord_4471"}, module="stages.s04_mcp.mute", timeout=3.0
    )
    took = time.perf_counter() - started

    assert not result.ok, "мовчазний сервер відповів"
    assert took < 25, f"чекали {took:.1f} с — тайм-аут не спрацював"
    assert result.failure["phase"] in {"call", "startup"}, result.failure


def check_every_call_leaves_a_trace_record() -> None:
    """ВІДМОВА · виклик без сліду не існує як стан (AC-08b)"""
    _require_mcp()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("check", path=path, stage="s04") as tracer:
            call_tool("get_order_status", {"order_id": "ord_4471"}, tracer=tracer)
            call_tool("get_order_status", {"order_id": "x"}, broken=True, tracer=tracer)
        steps = [s for s in iter_steps(path) if s["kind"] == "mcp_call"]

    assert len(steps) == 2, f"кроків {len(steps)}, а викликів було два"
    assert {s["ok"] for s in steps} == {True, False}
    failed = next(s for s in steps if not s["ok"])
    assert failed["phase"] == "startup", failed
    assert all(s["tool"] == "get_order_status" and s["server"] for s in steps)


def check_server_fits_the_line_budget() -> None:
    """server: оголошення інструментів вміщається в один екран (NFR-2: ≤60 рядків)"""
    assert _executable_lines("server.py") <= 60, _executable_lines("server.py")


def check_client_fits_the_line_budget() -> None:
    """client: клієнт вміщається в один екран (NFR-1: ≤80 рядків)"""
    assert _executable_lines("client.py") <= 80, _executable_lines("client.py")


def _executable_lines(name: str) -> int:
    """Виконувані рядки: без імпортів і докстрінгів, але З викликами-інструкціями."""
    source = (Path(__file__).parent / name).read_text(encoding="utf-8")

    def is_docstring(node) -> bool:
        return isinstance(node, ast.Expr) and isinstance(getattr(node.value, "value", None), str)

    return len(
        {
            n.lineno
            for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.stmt)
            and not isinstance(n, (ast.Import, ast.ImportFrom))
            and not is_docstring(n)
        }
    )


CHECKS = [
    check_list_tools_returns_every_tool_with_a_usable_schema,
    check_no_field_is_lost_crossing_the_process_boundary,
    check_calling_a_tool_returns_the_same_shape_as_the_local_function,
    check_the_search_response_carries_prose_around_the_data,
    check_access_level_travels_in_the_payload,
    check_a_server_that_fails_to_start_is_named,
    check_a_server_that_never_answers_times_out,
    check_every_call_leaves_a_trace_record,
    check_server_fits_the_line_budget,
    check_client_fits_the_line_budget,
    check_payload_survives_prose_around_it,
    check_a_clean_response_still_parses,
    check_no_payload_is_named_not_guessed,
    check_an_empty_result_is_not_a_missing_one,
    check_prose_that_merely_looks_like_data_is_not_taken,
    check_failure_description_names_the_phase,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 4 · MCP")


if __name__ == "__main__":
    raise SystemExit(main())
