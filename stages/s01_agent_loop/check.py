"""Перевірки етапу 1. Офлайн, без API-ключа, детерміновано.

Запуск: ``python -m stages.s01_agent_loop.check``

Перевірки з префіксом ``ВІДМОВА ·`` перевіряють режими відмови — те, що станеться, коли піде
не так. Саме заради них існує підробний клієнт: на справжній моделі «ліміт кроків спрацював»
перевірити неможливо, бо вона недетермінована.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
from pathlib import Path

from shared.check_runner import run_checks
from shared.config import Settings
from shared.fake_llm import FakeLLM, text, tool_call
from shared.llm import banner, get_client, is_fake
from shared.trace import group_by_trace, trace_run
from stages.s01_agent_loop.loop import run_agent
from stages.s01_agent_loop.run import SCENARIO_TITLES
from stages.s01_agent_loop.run import main as demo_main
from stages.s01_agent_loop.tools import REGISTRY, Tool, tool_schemas
from stages.s01_agent_loop.validate import validate_arguments

# --- T1 · реєстр інструментів -------------------------------------------------


def check_registry_has_three_tools() -> None:
    """tools: у реєстрі рівно три інструменти з очікуваними іменами"""
    assert set(REGISTRY) == {"get_weather", "get_order_status", "initiate_return"}, sorted(REGISTRY)
    for name, tool in REGISTRY.items():
        assert tool.name == name, f"{name}: ім'я в записі не збігається з ключем"
        assert callable(tool.func), f"{name}: не має виконуваної функції"
        assert tool.description.strip(), f"{name}: порожній опис — модель не зможе обрати"


def check_exactly_one_tool_is_irreversible() -> None:
    """tools: незворотним позначено рівно один інструмент — оформлення повернення"""
    irreversible = {name for name, tool in REGISTRY.items() if tool.irreversible}
    assert irreversible == {"initiate_return"}, irreversible


def check_schemas_are_model_ready() -> None:
    """tools: схеми придатні до передачі в tools= без жодних перетворень"""
    schemas = tool_schemas()
    assert len(schemas) == 3
    for schema in schemas:
        assert schema["type"] == "function"
        fn = schema["function"]
        assert fn["name"] in REGISTRY
        assert fn["description"].strip()
        params = fn["parameters"]
        assert params["type"] == "object"
        assert params["properties"], f"{fn['name']}: немає жодного параметра"
        assert isinstance(params["required"], list)
        for field in params["required"]:
            assert field in params["properties"], f"{fn['name']}: {field} не описаний"
    # схема має бути серіалізовною — інакше SDK впаде вже на відправці
    json.dumps(schemas)


def check_tools_return_text_from_fixtures() -> None:
    """tools: інструменти читають фікстури й не ходять у мережу"""
    # Свідомо НЕ перевіряємо входження назви міста у відповідь: українська її відмінює
    # («Київ» -> «у Києві»), і така перевірка падала б на робочому коді. Перевіряємо вміст.
    weather = REGISTRY["get_weather"].func(city="Київ")
    assert isinstance(weather, str) and "+28" in weather, weather

    status = REGISTRY["get_order_status"].func(order_id="ord_4471")
    assert isinstance(status, str) and "ord_4471" in status, status

    unknown = REGISTRY["get_order_status"].func(order_id="ord_нема")
    assert "не знайдено" in unknown.lower(), unknown

    # незворотний інструмент теж лишається чистою функцією над фікстурами
    refused = REGISTRY["initiate_return"].func(order_id="ord_4473", reason="передумав")
    assert "не підлягає" in refused, refused


# --- T5 · демо ----------------------------------------------------------------


def check_demo_runs_offline_and_shows_four_scenarios() -> None:
    """demo: чотири сценарії підряд, офлайн, без ключа"""
    buffer = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        with contextlib.redirect_stdout(buffer):
            exit_code = demo_main(trace_path=Path(tmp) / "demo.jsonl")
        wrote_trace = (Path(tmp) / "demo.jsonl").exists()
    out = buffer.getvalue()
    assert wrote_trace, "демо не записало трейс"

    assert exit_code == 0, exit_code
    assert out.splitlines()[0].startswith("[FakeLLM]"), out.splitlines()[0]

    for marker in SCENARIO_TITLES:
        assert marker in out, f"немає сценарію «{marker}» у виводі"

    # кожен сценарій має показати роботу інструмента або причину, чому її не було
    assert "get_order_status" in out and "initiate_return" in out, out
    assert "ліміт" in out.lower(), "зупинку лімітом не видно"
    assert "підтвердж" in out.lower(), "гейт підтвердження не видно"


def check_client_factory_picks_the_configured_provider() -> None:
    """llm: з налаштованим провайдером фабрика дає справжній клієнт і називає його"""
    configured = Settings.load(
        source={
            "LLM_BASE_URL": "https://api.groq.com/openai/v1",
            "LLM_API_KEY": "gsk_test",
            "LLM_MODEL": "llama-3.3-70b-versatile",
        }
    )
    client = get_client(demo_script=[text("не має знадобитись")], settings=configured)
    assert not is_fake(client), "справжній провайдер налаштований, а повернулася підробка"
    assert str(client.base_url).startswith("https://api.groq.com"), client.base_url

    line = banner(client, settings=configured)
    assert "api.groq.com" in line and "llama-3.3-70b-versatile" in line, line
    # Друга половина AC-05 — що звернення справді відбувається — перевіряється вручну
    # за чеклістом в уроці: мережа й ключ зруйнували б офлайн і детермінізм.


# --- T4 · гейт підтвердження незворотної дії ----------------------------------


def _spy_return_tool() -> tuple[dict, list]:
    """Незворотний інструмент, що записує факт свого виклику."""
    calls: list[dict] = []
    original = REGISTRY["initiate_return"]

    def spy(**kwargs):
        calls.append(kwargs)
        return "повернення створено"

    tool = Tool(
        name=original.name,
        description=original.description,
        parameters=original.parameters,
        func=spy,
        irreversible=True,
    )
    return {"initiate_return": tool}, calls


def check_irreversible_tool_is_blocked_without_confirmation() -> None:
    """ВІДМОВА · gate: незворотна дія не виконується без підтвердження"""
    tools, calls = _spy_return_tool()
    client = FakeLLM(
        script=[tool_call("initiate_return", {"order_id": "ord_4472", "reason": "малий"})]
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("check", path=path) as tracer:
            result = run_agent("поверни", client=client, tracer=tracer, tools=tools)
        kinds = [s["kind"] for s in next(iter(group_by_trace(path).values()))]

    assert calls == [], f"незворотну функцію виконано без підтвердження: {calls}"
    assert result.blocked_tool == "initiate_return", result
    assert "tool_blocked" in kinds, kinds
    assert "tool_call" not in kinds, kinds
    # прогін має пояснити, ЩО саме сталося б, інакше підтверджувати наосліп
    assert "ord_4472" in result.answer and "підтвердж" in result.answer.lower(), result.answer


def check_confirmed_run_executes_the_irreversible_tool() -> None:
    """gate: з підтвердженням та сама дія виконується — гейт не глухий"""
    tools, calls = _spy_return_tool()
    client = FakeLLM(
        script=[
            tool_call("initiate_return", {"order_id": "ord_4472", "reason": "малий"}),
            text("Повернення оформлено."),
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("check", path=path) as tracer:
            result = run_agent("поверни", client=client, tracer=tracer, tools=tools, confirmed=True)
        kinds = [s["kind"] for s in next(iter(group_by_trace(path).values()))]

    assert calls == [{"order_id": "ord_4472", "reason": "малий"}], calls
    assert result.blocked_tool is None
    assert "tool_call" in kinds and "tool_blocked" not in kinds, kinds
    assert result.answer == "Повернення оформлено."


def check_gate_leaves_reversible_tools_alone() -> None:
    """gate: зворотні інструменти гейт не зачіпає навіть без підтвердження"""
    result, steps, _ = _run(
        [
            tool_call("get_order_status", {"order_id": "ord_4471"}),
            text("У дорозі."),
        ]
    )
    kinds = [s["kind"] for s in steps]
    assert result.blocked_tool is None
    assert "tool_call" in kinds and "tool_blocked" not in kinds, kinds


# --- T2 · валідація аргументів ------------------------------------------------

WEATHER_SCHEMA = REGISTRY["get_weather"].parameters
RETURN_SCHEMA = REGISTRY["initiate_return"].parameters


def check_valid_arguments_pass() -> None:
    """validate: коректні аргументи проходять без змін"""
    ok, result = validate_arguments(WEATHER_SCHEMA, {"city": "Львів"})
    assert ok, result
    assert result == {"city": "Львів"}, result

    ok, result = validate_arguments(RETURN_SCHEMA, {"order_id": "ord_4472", "reason": "малий"})
    assert ok, result


def check_missing_required_field_is_rejected() -> None:
    """ВІДМОВА · validate: відсутнє обов'язкове поле не проходить"""
    ok, reason = validate_arguments(RETURN_SCHEMA, {"order_id": "ord_4472"})
    assert not ok
    assert "reason" in reason, reason
    assert "обов" in reason.lower(), reason


