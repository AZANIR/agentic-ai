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
from shared.counters import InMemory
from shared.fake_llm import FakeLLM, text
from shared.trace import trace_run
from stages.s06_platform.guards import OK
from stages.s08_eval.trajectory import extract
from stages.s10_capstone import arch, assemble, latency, scenarios, seams
from stages.s10_capstone import service as service_module
from stages.s10_capstone.run import main as demo_main
from stages.s10_capstone.run import measured
from stages.s10_capstone.service import (
    AGENT,
    COST_PER_REQUEST,
    ROUTED,
    SEARCH,
    Capstone,
    Reply,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії (NFR-2).
BUDGET_SECONDS = 30

NEWLINE = chr(10)
LINE_BUDGET = 110
WORD_BUDGET = 2500

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
    """сценарії: звіряється гілка, інструменти І фінальний стан, не лише текст (AC-05)"""
    with _running() as (_service, tmp, _traces):
        outcomes = scenarios.play_all(tmp, _tracer_of(_service), base=_base())

    assert len(outcomes) == len(scenarios.SCENARIOS), len(outcomes)
    assert any(item.breaks for item in scenarios.SCENARIOS), (
        "жоден сценарій не ламає частини — а саме це ADR-0006 обіцяє окремим рядком"
    )
    assert any(item.tools for item in scenarios.SCENARIOS), (
        "жоден сценарій не кличе інструмента — тоді диспетчер етапу 1 не виконується "
        "взагалі й лише ВИГЛЯДАЄ зібраним"
    )
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
    """FAILURE · відмова частини не є падінням системи (AC-05b)"""

    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "s10.jsonl"
        with trace_run("check", path=traces, stage="s10", case="falls") as tracer:
            # Той самий клієнт, що в сценарії «частина відмовляє»: дві копії відмови
            # означали б, що перевірка й сценарій ламають РІЗНЕ й лише схоже.
            service = scenarios.build(Path(tmp), tracer, client=scenarios.Falls(), base=_base())
            reply = service.ask(scenarios.KEY, "Порахуй 2 плюс 2.", now=scenarios.NOW)
        kinds = [step["kind"] for step in _steps(traces)]

    assert not reply.ok, "частина відмовила, а сервіс сказав, що все гаразд"
    assert "ConnectionError" in reply.detail, reply.detail
    assert "failed" in kinds, kinds
    assert reply.text, "відмову не названо — читач не дізнається, ЩО саме зламалось"


def check_a_request_without_credentials_is_refused_by_the_imported_guard() -> None:
    """FAILURE · воротар етапу 6 відмовляє, і це ТОЙ САМИЙ код (AC-07)"""
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
    """FAILURE · офлайн: правило девʼяти етапів не зламано десятим (AC-11)"""
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
    """FAILURE · складання: етап без жодного виконаного рядка названо (AC-02b)"""
    empty = assemble.Assembly(executed=dict.fromkeys(assemble.PARTS, 0), adapters=1)
    assert empty.silent == sorted(assemble.PARTS), empty.silent
    assert "s01" in empty.line(), empty.line()

    # Дзеркальна половина: коли всі працюють, перелік мовчазних порожній.
    got = _assembly()
    assert got.silent == [], got.silent

    # І свідомо не ввімкнені стоять ОКРЕМО: нуль для них — рішення, а не помилка.
    assert assemble.NOT_WIRED, (
        "перелік свідомо не ввімкнених порожній — тоді «нуль за рішенням» і «нуль за "
        "недоглядом» знову одне й те саме (ADR-0008)"
    )
    for name in assemble.NOT_WIRED:
        assert name not in assemble.PARTS, f"{name} і в частинах, і в не ввімкнених"
        assert assemble.NOT_WIRED[name].strip(), f"{name}: причину не названо"


def check_the_price_of_assembly_is_two_numbers_in_one_unit() -> None:
    """складання: ціна названа двома числами в одній одиниці (AC-03)"""
    got = _assembly()

    assert got.adapters > 0, "перехідників нуль — або їх немає, або їх не рахують"
    assert got.worked > 0, "виконаних рядків нуль — вимір не працює"
    assert str(got.adapters) in got.line() and str(got.worked) in got.line(), got.line()

    # Одиниця одна: ОБИДВА числа — рядки, що ВИКОНАЛИСЬ. Ціна, порахована статично, поруч
    # із виконаним лічила б «є в коді» проти «працює» — саме ту підміну, яку етап викриває.
    assert got.adapters < got.written, (
        f"виконаних рядків перехідників {got.adapters} з {got.written} написаних — "
        "рівність означає, що ціну беруть із коду, а не з прогону"
    )
    assert assemble.executable_lines("seams.py") > got.written, (
        "перехідники важать як увесь модуль швів — тоді в ціну потрапила проза про ціну"
    )

    # Рахуються САМЕ перехідники. Проба поведінкова, не переписана: прибери один із
    # реєстру — число мусить впасти. Порівняння з власною копією тієї ж логіки довело б
    # лише, що дві копії однакові (та сама тавтологія, що вже ловилась на етапах 8 і 9).
    kept = dict(seams.ADAPTERS)
    seams.ADAPTERS.pop("answer_of_agent")
    try:
        fewer = assemble.adapter_lines()
    finally:
        seams.ADAPTERS.clear()
        seams.ADAPTERS.update(kept)
    assert fewer < got.written, (
        "реєстр перехідників на ціну не впливає — у неї їде весь модуль швів, "
        "і «ціна складання» перестає бути ціною складання"
    )


def check_adapters_stay_under_a_fifth_of_what_executed() -> None:
    """FAILURE · межа жанру: перехідники ≤ 1/5 виконаного (AC-03b, NFR-7)"""
    got = _assembly()
    assert got.ratio <= 0.2, (
        f"перехідники {got.adapters} на {got.worked} виконаних ({got.ratio:.0%}) — "
        "капстоун уже не збирає, а переписує"
    )
    # Дзеркальна половина: межа справді розрізняє. Удвічі більше перехідників — за межею.
    too_much = assemble.Assembly(executed=got.executed, adapters=got.worked // 3)
    assert too_much.ratio > 0.2, too_much.ratio


def check_the_warmup_runs_before_the_measured_pass() -> None:
    """FAILURE · прогрів: імпорт не входить у ціну прогону (NFR-10)"""
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
        # Етап, названий у шві, мусить ІСНУВАТИ. `startswith('s')` пропускав і `s99`,
        # тобто перевіряв форму рядка замість того, про що шов говорить.
        for part in item.between:
            assert part == "s10" or arch.stage_folder(part) is not None, (
                f"шов {item.name!r} називає етап {part!r}, якого не існує"
            )


def _branching(node: ast.AST) -> list[ast.AST]:
    """Розгалуження всередині функції, окрім охорони порожнього значення.

    `ast.IfExp` тут разом із `ast.If` навмисно: `a if cond else b` — те саме рішення, лише
    в один рядок, і перша редакція його не збирала взагалі.
    """
    return [
        inner
        for inner in ast.walk(node)
        if isinstance(inner, (ast.If, ast.IfExp, ast.Match)) and not _is_empty_guard(inner)
    ]


def check_an_adapter_that_decides_is_refused() -> None:
    """FAILURE · перехідник, що вирішує, є частиною (AC-04b)"""
    tree = ast.parse((HERE / "seams.py").read_text(encoding="utf-8"))
    wanted = {function.__name__ for function in seams.ADAPTERS.values()}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name in wanted):
            continue
        assert not _branching(node), (
            f"перехідник {node.name!r} розгалужується — той, що вирішує, є частиною, "
            "і їй місце в етапі з уроком і перевірками"
        )

    # Дзеркальна половина: перевірка мусить ЛОВИТИ обидві форми рішення. Без неї виняток
    # для охорони тихо звільняв усе, чий тест — просто ім'я, і перехідник, що переадресовує
    # операторові, проходив як «переклад форми».
    for source, why in (
        ("def a(x):\n    if x.needs_human:\n        return 1\n    return 2", "рішення через if"),
        ("def a(x):\n    return 1 if x.confident else 2", "рішення через вираз"),
        (
            "def a(x):\n    if x.steps > 2:\n        return 1\n    return 2",
            "рішення через порівняння",
        ),
    ):
        found = ast.parse(source).body[0]
        assert _branching(found), f"{why} не спіймано — виняток для охорони надто широкий"

    # І навпаки: охорона порожнього значення рішенням не є й лишається дозволеною.
    kept = ast.parse("def a(x):\n    if not x.hits:\n        return None\n    return x.hits").body[
        0
    ]
    assert not _branching(kept), "охорону порожнього значення названо рішенням"


def _is_empty_guard(node: Any) -> bool:
    """Охорона порожнього значення — не рішення: вона перекладає «нічого» у «нічого».

    Вузько навмисно: тільки `if not <ім'я>:` з єдиним `return` у тілі. Ширший виняток —
    «будь-який тест, що є іменем» — звільняв і `if result.needs_human: …`, тобто рівно те
    рішення, заради заборони якого перевірка існує.
    """
    if not isinstance(node, ast.If):
        return False
    negated = isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not)
    over_name = negated and isinstance(node.test.operand, (ast.Name, ast.Attribute))
    return bool(over_name) and len(node.body) == 1 and isinstance(node.body[0], ast.Return)


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
    """FAILURE · обґрунтування: биле посилання названо (AC-06b)"""
    good = arch.read()
    assert not arch.dangling(good), arch.dangling(good)

    first = arch.justifications(good)[0].what
    wrapped = arch.wrap_items(good)[0].what
    row, wrap_row = f"| {first} | s06 |", f"| {wrapped} | s06 |"

    # Кожна вада мусить бути спіймана ОКРЕМО. Три перші — про джерело; три наступні — про
    # рядок, який розбирач не зрозумів. Пропущений рядок не відрізняється від відсутнього:
    # биле посилання всередині нього зникало разом із ним, і `dangling()` мовчав.
    for spoiled_row, expect in (
        (f"| {first} | s99 |", "етапу s99 не існує"),
        (f"| {first} | s01 · ADR-9999 |", "ADR-9999"),
        (f"| {first} | невідомо |", "джерела не названо"),
        (f"| {first} | s99 | нотатка |", "не розібрано"),
        (f"|{first}|s99|", "не розібрано"),
        (f"| {first} " + chr(92) + "| хвіст | s99 |", "не розібрано"),
    ):
        spoiled = good.replace(row, spoiled_row)
        assert spoiled != good, f"рядок {first!r} не знайдено — проба не підмінила нічого"
        broken = arch.dangling(spoiled)
        assert broken, f"{spoiled_row!r} не спіймано"
        assert any(expect in line for line in broken), (spoiled_row, broken)

    # Таблиця обвісу теж називає етапи, і спершу вона до звірки не входила.
    spoiled = good.replace(wrap_row, f"| {wrapped} | s99 |")
    assert spoiled != good, f"рядок обвісу {wrapped!r} не знайдено"
    assert any("s99" in line for line in arch.dangling(spoiled)), (
        "биле посилання в таблиці обвісу проходить мовчки — а вада там та сама"
    )

    # І заголовок третього рівня не має ковтати розділ: інакше рішень стає нуль, а
    # `dangling()` — порожній, тобто вада виглядає як бездоганний документ.
    drafted = good.replace(
        arch.DECISIONS, f"### {first} (чернетка)" + NEWLINE * 2 + arch.DECISIONS, 1
    )
    assert len(arch.justifications(drafted)) == len(arch.justifications(good)), (
        "заголовок третього рівня ковтнув розділ рішень"
    )


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
    """крос-контекст: оцінювач етапу 8 дає ТРИ рівні на кількох траєкторіях (AC-09)"""
    from stages.s08_eval.cases import Case  # noqa: PLC0415
    from stages.s08_eval.judge import get_judge  # noqa: PLC0415
    from stages.s08_eval.levels import COMPONENT, E2E, PATH, evaluate  # noqa: PLC0415
    from stages.s08_eval.trajectory import RUN_KEYS, by_ref  # noqa: PLC0415

    with _running() as (service, _tmp, traces):
        for item in scenarios.SCENARIOS:
            service.ask(item.key, item.question, now=scenarios.NOW)
        # Групування ЗА ЗАПИТОМ, а не за прогоном: `case` один на весь файл, тож
        # `len(walked) == len(by_run)` було б тотожністю 1 == 1 і не стверджувало нічого.
        walked = extract(traces, key=by_ref)
        by_run = extract(traces, key=lambda step: step.get("case"))

    assert len(walked) > 1, (
        f"оцінювач витяг {len(walked)} траєкторію — на шести запитах це означає, що він "
        "групує за прогоном, а не за запитом, і «три рівні» рахувалися б на одному мішку"
    )
    assert len(walked) > len(by_run), (len(walked), len(by_run))
    assert all(trajectory.steps for trajectory in walked), "порожня траєкторія"

    # І він ВИНОСИТЬ вердикти, а не лише читає рядки. Три рівні, порядок сталий.
    judge = get_judge()
    for scenario, trajectory in zip(scenarios.SCENARIOS, walked, strict=False):
        case = Case(
            name=scenario.name,
            task=scenario.question,
            expected_tools=scenario.tools,
            budget=12,
            answer="",
            expected_answer="",
            acts=(),
        )
        verdicts = evaluate(case, trajectory, judge)
        assert [item.level for item in verdicts] == [E2E, PATH, COMPONENT], verdicts
        assert all(item.state for item in verdicts), (scenario.name, verdicts)

    assert "case" in RUN_KEYS, "ключ прогону капстоуна не входить у перелік оцінювача"


