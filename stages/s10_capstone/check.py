"""Перевірки етапу 10.

    python -m stages.s10_capstone.check

Працюють **без ключа й без мережі** — правило, яке трималось дев'ять етапів, і зламати його
найлегше саме на десятому.

**Головна перевірка тут не про код капстоуна, а про складання**: кожен етап, названий
частиною, мусить виконати ненульове число власних рядків. Етап, присутній лише в рядку
`import`, червонить набір із власною назвою.
"""

from __future__ import annotations

import ast
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from shared.check_runner import NotVerified, code_mentions, require_intact_source, run_checks
from shared.trace import trace_run
from stages.s08_eval.trajectory import extract
from stages.s10_capstone import arch, assemble, scenarios, seams
from stages.s10_capstone.run import main as demo_main
from stages.s10_capstone.run import measured
from stages.s10_capstone.service import AGENT, ROUTED, SEARCH, Capstone, Reply

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії (NFR-2).
BUDGET_SECONDS = 30

NEWLINE = chr(10)
LINE_BUDGET = 110

# Індекс будується раз на прогін набору: він однаковий для всіх перевірок, а будувати його
# на кожній означало б міряти ембеддинги замість складання.
_BASE: Any = None


def _base() -> Any:
    global _BASE
    if _BASE is None:
        _BASE = seams.build_search()
    return _BASE


@contextmanager
def _running():
    """Сервіс, трасувальник і тимчасовий каталог. Усе подається ззовні, як на етапі 6."""
    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "s10.jsonl"
        with trace_run("check", path=traces, stage="s10", case="check") as tracer:
            yield scenarios.build(Path(tmp), tracer, base=_base()), Path(tmp), traces


def _executable_lines(name: str) -> int:
    tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
    return len(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.stmt)
            and not isinstance(node, (ast.Import, ast.ImportFrom))
            and not (
                isinstance(node, ast.Expr) and isinstance(getattr(node.value, "value", None), str)
            )
        }
    )


def _assembly() -> assemble.Assembly:
    """Той самий вимір, що робить демо — **той самий виклик**, не схожий на нього.

    Своє замикання дало б своє число, і перевірка «числа демо збігаються з виміром»
    порівнювала б два виміри між собою замість числа з його джерелом.
    """
    with _running() as (service, tmp, traces):
        # Ті самі умови, що в демо: трейс уже містить прогін сценаріїв. Оцінювачу,
        # якому нічого судити, нічого й розбирати — гілка розбору не виконується, і
        # вимір виходить на рядок меншим. Умови — частина виміру, а не тло (етап 7).
        scenarios.play_all(tmp, _tracer_of(service), base=_base())
        return measured(service, traces)


# --- сервіс і сценарії ---------------------------------------------------------------------


def check_one_command_answers_and_names_the_parts_that_took_part() -> None:
    """сервіс: відповідь називає, які частини брали участь (AC-01)"""
    with _running() as (service, _tmp, _traces):
        reply = service.ask(scenarios.KEY, "Скільки днів на повернення товару?", now=scenarios.NOW)

    assert isinstance(reply, Reply), type(reply)
    assert reply.ok, (reply.kind, reply.text)
    assert reply.branch in (SEARCH, ROUTED, AGENT), reply.branch
    assert reply.parts, "відповідь не називає жодної частини"
    assert "s06" in reply.parts, "воротар не позначений як учасник — а він працює завжди"
    assert reply.trace_id, "відповідь без ідентифікатора трейсу"


def check_five_scenarios_check_the_branch_and_the_final_state() -> None:
    """сценарії: звіряється гілка І фінальний стан, не лише текст (AC-05)"""
    with _running() as (_service, tmp, _traces):
        outcomes = scenarios.play_all(tmp, _tracer_of(_service), base=_base())

    assert len(outcomes) == 5, len(outcomes)
    for outcome in outcomes:
        assert not outcome.mismatch, (outcome.scenario.name, outcome.mismatch)

    # Дзеркальна половина: сценарій, у якого зіпсували очікуваний стан, мусить упасти.
    import dataclasses  # noqa: PLC0415

    with _running() as (service, _tmp, _traces):
        first = scenarios.SCENARIOS[0]
        lied = dataclasses.replace(first, remembered=not first.remembered)
        broken = scenarios.play(service, lied)
    assert broken.mismatch, "підмінений фінальний стан не спіймано — звіряється лише текст"