def check_unknown_field_is_rejected() -> None:
    """ВІДМОВА · validate: зайве поле не проходить мовчки"""
    ok, reason = validate_arguments(WEATHER_SCHEMA, {"city": "Львів", "units": "metric"})
    assert not ok
    assert "units" in reason, reason


def check_wrong_type_is_never_coerced() -> None:
    """ВІДМОВА · validate: тип не приводиться — рядок замість числа це відмова"""
    schema = {
        "type": "object",
        "properties": {"days": {"type": "integer"}},
        "required": ["days"],
        "additionalProperties": False,
    }
    ok, reason = validate_arguments(schema, {"days": "3"})
    assert not ok, "рядок '3' не має тихо стати числом 3"
    assert "days" in reason and "integer" in reason, reason

    # булеве значення в Python є підтипом int — але для схеми це різні типи
    ok, reason = validate_arguments(schema, {"days": True})
    assert not ok, "True не має вважатися цілим числом"


def check_rejection_reason_is_human_readable() -> None:
    """validate: пояснення відмови — речення, а не дамп структури"""
    _, reason = validate_arguments(RETURN_SCHEMA, {})
    assert len(reason) > 20, reason
    assert reason.endswith("."), f"не схоже на речення: {reason}"
    # Апостроф як індикатор дампу не годиться: «обов'язкових» — звичайне українське слово.
    # Перевіряємо те, що справді має значення — дужки структури й імена відсутніх полів.
    assert not set(reason) & set("{}[]"), f"схоже на дамп структури: {reason}"
    assert "order_id" in reason and "reason" in reason, f"не названо, чого бракує: {reason}"