def check_latency_numbers_are_printed_with_their_conditions() -> None:
    """затримка: p50 і p95 ДРУКУЮТЬСЯ разом з умовами (AC-08)"""
    import io  # noqa: PLC0415
    from contextlib import redirect_stdout  # noqa: PLC0415

    with _running() as (service, _tmp, _traces):
        took = latency.measure(service)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            latency.report(took)
    printed = buffer.getvalue()

    assert took.runs == latency.RUNS, took.runs
    assert took.p95 >= took.p50, took

    # Числа НАДРУКОВАНІ, і надруковані ті самі, що заміряні. Без цього «є p50 і p95»
    # доводилось би тим, що список відсортований, — тобто нічим.
    assert f"p50 {took.p50:.1f}" in printed, printed
    assert f"p95 {took.p95:.1f}" in printed, printed

    # Умови стоять ПЕРЕД числами — інакше число не є виміром (урок етапу 7).
    for condition in latency.CONDITIONS:
        assert condition in printed, f"умову {condition!r} не надруковано"
    assert printed.index(latency.CONDITIONS[0]) < printed.index("p50"), (
        "число надруковано раніше за свої умови"
    )

    # І урок повторює ті самі умови: читач, який не запускав демо, мусить їх бачити.
    lesson = (HERE / "README.md").read_text(encoding="utf-8")
    for condition in ("підроблен", "локальн", "запит"):
        assert condition in lesson.lower(), f"урок не називає умову {condition!r}"


