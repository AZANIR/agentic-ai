"""Перевірки етапу 3.

    python -m stages.s03_router.check

Офлайн, без ключа. Правило те саме, що на етапах 1–2: серед перевірок обов'язково є ті, що
стверджують **режим відмови**, і їх не менше третини. Щасливий шлях сам по собі не доводить
нічого — він лише показує, що код запускається.
"""

from __future__ import annotations

import ast
import tempfile
from pathlib import Path

from shared.check_runner import run_checks
from shared.fake_llm import FakeLLM, text, tool_call
from shared.trace import iter_steps, trace_run
from stages.s02_rag.documents import INTERNAL, PUBLIC
from stages.s03_router import graph as graph_module
from stages.s03_router.graph import (
    FINISH_REASONS,
    NO_SPECIALIST,
    SUPERVISOR,
    route_prompt,
    run_graph,
)
from stages.s03_router.specialists import SPECIALISTS, Specialist, safely
from stages.s03_router.state import DECLARED, FROZEN, State, StateFieldError

INTERNAL_BAIT = "яка сума автоматичного повернення"

# --- T1 · схема стану ---------------------------------------------------------


def check_state_declares_everything_the_graph_knows() -> None:
    """state: схема оголошує повний перелік того, що граф знає про задачу"""
    state = State(query="скільки днів на повернення", access="public")

    assert state.query and state.access == "public"
    assert state.handoffs == 0 and state.revisions == 0
    assert state.path == [] and state.finish_reason is None
    for name in ("query", "access", "handoffs", "revisions", "path", "finish_reason"):
        assert name in DECLARED, f"поле {name} не оголошене у схемі"


def check_reading_an_undeclared_field_names_it() -> None:
    """ВІДМОВА · state: читання неоголошеного поля падає з назвою поля"""
    state = State(query="q", access="public")
    try:
        state.speciality  # noqa: B018 — саме читання і є предметом перевірки
    except StateFieldError as error:
        assert "speciality" in str(error), error
        assert "handoffs" in str(error), "помилка має називати те, що у схемі Є"
    else:
        raise AssertionError(
            "неоголошене поле прочиталось — схема стану лишилась підказкою, а не контрактом"
        )


def check_writing_an_undeclared_field_is_refused() -> None:
    """ВІДМОВА · state: запис неоголошеного поля відхиляється, а не створює його"""
    state = State(query="q", access="public")
    try:
        state.speciality = "orders"
    except StateFieldError as error:
        assert "speciality" in str(error), error
    else:
        raise AssertionError("вузол створив поле на льоту — наступний вузол про це не дізнається")


def check_no_node_may_raise_the_access_level() -> None:
    """ВІДМОВА · state: рівень доступу не можна перезаписати з вузла (ADR-0003)"""
    state = State(query="q", access="public")
    for name in sorted(FROZEN):
        try:
            setattr(state, name, "internal")
        except StateFieldError as error:
            assert name in str(error), error
        else:
            raise AssertionError(f"поле {name} перезаписалось — воно мало бути незмінним")
    assert state.access == "public"


def check_counters_move_and_the_path_records_every_node() -> None:
    """state: лічильники ростуть, шлях записує кожен вузол по порядку"""
    state = State(query="q", access="public")
    state.handoffs += 1
    state.path.append("supervisor")
    state.handoffs += 1
    state.path.append("knowledge")
    state.finish_reason = "answered"

    assert state.handoffs == 2
    assert state.path == ["supervisor", "knowledge"]
    assert state.finish_reason == "answered"


# --- T2 · спеціалісти ----------------------------------------------------------


def check_every_specialist_carries_a_competence_description() -> None:
    """specialists: кожен спеціаліст має назву й опис компетенції для маршруту"""
    assert set(SPECIALISTS) == {"orders", "knowledge", "math"}, sorted(SPECIALISTS)
    for name, specialist in SPECIALISTS.items():
        assert specialist.name == name
        assert len(specialist.competence) > 30, f"{name}: опис надто короткий, щоб обрати за ним"
        assert callable(specialist.handle)


def check_knowledge_specialist_reads_access_from_the_state() -> None:
    """ВІДМОВА · specialists: спеціаліст знань бере рівень доступу зі стану, не з аргументів"""
    state = State(query=INTERNAL_BAIT, access=PUBLIC)
    answer = SPECIALISTS["knowledge"].handle(state)

    assert answer.text, "спеціаліст нічого не повернув"
    assert answer.sources, "відповідь без джерела — етап 2 такого стану не має"
    assert not any("internal" in s for s in answer.sources), (
        f"внутрішній документ у джерелах покупця: {answer.sources}"
    )
    assert "1500" not in answer.text, "суму з внутрішнього документа видно покупцю"