def check_a_failing_part_leaves_the_service_alive_and_named() -> None:
    """ВІДМОВА · відмова частини не є падінням системи (AC-05b)"""

    class Falls:
        """Клієнт, що відмовляє на кожному виклику. Роль: недоступна залежність."""

        class chat:  # noqa: N801
            class completions:  # noqa: N801
                @staticmethod
                def create(**_kwargs: Any) -> Any:
                    raise ConnectionError("провайдер недоступний")

    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "s10.jsonl"
        with trace_run("check", path=traces, stage="s10", case="falls") as tracer:
            service = scenarios.build(Path(tmp), tracer, client=Falls(), base=_base())
            reply = service.ask(scenarios.KEY, "Порахуй 2 плюс 2.", now=scenarios.NOW)
        kinds = [step["kind"] for step in _steps(traces)]

    assert not reply.ok, "частина відмовила, а сервіс сказав, що все гаразд"
    assert "ConnectionError" in reply.detail, reply.detail
    assert "failed" in kinds, kinds
    assert reply.text, "відмову не названо — читач не дізнається, ЩО саме зламалось"


def check_a_request_without_credentials_is_refused_by_the_imported_guard() -> None:
    """ВІДМОВА · воротар етапу 6 відмовляє, і це ТОЙ САМИЙ код (AC-07)"""
    with _running() as (service, _tmp, traces):
        reply = service.ask("not-a-key", "Скільки днів на повернення?", now=scenarios.NOW)
        steps = _steps(traces)

    assert not reply.ok and reply.kind == "unauthenticated", (reply.ok, reply.kind)
    assert any(step["kind"] == "guard" for step in steps), "відмова не лишила сліду в трейсі"

    # Той самий код, не переписаний: капстоун не має власних воротарів.
    source = (HERE / "service.py").read_text(encoding="utf-8")
    assert "from stages.s06_platform.guards import" in source, "воротарі не імпортовані"
    assert not code_mentions(source, {"compare_digest", "hmac"}), (
        "капстоун порівнює ключі сам — це переписаний воротар, а не імпортований"
    )


def check_all_five_scenarios_run_with_no_key_and_no_network() -> None:
    """ВІДМОВА · офлайн: правило девʼяти етапів не зламано десятим (AC-11)"""
    from shared.config import settings  # noqa: PLC0415

    if settings.has_real_llm:
        raise NotVerified("ключ налаштовано — гілку «без ключа» не відтворити")

    for name in assemble.OWN:
        source = (HERE / name).read_text(encoding="utf-8")
        assert not code_mentions(source, {"httpx", "requests", "urlopen", "socket"}), (
            f"{name} тягне мережу — етап перестає проходитись офлайн"
        )

    with _running() as (_service, tmp, _traces):
        outcomes = scenarios.play_all(tmp, _tracer_of(_service), base=_base())
    assert all(not outcome.mismatch for outcome in outcomes), [o.mismatch for o in outcomes]


# --- складання ------------------------------------------------------------------------------


def check_every_named_part_executes_a_non_zero_number_of_its_own_lines() -> None:
    """складання: кожна названа частина виконує СВОЇ рядки (AC-02)"""
    got = _assembly()

    assert set(got.executed) == set(assemble.PARTS), sorted(got.executed)
    for name in assemble.PARTS:
        assert got.executed[name] > 0, (
            f"етап {name} названо частиною складання, а він виконав нуль рядків — "
            "це рядок `import`, а не складання"
        )
    assert len(assemble.PARTS) >= 6, f"частин {len(assemble.PARTS)} — менше шести (NFR-9)"