def check_one_request_is_counted_once_and_in_one_bucket() -> None:
    """FAILURE · метрики: відмова частини не додає ще й успіху (AC-01c)"""
    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "s10.jsonl"
        with trace_run("check", path=traces, stage="s10", case="metrics") as tracer:
            service = scenarios.build(Path(tmp), tracer, client=scenarios.Falls(), base=_base())
            reply = service.ask(scenarios.KEY, "Яка зараз погода в Києві?", now=scenarios.NOW)
            counted = dict(service.metrics.requests)

    assert not reply.ok and reply.kind == "dependency_down", (reply.ok, reply.kind)
    assert sum(counted.values()) == 1, (
        f"один запит порахований {sum(counted.values())} раз(и): {counted} — оператор "
        "бачить більше запитів, ніж було, і той самий запит як успіх І як відмову"
    )
    assert counted.get("dependency_down") == 1, counted

    # Друга половина, і без неї перша неповна: успішний запит теж рахується РІВНО раз.
    # Інакше «рахувати один раз» можна задовольнити, не рахуючи взагалі.
    with _running() as (service, _tmp, _traces):
        good = service.ask(scenarios.KEY, "Скільки днів на повернення?", now=scenarios.NOW)
        healthy = dict(service.metrics.requests)
    assert good.ok, (good.kind, good.text)
    assert healthy == {OK: 1}, f"успішний запит дав метрики {healthy} — очікувався рівно один успіх"
    # І відповідь називає тих, хто ВЖЕ відпрацював: інакше «нічого не сталося» і
    # «зламалось на середині» виглядають однаково.
    assert "s06" in reply.parts and "s02" in reply.parts, reply.parts