# --- T3 · цикл ReAct ----------------------------------------------------------


def _run(script, *, max_steps=8, confirmed=False, repeat_last=False):
    """Прогнати цикл на підробленій моделі, у тимчасовому трейсі."""
    client = FakeLLM(script=list(script), repeat_last=repeat_last)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("check", path=path, stage="s01") as tracer:
            result = run_agent(
                "перевірка",
                client=client,
                tracer=tracer,
                max_steps=max_steps,
                confirmed=confirmed,
            )
        steps = next(iter(group_by_trace(path).values()))
    return result, steps, client


def check_loop_completes_a_tool_call() -> None:
    """loop: модель обирає інструмент, отримує результат і дає відповідь"""
    result, steps, client = _run(
        [
            tool_call("get_order_status", {"order_id": "ord_4471"}),
            text("Ваше замовлення в дорозі, очікується за 2 дні."),
        ]
    )
    assert result.answer and "дорозі" in result.answer, result
    assert result.steps == 2, result.steps
    assert not result.stopped_by_limit

    kinds = [s["kind"] for s in steps]
    assert kinds.count("llm_call") == 2, kinds
    assert kinds.count("tool_call") == 1, kinds
    assert kinds[0] == "run_start" and kinds[-1] == "run_end", kinds

    # результат інструмента мусив повернутися моделі — інакше вона відповідала б наосліп
    sent = client.calls[-1]["messages"]
    assert any(m.get("role") == "tool" for m in sent), sent


def check_loop_sends_tool_schemas() -> None:
    """loop: модель отримує схеми інструментів, інакше обирати їй нема з чого"""
    _, _, client = _run([text("готово")])
    first = client.calls[0]
    names = {t["function"]["name"] for t in first["tools"]}
    assert names == set(REGISTRY), names


def check_step_limit_stops_a_runaway_loop() -> None:
    """ВІДМОВА · loop: нескінченний цикл зупиняється лімітом, а не сам собою"""
    client = FakeLLM.always_calling("get_weather", {"city": "Київ"})
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("check", path=path) as tracer:
            result = run_agent("перевірка", client=client, tracer=tracer, max_steps=3)
    assert result.stopped_by_limit, "ліміт не спрацював"
    assert result.steps == 3, result.steps
    assert result.answer is None, f"вигадав відповідь: {result.answer}"
    assert client.call_count == 3, client.call_count