def check_a_part_with_zero_executed_lines_reddens_and_is_named() -> None:
    """ВІДМОВА · складання: етап без жодного виконаного рядка названо (AC-02b)"""
    empty = assemble.Assembly(executed=dict.fromkeys(assemble.PARTS, 0), adapters=1)
    assert empty.silent == sorted(assemble.PARTS), empty.silent
    assert "s01" in empty.line(), empty.line()

    # Дзеркальна половина: коли всі працюють, перелік мовчазних порожній.
    got = _assembly()
    assert got.silent == [], got.silent

    # І свідомо не ввімкнені стоять ОКРЕМО: нуль для них — рішення, а не помилка.
    for name in assemble.NOT_WIRED:
        assert name not in assemble.PARTS, f"{name} і в частинах, і в не ввімкнених"
        assert assemble.NOT_WIRED[name].strip(), f"{name}: причину не названо"


def check_the_price_of_assembly_is_two_numbers_in_one_unit() -> None:
    """складання: ціна названа двома числами в одній одиниці (AC-03)"""
    got = _assembly()

    assert got.adapters > 0, "перехідників нуль — або їх немає, або їх не рахують"
    assert got.worked > 0, "виконаних рядків нуль — вимір не працює"
    assert str(got.adapters) in got.line() and str(got.worked) in got.line(), got.line()

    # Одиниця одна: обидва числа — виконувані рядки, порахованi тим самим способом.
    assert assemble.adapter_lines() == got.adapters, assemble.adapter_lines()
    assert assemble.executable_lines("seams.py") > got.adapters, (
        "перехідники важать як увесь модуль швів — тоді в ціну потрапила проза про ціну"
    )

    # Рахуються САМЕ перехідники. Проба поведінкова, не переписана: прибери один із
    # реєстру — число мусить впасти. Порівняння з власною копією тієї ж логіки довело б
    # лише, що дві копії однакові (та сама тавтологія, що вже ловилась на етапах 8 і 9).
    kept = dict(seams.ADAPTERS)
    seams.ADAPTERS.pop("memory_takes_a_path")
    try:
        fewer = assemble.adapter_lines()
    finally:
        seams.ADAPTERS.clear()
        seams.ADAPTERS.update(kept)
    assert fewer < got.adapters, (
        "реєстр перехідників на ціну не впливає — у неї їде весь модуль швів, "
        "і «ціна складання» перестає бути ціною складання"
    )


def check_adapters_stay_under_a_fifth_of_what_executed() -> None:
    """ВІДМОВА · межа жанру: перехідники ≤ 1/5 виконаного (AC-03b, NFR-7)"""
    got = _assembly()
    assert got.ratio <= 0.2, (
        f"перехідники {got.adapters} на {got.worked} виконаних ({got.ratio:.0%}) — "
        "капстоун уже не збирає, а переписує"
    )
    # Дзеркальна половина: межа справді розрізняє. Удвічі більше перехідників — за межею.
    too_much = assemble.Assembly(executed=got.executed, adapters=got.worked // 3)
    assert too_much.ratio > 0.2, too_much.ratio


def check_the_warmup_runs_before_the_measured_pass() -> None:
    """ВІДМОВА · прогрів: імпорт не входить у ціну прогону (NFR-8)"""
    calls: list[int] = []
    assemble.measure(lambda: calls.append(1))
    assert len(calls) == 2, (
        f"роботу виконано {len(calls)} раз(и) — без прогріву в ціну ОДНОГО запиту "
        "поїдуть рядки імпорту, які трапляються раз на процес"
    )


def check_every_adapter_names_the_seam_it_closes() -> None:
    """перехідники: кожен називає свій шов (AC-04)"""
    named = {item.name for item in seams.SEAMS}
    for name in seams.ADAPTERS:
        assert name in named, f"перехідник {name!r} не має шва — це не перехідник"

    for item in seams.SEAMS:
        assert len(set(item.between)) == 2, (item.name, item.between)
        assert len(item.why) > 40, f"{item.name}: причину названо надто коротко"
        assert all(part.startswith("s") for part in item.between), item.between


def check_an_adapter_that_decides_is_refused() -> None:
    """ВІДМОВА · перехідник, що вирішує, є частиною (AC-04b)"""
    tree = ast.parse((HERE / "seams.py").read_text(encoding="utf-8"))
    wanted = {function.__name__ for function in seams.ADAPTERS.values()}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in wanted):
            continue
        branching = [
            inner
            for inner in ast.walk(node)
            if isinstance(inner, (ast.If, ast.Match)) and not _is_guard(inner)
        ]
        assert not branching, (
            f"перехідник {node.name!r} розгалужується — той, що вирішує, є частиною, "
            "і їй місце в етапі з уроком і перевірками"
        )