@contextmanager
def _asking(budget: float):
    """Сервіс із заданою денною межею. Дві витрати замість ста — щоб перевірка була швидка."""
    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "s10.jsonl"
        with trace_run("check", path=traces, stage="s10", case="budget") as tracer:
            yield Capstone(
                settings=scenarios.demo_settings(budget_usd_per_day=budget),
                counters=InMemory(),
                client=FakeLLM(script=[text("51")], repeat_last=True),
                tracer=tracer,
                memory_path=Path(tmp) / "facts.jsonl",
                base=_base(),
            )


def _kinds(service: Any, times: int) -> list[str]:
    return [
        service.ask(scenarios.KEY, "Скільки днів на повернення?", now=scenarios.NOW).kind
        for _ in range(times)
    ]


def check_the_found_text_travels_behind_the_stage_2_fence() -> None:
    """FAILURE · чужий текст іде в модель за огорожею блоку даних (AC-01d)"""
    from stages.s02_rag.answer import CLOSE_DATA, OPEN_DATA  # noqa: PLC0415

    with _running() as (service, _tmp, _traces):
        found = seams.from_search(
            service.base, "Скільки днів на повернення товару?", tracer=service.tracer
        )

    assert found.text, "пошук нічого не знайшов — огорожу нема на чому перевіряти"
    assert OPEN_DATA in found.prompt and CLOSE_DATA in found.prompt, (
        "знайдений текст їде в модель БЕЗ огорожі блоку даних — етап 2 цю щілину закрив, "
        "а капстоун відкрив її наново, у тому єдиному місці, де всі частини стоять поруч"
    )
    fenced = found.prompt.split(OPEN_DATA, 1)[1].split(CLOSE_DATA, 1)[0]
    assert found.text.split()[0] in fenced, "огорожа є, а знайдене — поза нею"

    # І сервіс веде в модель САМЕ той промпт, а не склеєний власноруч. Без цього огорожу
    # можна лишити в перехіднику й обійти її на рівень вище.
    source = (HERE / "service.py").read_text(encoding="utf-8")
    assert "asked = context.prompt or question" in source, (
        "сервіс складає промпт сам — тоді огорожа етапу 2 не діє там, де вона потрібна"
    )
    assert 'f"{context.text}' not in source, "сервіс склеює знайдений текст із питанням"