def check_operator_gets_more_than_a_shopper_from_the_same_question() -> None:
    """ВІДМОВА · specialists: оператор ОТРИМУЄ те, що йому можна — дзеркальна перевірка"""
    shopper = SPECIALISTS["knowledge"].handle(State(query=INTERNAL_BAIT, access=PUBLIC))
    operator = SPECIALISTS["knowledge"].handle(State(query=INTERNAL_BAIT, access=INTERNAL))

    assert any("internal-refund-thresholds" in s for s in operator.sources), (
        f"оператор не бачить внутрішнього документа: {operator.sources} — "
        "рівень доступу не дійшов до пошуку"
    )
    assert "1500" in operator.text, "оператору не дійшов сам зміст, лише мітка"
    assert operator.sources != shopper.sources, "рівень доступу не змінив нічого"


def check_orders_specialist_runs_the_stage_one_loop() -> None:
    """specialists: спеціаліст замовлень працює циклом етапу 1, а не власним"""
    state = State(query="який статус замовлення ord_4471", access=PUBLIC)
    client = FakeLLM(
        script=[
            tool_call("get_order_status", {"order_id": "ord_4471"}),
            text("Замовлення ord_4471 у дорозі."),
        ]
    )
    answer = SPECIALISTS["orders"].handle(state, client=client)
    assert "ord_4471" in answer.text, answer.text
    assert answer.steps >= 2, "цикл не зробив жодного кроку з інструментом"


def check_specialist_failure_becomes_a_result_not_a_crash() -> None:
    """ВІДМОВА · specialists: виняток усередині спеціаліста стає результатом кроку"""

    def explode(state, **kwargs):
        raise RuntimeError("склад недоступний")

    broken = Specialist(name="broken", competence="ламається завжди" * 5, handle=explode)
    answer = safely(broken, State(query="q", access=PUBLIC))

    assert answer.error, "виняток загубився — граф не дізнається, що сталось"
    assert "склад недоступний" in answer.error
    assert "broken" in answer.error, "помилка має називати вузол"
    assert not answer.text, "зламаний спеціаліст не має видавати тексту"


# --- T3 · граф ------------------------------------------------------------------

SIX = [
    ("який статус замовлення ord_4471", "orders"),
    ("хочу оформити повернення ord_9001", "orders"),
    ("скільки днів на повернення товару", "knowledge"),
    ("з чого пошита вишита сорочка", "knowledge"),
    ("скільки буде 1200 + 340", "math"),
    ("порахуй 450 200 90", "math"),
]


def _scripted(*replies: str) -> FakeLLM:
    """Клієнт, який відповідає рівно цими рядками, по одному на виклик."""
    return FakeLLM(script=[text(r) for r in replies])


def _run(query: str, *replies: str, access: str = PUBLIC, revision_limit: int = 2):
    with tempfile.TemporaryDirectory() as tmp:
        with trace_run("check", path=Path(tmp) / "t.jsonl", stage="s03") as tracer:
            state = run_graph(
                query,
                access=access,
                client=_scripted(*replies),
                tracer=tracer,
                revision_limit=revision_limit,
            )
            steps = list(iter_steps(Path(tmp) / "t.jsonl"))
    return state, steps


def check_six_queries_reach_their_expected_specialists() -> None:
    """e2e · шість запитів доходять до шести очікуваних спеціалістів"""
    for query, expected in SIX:
        state, _ = _run(query, expected, "ok")
        assert state.path == [SUPERVISOR, expected], f"{query!r} -> {state.path}"
        assert state.finish_reason == "answered", state.finish_reason
        assert state.handoffs == 1, f"{query!r}: передач {state.handoffs}, а мало бути 1"
        assert state.answer, f"{query!r}: відповіді немає"


def check_route_prompt_shows_the_model_every_competence() -> None:
    """graph: модель бачить опис КОЖНОЇ компетенції, інакше вибір неможливий"""
    prompt = route_prompt(State(query="будь-що", access=PUBLIC))
    for specialist in SPECIALISTS.values():
        head = specialist.competence.split(",")[0][:40]
        assert head in prompt, f"опис {specialist.name} не дійшов до моделі"
        assert specialist.name in prompt
    assert "будь-що" in prompt, "запит не дійшов до моделі"
    assert NO_SPECIALIST in prompt, "модель має знати, як сказати «жоден»"