def _is_guard(node: Any) -> bool:
    """Охорона порожнього значення — не рішення: вона перекладає «нічого» у «нічого»."""
    return isinstance(node, ast.If) and isinstance(
        node.test, (ast.UnaryOp, ast.Name, ast.Attribute)
    )


# --- обґрунтування --------------------------------------------------------------------------


def check_every_decision_cites_a_stage_that_exists() -> None:
    """обґрунтування: кожне рішення має джерело, і джерело існує (AC-06)"""
    text = arch.read()
    items = arch.justifications(text)

    assert len(items) >= 15, f"рішень {len(items)} — надто мало для зібраного сервісу"
    assert not arch.dangling(text), arch.dangling(text)
    for item in items:
        assert item.stage, f"{item.what!r}: джерела не названо"
        assert arch.stage_folder(item.stage) is not None, item.stage


def check_a_dangling_citation_reddens_and_is_named() -> None:
    """ВІДМОВА · обґрунтування: биле посилання названо (AC-06b)"""
    good = arch.read()
    assert not arch.dangling(good), arch.dangling(good)

    # Три різні вади, і кожна мусить бути спіймана окремо.
    for source, expect in (
        ("s99", "етапу s99 не існує"),
        ("s01 · ADR-9999", "ADR-9999"),
        ("невідомо", "джерела не названо"),
    ):
        first = arch.justifications(good)[0].what
        spoiled = good.replace(f"| {first} | s06 |", f"| {first} | {source} |")
        assert spoiled != good, f"рядок {first!r} не знайдено — проба не підмінила нічого"
        broken = arch.dangling(spoiled)
        assert broken, f"{source!r} не спіймано"
        assert any(expect in line for line in broken), (source, broken)


def check_every_wrap_item_names_its_source_stage() -> None:
    """обвіс: кожен пункт називає етап-джерело (AC-07b)"""
    text = arch.read()
    body = text.split("## Обвіс і його походження", 1)[1].split(NEWLINE + "## ", 1)[0]
    for wanted in (
        "Автентифікація",
        "Ліміт частоти",
        "Бюджетний",
        "Метрики",
        "Трасування",
        "копія",
    ):
        assert wanted in body, f"в обвісі немає пункту {wanted!r}"
    rows = [line for line in body.split(NEWLINE) if line.strip().startswith("|")]
    for line in rows[2:]:
        source = line.strip().strip("|").split("|")[-1].strip()
        assert arch.SOURCE.match(source), f"пункт обвісу без джерела: {line.strip()!r}"


def check_the_assembly_report_is_not_empty() -> None:
    """звіт: розділ «що складання виявило» не порожній (AC-10)"""
    text = arch.read()
    found = arch.revealed(text)

    assert len(found) >= 4, (
        f"у звіті {len(found)} пунктів — девʼять незалежно спроєктованих модулів не "
        "стикуються ідеально, і звіт, який каже інакше, звітує не про складання"
    )
    stages = {f"s0{number}" for number in range(1, 10)}
    assert any(any(name in item for name in stages) for item in found), (
        "жоден пункт звіту не називає етапу — це враження, а не знахідка"
    )
    assert arch.own_decisions(text), "розділ власних рішень порожній"
    for what, why in arch.own_decisions(text):
        assert len(why) > 30, f"{what!r}: причини, чому джерела немає, не названо"