def check_the_budget_guard_has_a_witness() -> None:
    """FAILURE · бюджет: вичерпана межа зупиняє запити, і без списання це червоніє (AC-07c)"""
    allowed = 2
    with _asking(allowed * COST_PER_REQUEST) as service:
        kinds = _kinds(service, allowed + 1)
        spent = service.metrics.spent_usd

    assert kinds[:allowed] == [OK] * allowed, kinds
    assert kinds[allowed] == "budget_exhausted", (
        f"межу вичерпано, а сервіс відповів {kinds[allowed]!r} — запобіжник етапу 6 не працює"
    )
    assert abs(spent - allowed * COST_PER_REQUEST) < 1e-9, spent

    # Дзеркальна половина, і саме вона тут головна: списання, підмінене на нуль, робить
    # запобіжник вічно голодним. Без неї `charge` можна було прибрати зовсім — набір
    # лишався зеленим, і бюджетний воротар не спрацьовував уже НІКОЛИ.
    healthy = service_module.charge
    service_module.charge = lambda *_args, **_kwargs: 0.0
    try:
        with _asking(allowed * COST_PER_REQUEST) as service:
            kinds = _kinds(service, allowed + 1)
    finally:
        service_module.charge = healthy
    assert "budget_exhausted" not in kinds, (
        "запобіжник спрацював навіть без списання — тоді він реагує не на витрати"
    )