def check_a_route_the_model_invented_is_not_followed() -> None:
    """ВІДМОВА · graph: вигадана моделлю назва вузла не стає маршрутом"""
    state, _ = _run("яка погода в Києві", "weather")
    assert state.path == [SUPERVISOR], f"викликано спеціаліста: {state.path}"
    assert state.finish_reason == "no_specialist", state.finish_reason
    assert state.handoffs == 0
    assert "weather" not in (state.answer or ""), "вигадана назва потрапила у відповідь"
    for name in SPECIALISTS:
        assert name in (state.answer or ""), "відмова має називати доступні компетенції"


def check_revision_loop_stops_at_the_limit() -> None:
    """ВІДМОВА · graph: цикл ревізій зупиняється лімітом, а не крутиться далі"""
    state, steps = _run(
        "скільки днів на повернення товару",
        "knowledge",
        "мало",
        "мало",
        "мало",
        "мало",
        "мало",
        revision_limit=2,
    )
    assert state.finish_reason == "revision_limit", state.finish_reason
    assert state.revisions == 2, f"ревізій {state.revisions}, а ліміт 2"
    assert state.handoffs == 3, f"передач {state.handoffs}: перша плюс дві ревізії"
    assert state.answer is None or "незавершен" in (state.answer or "").lower(), (
        "часткова відповідь видається за готову"
    )
    assert any(s["kind"] == "revision" for s in steps), "ревізії немає у трейсі"


def check_a_broken_specialist_does_not_kill_the_graph() -> None:
    """ВІДМОВА · graph: виняток спеціаліста стає станом, а не падінням прогону"""

    def explode(state, **kwargs):
        raise RuntimeError("склад недоступний")

    original = SPECIALISTS["orders"]
    SPECIALISTS["orders"] = Specialist(original.name, original.competence, explode)
    try:
        state, steps = _run("який статус замовлення ord_4471", "orders")
    finally:
        SPECIALISTS["orders"] = original

    assert state.finish_reason == "specialist_failed", state.finish_reason
    assert state.error and "склад недоступний" in state.error
    assert "orders" in state.error, "помилка має називати вузол"
    assert any(s["kind"] == "specialist_failed" for s in steps), "збою немає у трейсі"


def check_every_run_ends_with_a_stated_reason() -> None:
    """graph: жоден прогін не завершується без названої причини (AC-02)"""
    cases = [
        ("скільки днів на повернення товару", ("knowledge", "ok")),
        ("яка погода в Києві", ("weather",)),
        ("скільки буде 2 + 2", ("math", "мало", "мало", "мало")),
    ]
    reasons = set()
    for query, replies in cases:
        state, _ = _run(query, *replies)
        assert state.done, f"{query!r} завершився без причини"
        assert state.finish_reason in FINISH_REASONS, state.finish_reason
        reasons.add(state.finish_reason)
    assert len(reasons) == 3, f"три різні сценарії дали причини: {reasons}"


def check_graph_fits_the_line_budget() -> None:
    """graph: маршрутизація вміщається в один екран (NFR-1: ≤80 рядків)"""
    source = Path(graph_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = {
        n.lineno
        for n in ast.walk(tree)
        if isinstance(n, ast.stmt) and not isinstance(n, (ast.Expr, ast.Import, ast.ImportFrom))
    }
    assert len(lines) <= 80, f"graph.py: {len(lines)} виконуваних рядків із 80 (SAD §11)"


CHECKS = [
    check_six_queries_reach_their_expected_specialists,
    check_route_prompt_shows_the_model_every_competence,
    check_a_route_the_model_invented_is_not_followed,
    check_revision_loop_stops_at_the_limit,
    check_a_broken_specialist_does_not_kill_the_graph,
    check_every_run_ends_with_a_stated_reason,
    check_graph_fits_the_line_budget,
    check_every_specialist_carries_a_competence_description,
    check_knowledge_specialist_reads_access_from_the_state,
    check_operator_gets_more_than_a_shopper_from_the_same_question,
    check_orders_specialist_runs_the_stage_one_loop,
    check_specialist_failure_becomes_a_result_not_a_crash,
    check_state_declares_everything_the_graph_knows,
    check_reading_an_undeclared_field_names_it,
    check_writing_an_undeclared_field_is_refused,
    check_no_node_may_raise_the_access_level,
    check_counters_move_and_the_path_records_every_node,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 3 · Router")


if __name__ == "__main__":
    raise SystemExit(main())