# --- крос-контекст і межі -------------------------------------------------------------------


def check_the_stage_8_evaluator_judges_the_capstone_unchanged() -> None:
    """крос-контекст: оцінювач етапу 8 читає трейси капстоуна (AC-09)"""
    with _running() as (service, _tmp, traces):
        for item in scenarios.SCENARIOS:
            service.ask(scenarios.KEY, item.question, now=scenarios.NOW)
        walked = extract(traces, key=lambda step: step.get("case"))
        by_id = extract(traces)

    assert walked, "оцінювач не витяг жодної траєкторії з трейсу капстоуна"
    assert all(trajectory.steps for trajectory in walked), "порожня траєкторія"
    assert len(by_id) == len(walked), (len(by_id), len(walked))

    # Ключ прогону стоїть із першого рядка — і оцінювач його знає (правило етапу 9).
    from stages.s08_eval.trajectory import RUN_KEYS  # noqa: PLC0415

    assert "case" in RUN_KEYS, "ключ прогону капстоуна не входить у перелік оцінювача"


def check_latency_numbers_are_printed_with_their_conditions() -> None:
    """затримка: число друкується разом з умовами (AC-08)"""
    import time  # noqa: PLC0415

    with _running() as (service, _tmp, _traces):
        marks = []
        for _ in range(20):
            started = time.perf_counter()
            service.ask(scenarios.KEY, "Скільки днів на повернення?", now=scenarios.NOW)
            marks.append((time.perf_counter() - started) * 1000)

    marks.sort()
    p50, p95 = marks[len(marks) // 2], marks[-max(1, len(marks) // 20)]
    assert p95 >= p50, (p50, p95)

    # Умови мусять стояти в уроці поруч із числами — інакше число не є виміром.
    lesson = (HERE / "README.md").read_text(encoding="utf-8")
    for condition in ("підроблен", "локальн", "запит"):
        assert condition in lesson.lower(), f"урок не називає умову {condition!r}"


def check_a_missing_load_tool_yields_not_evaluated_never_a_failure() -> None:
    """ВІДМОВА · навантаження: без інструмента — третій стан (AC-08b)"""
    from importlib.util import find_spec  # noqa: PLC0415

    if find_spec("locust") is None:
        raise NotVerified(
            "навантажувального інструмента немає — постав `pip install locust`; "
            "числа затримки лишаються локальними"
        )
    raise NotVerified("locust встановлено, але прогін потребує піднятого сервісу")


def check_a_broken_adapter_reddens_the_check_about_that_seam() -> None:
    """ВІДМОВА · зуби: зламаний перехідник червонить перевірку про свій шов (AC-12)"""
    healthy = seams.from_agent

    def silent(task: str, *, client: Any, tracer: Any) -> Any:
        """Зламано навмисно: перехідник більше не називає частини."""
        worked = healthy(task, client=client, tracer=tracer)
        return seams.Worked(text=worked.text, part="", detail=worked.detail)

    seams.from_agent = silent
    try:
        try:
            check_five_scenarios_check_the_branch_and_the_final_state()
        except AssertionError as caught:
            assert "частини" in str(caught), f"червоніє не про той шов: {caught}"
        else:
            raise AssertionError(
                "перехідник зламано, а сценарії лишились зеленими — вони звіряють текст, "
                "а не склад частин"
            )
        # Дзеркальна половина: перевірка ПРО ІНШИЙ шов від цієї поломки не червоніє.
        check_every_adapter_names_the_seam_it_closes()
    finally:
        seams.from_agent = healthy

    check_five_scenarios_check_the_branch_and_the_final_state()


# --- бюджети ---------------------------------------------------------------------------------


def check_the_modules_fit_the_line_budget() -> None:
    """бюджет: кожен модуль капстоуна вкладається у стелю рядків (NFR-1)"""
    for name in assemble.OWN:
        require_intact_source(name)
        lines = _executable_lines(name)
        assert lines <= LINE_BUDGET, f"{name}: {lines} > {LINE_BUDGET} виконуваних рядків"


def check_the_demo_shows_every_scene_offline_within_its_budget() -> None:
    """e2e · демо: сім сцен, без ключа й без мережі, у межах часу (NFR-2b)"""
    import io  # noqa: PLC0415
    import time  # noqa: PLC0415
    from contextlib import redirect_stdout  # noqa: PLC0415

    buffer = io.StringIO()
    started = time.perf_counter()
    with redirect_stdout(buffer):
        code = demo_main(base=_base())
    took = time.perf_counter() - started
    output = buffer.getvalue()

    assert code == 0, code
    assert took <= 15, f"демо йшло {took:.1f} с — стеля 15 с (NFR-2b)"
    for number in range(1, 8):
        assert f"{NEWLINE}{number}. " in output, f"сцена {number} не надрукувалась"

    # Числа сцен збігаються з тим, що дає вимір тут, а не набрані руками.
    got = _assembly()
    assert f"виконано рядків етапів: {got.worked}" in output, got.worked
    assert f"рядків перехідників:    {got.adapters}" in output, got.adapters


def check_twenty_runs_give_the_same_branches_and_states() -> None:
    """ВІДМОВА · детермінізм: двадцять прогонів дають ті самі гілки й стани (NFR-6)"""

    def fingerprint() -> tuple:
        with _running() as (_service, tmp, _traces):
            outcomes = scenarios.play_all(tmp, _tracer_of(_service), base=_base())
        return tuple((out.branch, out.parts, out.remembered, out.kind) for out in outcomes)

    first = fingerprint()
    for index in range(1, 20):
        assert fingerprint() == first, f"прогін {index} дав інші гілки або стани"


def check_the_failure_modes_are_at_least_a_third() -> None:
    """перевірки: режимів відмови не менше третини (NFR-4)"""
    labels = [(check.__doc__ or "").split(NEWLINE)[0] for check in CHECKS]
    failures = [label for label in labels if label.startswith("ВІДМОВА")]
    assert len(failures) * 3 >= len(CHECKS), (
        f"режимів відмови {len(failures)} із {len(CHECKS)} — менше третини"
    )


def _tracer_of(service: Capstone) -> Any:
    return service.tracer


def _steps(traces: Path) -> list[dict[str, Any]]:
    from shared.trace import iter_steps  # noqa: PLC0415

    return list(iter_steps(traces))


CHECKS = [
    check_one_command_answers_and_names_the_parts_that_took_part,
    check_five_scenarios_check_the_branch_and_the_final_state,
    check_a_failing_part_leaves_the_service_alive_and_named,
    check_a_request_without_credentials_is_refused_by_the_imported_guard,
    check_all_five_scenarios_run_with_no_key_and_no_network,
    check_every_named_part_executes_a_non_zero_number_of_its_own_lines,
    check_a_part_with_zero_executed_lines_reddens_and_is_named,
    check_the_price_of_assembly_is_two_numbers_in_one_unit,
    check_adapters_stay_under_a_fifth_of_what_executed,
    check_the_warmup_runs_before_the_measured_pass,
    check_every_adapter_names_the_seam_it_closes,
    check_an_adapter_that_decides_is_refused,
    check_every_decision_cites_a_stage_that_exists,
    check_a_dangling_citation_reddens_and_is_named,
    check_every_wrap_item_names_its_source_stage,
    check_the_assembly_report_is_not_empty,
    check_the_stage_8_evaluator_judges_the_capstone_unchanged,
    check_latency_numbers_are_printed_with_their_conditions,
    check_a_missing_load_tool_yields_not_evaluated_never_a_failure,
    check_a_broken_adapter_reddens_the_check_about_that_seam,
    check_the_modules_fit_the_line_budget,
    check_the_demo_shows_every_scene_offline_within_its_budget,
    check_twenty_runs_give_the_same_branches_and_states,
    check_the_failure_modes_are_at_least_a_third,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 10 · Capstone")


if __name__ == "__main__":
    raise SystemExit(main())