def check_the_lesson_numbers_come_from_the_run() -> None:
    """урок: числа в таблиці «Числа» збігаються з виміром (AC-02c)"""
    got = _assembly()
    lesson = (HERE / "README.md").read_text(encoding="utf-8")

    # Числа, вбиті в урок і не звірені ні з чим, старіють мовчки — рівно те, проти чого
    # написаний `arch.py`. Будь-який рядок, доданий в етапи 1–8, зсуває їх, і саме тут
    # це має почервоніти, а не через рік у читача.
    for label, value in (
        ("Виконано рядків етапів на прогін", got.worked),
        ("Рядків перехідників, що виконались", got.adapters),
        ("Рядків перехідників написано", got.written),
        ("Частин, що виконуються", len(assemble.PARTS)),
        ("Свідомо не ввімкнено", len(assemble.NOT_WIRED)),
        ("Швів названо", len(seams.SEAMS)),
        ("Сценаріїв", len(scenarios.SCENARIOS)),
        ("Перевірок", len(CHECKS)),
    ):
        row = f"| {label} | {value} |"
        assert row in lesson, f"урок не містить рядка {row!r} — число розійшлося з виміром"


def check_the_lesson_fits_the_word_budget() -> None:
    """бюджет: урок вкладається у стелю слів (NFR-3)"""
    for name in ("README.md", "README.en.md"):
        words = len((HERE / name).read_text(encoding="utf-8").split())
        assert words <= WORD_BUDGET, f"{name}: {words} > {WORD_BUDGET} слів"


def check_a_missing_load_tool_yields_not_evaluated_never_a_failure() -> None:
    """FAILURE · навантаження: без інструмента — третій стан (AC-08b)"""
    from importlib.util import find_spec  # noqa: PLC0415

    if find_spec("locust") is None:
        raise NotVerified(
            "навантажувального інструмента немає — постав `pip install locust`; "
            "числа затримки лишаються локальними"
        )
    raise NotVerified("locust встановлено, але прогін потребує піднятого сервісу")


def check_a_broken_adapter_reddens_the_check_about_that_seam() -> None:
    """FAILURE · зуби: зламаний перехідник червонить перевірку про свій шов (AC-12)"""
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


def check_the_http_layer_is_stage_6_and_not_a_second_one() -> None:
    """деплой: зібраний сервіс віддається застосунком етапу 6, без свого шару (AC-13)"""
    source = (HERE / "serve.py").read_text(encoding="utf-8")

    assert "from stages.s06_platform.api import create_app" in source, (
        "капстоун не бере застосунок етапу 6 — тоді це другий HTTP-шар, а не складання"
    )
    assert not code_mentions(source, {"fastapi.fastapi", "fastapi"}), (
        "капстоун сам будує FastAPI — переписаний шар проходив би повз перевірку "
        "«немає власних воротарів», бо воротарі й справді лишились чужими"
    )
    tree = ast.parse(source)
    routes = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.decorator_list
    ]
    assert not routes, f"власні маршрути в капстоуні: {[node.name for node in routes]}"