def check_invalid_arguments_never_reach_the_tool() -> None:
    """ВІДМОВА · loop: криві аргументи не доходять до функції"""
    called: list[str] = []
    spy = Tool(
        name="get_weather",
        description=REGISTRY["get_weather"].description,
        parameters=REGISTRY["get_weather"].parameters,
        func=lambda **kw: called.append("викликано") or "не мало статися",
    )
    client = FakeLLM(
        script=[
            tool_call("get_weather", {"town": "Київ"}),
            text("зрозумів, виправляюсь"),
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.jsonl"
        with trace_run("check", path=path) as tracer:
            result = run_agent(
                "перевірка", client=client, tracer=tracer, tools={"get_weather": spy}
            )
        steps = next(iter(group_by_trace(path).values()))

    assert called == [], "інструмент виконався попри криві аргументи"
    assert result.answer, "цикл мав продовжитись, а не впасти"
    assert any(s["kind"] == "tool_rejected" for s in steps), [s["kind"] for s in steps]

    # пояснення мусило піти моделі як результат кроку
    tool_messages = [m for m in client.calls[-1]["messages"] if m.get("role") == "tool"]
    assert tool_messages and "town" in tool_messages[-1]["content"], tool_messages


# --- T6 · e2e: сама упряж перевірок -------------------------------------------


def check_rejection_is_returned_to_the_model() -> None:
    """ВІДМОВА · loop: відмова валідації повертається моделі, а не гасить прогін"""
    client = FakeLLM(
        script=[
            tool_call("get_weather", {"city": 42}),
            text("зрозумів, це має бути рядок"),
        ]
    )
    with tempfile.TemporaryDirectory() as tmp:
        with trace_run("check", path=Path(tmp) / "t.jsonl") as tracer:
            result = run_agent("погода", client=client, tracer=tracer)

    assert result.answer, "цикл зупинився замість продовжитись"
    assert result.steps == 2, f"модель не отримала другого шансу: {result.steps}"

    tool_reply = [m for m in client.calls[-1]["messages"] if m.get("role") == "tool"]
    assert tool_reply, "відмова не дійшла до моделі як результат кроку"
    assert "city" in tool_reply[-1]["content"] and "string" in tool_reply[-1]["content"], tool_reply


def check_stage_covers_at_least_three_failure_modes() -> None:
    """checks: щонайменше три перевірки етапу — на режими відмови, з описами"""
    docs = [(c.__doc__ or "").strip() for c in CHECKS]
    assert all(docs), "є перевірка без docstring — у виводі буде голе ім'я функції"
    assert len(set(docs)) == len(docs), "є перевірки з однаковим описом"

    failure = [d for d in docs if d.startswith("ВІДМОВА ·")]
    assert len(failure) >= 3, f"режимів відмови лише {len(failure)}: {failure}"

    covered = " ".join(failure).lower()
    for topic in ("ліміт", "аргумент", "підтвердження"):
        assert topic in covered, f"немає перевірки на «{topic}»: {failure}"


def check_broken_code_makes_the_check_run_fail_loudly() -> None:
    """ВІДМОВА · checks: зламана перевірка не може пройти тихо"""

    def deliberately_broken() -> None:
        """навмисно зламана"""
        expected, actual = 2, 1
        assert expected == actual, "гейт пропустив незворотну дію"

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = run_checks([deliberately_broken], title="мутація")
    out = buffer.getvalue()

    assert code == 1, "зламана перевірка дала нульовий код виходу"
    assert "FAIL" in out and "навмисно зламана" in out, out
    assert "deliberately_broken" in out, "не названо, яка саме перевірка впала"
    assert "AssertionError" in out and "check.py" in out, "не показано місце в коді"
    assert "гейт пропустив незворотну дію" in out, "не показано причину"


CHECKS = [
    check_registry_has_three_tools,
    check_exactly_one_tool_is_irreversible,
    check_schemas_are_model_ready,
    check_tools_return_text_from_fixtures,
    check_loop_completes_a_tool_call,
    check_loop_sends_tool_schemas,
    check_step_limit_stops_a_runaway_loop,
    check_invalid_arguments_never_reach_the_tool,
    check_demo_runs_offline_and_shows_four_scenarios,
    check_client_factory_picks_the_configured_provider,
    check_irreversible_tool_is_blocked_without_confirmation,
    check_confirmed_run_executes_the_irreversible_tool,
    check_gate_leaves_reversible_tools_alone,
    check_rejection_is_returned_to_the_model,
    check_stage_covers_at_least_three_failure_modes,
    check_broken_code_makes_the_check_run_fail_loudly,
    check_valid_arguments_pass,
    check_missing_required_field_is_rejected,
    check_unknown_field_is_rejected,
    check_wrong_type_is_never_coerced,
    check_rejection_reason_is_human_readable,
]

if __name__ == "__main__":
    raise SystemExit(run_checks(CHECKS, title="Етап 1 — цикл агента"))