def check_the_assembled_service_answers_over_http_unchanged() -> None:
    """FAILURE · деплой: чужий застосунок відмовляє без ключа й відповідає з ним (AC-13b)"""
    # Спроба імпорту, а не `find_spec`: симуляція чистої установки блокує пакет
    # хуком, який КИДАЄ, і `find_spec` падає замість того, щоб повернути `None`.
    try:
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from stages.s06_platform.api import create_app  # noqa: PLC0415
        from stages.s06_platform.observe import Health  # noqa: PLC0415
    except ImportError as error:
        raise NotVerified(f"fastapi недоступний — це чиста установка: {error}") from error

    with _running() as (service, _tmp, _traces):
        client = TestClient(create_app(service, Health(provider="fake")))
        refused = client.post(
            "/ask",
            json={"question": "Скільки днів на повернення товару?"},
            headers={"x-api-key": "not-a-key"},
        )
        answered = client.post(
            "/ask",
            json={"question": "Скільки днів на повернення товару?"},
            headers={"x-api-key": scenarios.KEY},
        )
        state = client.get("/healthz")

    assert refused.status_code == 401, (refused.status_code, refused.text[:200])
    assert refused.json()["kind"] == "unauthenticated", refused.json()
    assert answered.status_code == 200, (answered.status_code, answered.text[:200])
    assert answered.json()["ok"] and answered.json()["text"], answered.json()
    assert state.status_code in (200, 503), state.status_code

    # `Reply` навмисно НЕ зветься `Answer`, і саме тому цікаво, що чужому шару цього
    # досить: етапи 6 і 10 домовлені формою, а не іменем. Поле `retry_after` виявилось
    # останнім — на цій самій підстановці, а не в проєкті.
    assert hasattr(Reply, "retry_after") or "retry_after" in Reply.__dataclass_fields__, (
        "форма відповіді розійшлася з тим, чого чекає застосунок етапу 6"
    )


def check_the_live_deploy_stays_not_evaluated() -> None:
    """FAILURE · деплой: прогін проти справжнього HTTPS — третій стан (AC-13c)"""
    smoke = REPO_ROOT / "deploy" / "smoke.sh"
    assert smoke.exists(), "переліку для живого сервісу немає взагалі"
    assert "s10" in (REPO_ROOT / "deploy" / "RUNBOOK.md").read_text(encoding="utf-8"), (
        "RUNBOOK не знає про другий деплой — тоді його ніхто не відтворить"
    )
    raise NotVerified(
        "прогін проти справжнього HTTPS потребує піднятої машини; офлайн його не "
        "відтворити — і зелений колір тут був би за неперевірене"
    )


def check_the_modules_fit_the_line_budget() -> None:
    """бюджет: кожен модуль капстоуна вкладається у стелю рядків (NFR-1)"""
    for name in assemble.OWN:
        require_intact_source(name)
        lines = assemble.executable_lines(name)
        assert lines <= LINE_BUDGET, f"{name}: {lines} > {LINE_BUDGET} виконуваних рядків"


def check_the_demo_shows_every_scene_offline_within_its_budget() -> None:
    """e2e · демо: вісім сцен, без ключа й без мережі, у межах часу (NFR-2b)"""
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
    for number in range(1, 9):
        assert f"{NEWLINE}{number}. " in output, f"сцена {number} не надрукувалась"

    # Числа сцен збігаються з тим, що дає вимір тут, а не набрані руками.
    got = _assembly()
    assert f"виконано рядків етапів: {got.worked}" in output, got.worked
    assert f"рядків перехідників:    {got.adapters}" in output, got.adapters


def check_twenty_runs_give_the_same_branches_and_states() -> None:
    """FAILURE · детермінізм: двадцять прогонів дають ті самі гілки й стани (NFR-6)"""

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
    failures = [label for label in labels if label.startswith("FAILURE")]
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
    check_one_request_is_counted_once_and_in_one_bucket,
    check_the_found_text_travels_behind_the_stage_2_fence,
    check_the_budget_guard_has_a_witness,
    check_the_lesson_numbers_come_from_the_run,
    check_the_lesson_fits_the_word_budget,
    check_a_missing_load_tool_yields_not_evaluated_never_a_failure,
    check_a_broken_adapter_reddens_the_check_about_that_seam,
    check_the_http_layer_is_stage_6_and_not_a_second_one,
    check_the_assembled_service_answers_over_http_unchanged,
    check_the_live_deploy_stays_not_evaluated,
    check_the_modules_fit_the_line_budget,
    check_the_demo_shows_every_scene_offline_within_its_budget,
    check_twenty_runs_give_the_same_branches_and_states,
    check_the_failure_modes_are_at_least_a_third,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 10 · Capstone")


if __name__ == "__main__":
    raise SystemExit(main())
