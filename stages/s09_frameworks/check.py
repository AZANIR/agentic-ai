"""Перевірки етапу 9.

    python -m stages.s09_frameworks.check

Працюють **без ключа й без мережі**. Модель — підробка зі спільним сценарієм: інакше токени
були б неспівмірні ще до того, як фреймворк щось додав.

**Три стани, а не два.** Реалізація, чийого пакета немає, дає `НЕ ПЕРЕВІРЕНО` — але з
названою причиною, і причин тут дві різні: «не встановлено» лікується встановленням, «не
встановлюється на цьому Python» не лікується нічим, крім іншого інтерпретатора.
"""

from __future__ import annotations

import ast
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from shared.check_runner import NotVerified, code_mentions, require_intact_source, run_checks
from shared.fake_llm import FakeLLM
from shared.llm import get_model
from stages.s09_frameworks import (
    baseline,
    compare,
    contract,
    via_adk,
    via_crewai,
    via_langgraph,
)
from stages.s09_frameworks.counters import Tally, counted, executed_lines, tokens
from stages.s09_frameworks.run import IMPLEMENTATIONS, RULES, collect

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії (NFR-2).
BUDGET_SECONDS = 30

NEWLINE = chr(10)

# Модулі **реалізації**. `run.py` і `check.py` не рахуються (NFR-1).
IMPLEMENTATION = (
    "contract.py",
    "counters.py",
    "compare.py",
    "baseline.py",
    "via_langgraph.py",
    "via_crewai.py",
    "via_adk.py",
)
LINE_BUDGET = 110


def _client(script: list[dict[str, Any]] | None = None) -> Any:
    """Клієнт із лічильником. Той самий шлях, що в демо: інакше числа були б з іншого місця."""
    inner = FakeLLM(script=script or contract.script(), repeat_last=True)
    return counted(inner, contract.owned_texts())


@contextmanager
def _table():
    """Прогнати збір і віддати рядки разом із записаним файлом, поки він ще живий."""
    with tempfile.TemporaryDirectory() as tmp:
        rows = collect(Path(tmp) / "s09.jsonl")
        target = compare.save(rows, RULES, Path(tmp) / "COMPARISON.md")
        yield rows, target, target.read_text(encoding="utf-8")


def _counted_rows(rows: list[compare.Row]) -> list[compare.Row]:
    return [row for row in rows if row.counted]


# Модулі, конструювання клієнта з яких означає обхід спільної межі (ADR-0007).
TRANSPORTS = frozenset({"openai", "httpx", "requests", "litellm"})


def _client_constructions(source: str) -> list[str]:
    """Місця, де модуль будує власний транспорт. Порожньо — усе йде крізь спільну межу.

    Розбирається AST і шукається **виклик** виду `openai.OpenAI(...)` чи `httpx.Client()`,
    а не згадка слова: слово `openai` є і в рядку `"openai/gpt-4o"`, який лише називає
    провайдера для чужої обгортки й нікого не конструює.
    """
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        if isinstance(callee, ast.Attribute) and isinstance(callee.value, ast.Name):
            if callee.value.id in TRANSPORTS:
                found.append(f"рядок {node.lineno}: {callee.value.id}.{callee.attr}")
        elif isinstance(callee, ast.Name) and callee.id in TRANSPORTS:
            found.append(f"рядок {node.lineno}: {callee.id}")
    return found


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


# --- таблиця -----------------------------------------------------------------------------


def check_one_command_yields_a_row_per_implementation() -> None:
    """порівняння: одна команда дає рядок на кожну реалізацію (AC-01)"""
    with _table() as (rows, target, text):
        assert len(rows) == len(IMPLEMENTATIONS), (len(rows), len(IMPLEMENTATIONS))
        assert target.exists() and target.stat().st_size > 0, "таблицю не записано у файл"

        for column in compare.COLUMNS:
            assert f"| {column} |" in text, f"у таблиці немає колонки {column!r}"
        for row in rows:
            assert f"| {row.name} |" in text, f"{row.name} не доїхав до файлу"
            assert len(row.cells()) == len(compare.COLUMNS), row.cells()


def check_the_written_table_parses_back_to_the_same_numbers() -> None:
    """FAILURE · таблиця: розібраний файл дає ті самі числа, що й прогін (AC-01b)"""
    with _table() as (rows, _, text):
        parsed = compare.parse(text)
        assert set(parsed) == {row.name for row in rows}, (sorted(parsed), len(rows))
        for row in rows:
            assert parsed[row.name] == row.cells()[1:], (row.name, parsed[row.name])

        # Дзеркальна половина: рядок, що не доїхав до файлу, розбір мусить спіймати.
        lost = NEWLINE.join(
            line for line in text.split(NEWLINE) if not line.startswith(f"| {rows[0].name} |")
        )
        assert compare.parse(lost) != parsed, "розбір не помітив зниклого рядка — він рахує не файл"


def check_exactly_one_row_carries_no_framework() -> None:
    """порівняння: рівно один рядок без жодного фреймворка (AC-05, NFR-7)"""
    with _table() as (rows, _, _text):
        assert len(rows) >= 4, f"реалізацій {len(rows)} — менше чотирьох (NFR-7)"
        bare = [row for row in rows if row.module == "baseline.py"]
        assert len(bare) == 1, f"базових ліній {len(bare)}, а має бути рівно одна"
        assert bare[0].counted, "базова лінія не порахована — без неї таблиця не про те питання"
        assert bare[0].invisible == 0, (
            f"у базової лінії {bare[0].invisible} невидимих рядків — вона тягне фреймворк"
        )


# --- контракт ----------------------------------------------------------------------------


def check_all_implementations_honour_the_same_task_contract() -> None:
    """контракт: усі реалізації виконують ту саму задачу, і це доводиться прогоном (AC-02)"""
    with _table() as (rows, _, _text):
        # По ВСІХ рядках, а не по вцілілих. `_counted_rows` фільтрує саме за `not broken`,
        # тож `for row in ran: assert not row.broken` — тавтологія: він викидає з-під
        # ассерта рівно тих, про кого ассерт мав би скаржитись.
        violated = [(row.name, row.broken) for row in rows if row.broken]
        assert not violated, violated
        ran = _counted_rows(rows)
        assert ran, "жодної реалізації не прогнано — контракт нема на чому довести"
        if len(ran) < len(IMPLEMENTATIONS):
            raise NotVerified(
                f"виконанням доведено {len(ran)} із {len(IMPLEMENTATIONS)}: "
                + "; ".join(row.unverified for row in rows if row.unverified)
            )

    # Контракт — **код**, а не проза: він виконується на результаті, а не читається очима.
    import dataclasses  # noqa: PLC0415

    client = _client()
    result = dataclasses.replace(baseline.run(client), model_calls=client.tally.calls)
    assert contract.violations(result) == (), contract.violations(result)


def check_an_implementation_that_breaks_the_contract_gets_no_numbers() -> None:
    """FAILURE · контракт: порушник лишається в таблиці, але без чисел (AC-02b)"""
    good = contract.Result(
        name="ціла",
        asked=contract.QUESTION,
        answer=contract.ANSWER,
        tools_used=contract.TOOLS,
        stopped_by=contract.ANSWERED,
        model_calls=2,
        coordination="явна",
        why_source="код",
    )
    assert contract.violations(good) == (), contract.violations(good)

    import dataclasses  # noqa: PLC0415

    # Кожен елемент контракту ламається окремо — і кожен має бути названий.
    for field, value, expected in (
        ("asked", "інше питання", "вхід"),
        ("tools_used", ("search_notes", "search_notes"), "інструменти"),
        ("model_calls", 0, "модель"),
        ("stopped_by", contract.OUT_OF_BUDGET, "умова зупинки"),
        ("answer", "", "форма"),
        ("answer", "Повернення можливе.", "форма"),
    ):
        broken = contract.violations(dataclasses.replace(good, **{field: value}))
        assert broken, f"{field}={value!r} не спіймано — контракт не ловить цього елемента"
        assert any(name.startswith(expected) for name in broken), (field, broken)

    # Порушник лишається рядком таблиці, і замість чисел стоїть причина.
    row = compare.Row(
        name="порушник",
        module="baseline.py",
        broken=contract.violations(dataclasses.replace(good, stopped_by=contract.OUT_OF_BUDGET)),
    )
    cells = row.cells()
    assert not row.counted and "контракт порушено" in cells, cells
    assert "умова зупинки" in NEWLINE.join(cells), cells


# --- рядки -------------------------------------------------------------------------------


def check_my_lines_and_invisible_lines_are_two_separate_numbers() -> None:
    """рядки: моє й невидиме — два числа в одній одиниці (AC-03)"""
    with _table() as (rows, _, text):
        for row in _counted_rows(rows):
            assert row.mine > 0, f"{row.name}: нуль моїх рядків — модуль порожній?"
            assert f"| {row.mine} |" in text or str(row.mine) in text, row.name

        with_framework = [row for row in _counted_rows(rows) if row.module != "baseline.py"]
        if not with_framework:
            raise NotVerified("жодного фреймворка не встановлено — порівнювати нема з чим")
        for row in with_framework:
            assert row.invisible > 0, (
                f"{row.name}: нуль невидимих рядків — трасування не бачить пакета, "
                "і «менше коду» лишається аргументом без другої половини"
            )


def check_framework_lines_never_count_as_mine() -> None:
    """FAILURE · рядки: код фреймворка не рахується моїм (AC-03b)"""
    for name in IMPLEMENTATION:
        mine = compare.executable_lines(name)
        assert mine == _executable_lines(name), name
        assert mine < 200, f"{name}: {mine} рядків — схоже, лічильник зачепив чужий пакет"

    # Дзеркальна половина: трасування бачить пакет, а не мій модуль.
    if not via_langgraph.available():
        raise NotVerified("langgraph не встановлено — невидимі рядки нема де взяти")
    with executed_lines("langgraph") as seen:
        via_langgraph.run(_client())
    assert seen, "трасування не побачило жодного рядка пакета"
    mine_path = str(HERE)
    assert not any(name.startswith(mine_path) for name, _ in seen), (
        "мої рядки потрапили в невидимі — базова лінія отримала б безпідставну перевагу"
    )


# --- токени ------------------------------------------------------------------------------


def check_tokens_are_counted_at_the_provider_boundary_both_numbers() -> None:
    """токени: два числа, і рахуються на межі, а не в реалізації (AC-04)"""
    client = _client()
    baseline.run(client)
    tally = client.tally

    assert tally.calls == 2, f"викликів {tally.calls} — базова лінія робить рівно два"
    assert tally.asked > 0 and tally.sent > 0, tally
    assert tally.sent >= tally.asked, (tally.sent, tally.asked)

    # Лічильник стоїть НА МЕЖІ: реалізація його не бачить і не може підіграти.
    source = (HERE / "baseline.py").read_text(encoding="utf-8")
    assert not code_mentions(source, {"tally", "counted", "overhead"}), (
        "базова лінія знає про лічильник — тоді він міряє те, що їй зручно"
    )


def check_the_overhead_counter_is_proven_at_both_ends() -> None:
    """лічильник надбавки доведений на обох краях (AC-04b)"""
    owned = contract.owned_texts()

    # Край перший: контрактний запит — надбавка нуль.
    honest = Tally(owned=owned)
    honest.observe({"messages": [{"role": "user", "content": contract.RESEARCH_PROMPT}]})
    assert honest.overhead == 0, f"надбавка {honest.overhead} на суто контрактному запиті"

    # Край другий: чужий текст — надбавка строго додатна, і саме на його розмір.
    padded = Tally(owned=owned)
    extra = "Ти дуже старанний агент. Дій крок за кроком і не поспішай."
    padded.observe(
        {
            "messages": [
                {"role": "system", "content": extra},
                {"role": "user", "content": contract.RESEARCH_PROMPT},
            ]
        }
    )
    assert padded.overhead == tokens(extra), (padded.overhead, tokens(extra))
    assert padded.asked == honest.asked, "контрактна частина порахована по-різному"

    # І дзеркальна половина на справжньому прогоні: базова лінія додає нуль.
    client = _client()
    baseline.run(client)
    assert client.tally.overhead == 0, (
        f"базова лінія додала {client.tally.overhead} токенів понад контракт — "
        "тоді лічильник не відрізняє фреймворк від власного коду"
    )


def check_twenty_offline_runs_give_the_same_table() -> None:
    """FAILURE · детермінізм: двадцять прогонів дають ту саму таблицю (NFR-6, AC-04c)"""

    def fingerprint() -> tuple:
        with _table() as (rows, _, _text):
            return tuple(tuple(row.cells()) for row in rows)

    first = fingerprint()
    for run_index in range(1, 20):
        assert fingerprint() == first, f"прогін {run_index} дав іншу таблицю — числа мигтять"

    # І один прогін у СВІЖОМУ процесі. Двадцять прогонів тут ідуть в одному процесі, де
    # пакети вже імпортовані, тож мигтіння МІЖ процесами вони не бачать за побудовою —
    # а саме воно й було: 13992 невидимих рядки на холодному старті проти 1895 на теплому.
    import json  # noqa: PLC0415
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415

    probe = (
        "import json, tempfile;"
        "from pathlib import Path;"
        "from stages.s09_frameworks.run import collect;"
        "t=tempfile.mkdtemp();"
        "print(json.dumps([r.cells() for r in collect(Path(t)/'s09.jsonl')], ensure_ascii=False))"
    )
    done = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr[-400:]
    cold = tuple(tuple(cells) for cells in json.loads(done.stdout.strip().splitlines()[-1]))
    assert cold == first, (
        "свіжий процес дав іншу таблицю — прогрів прибрано або зламано, і колонка "
        f"невидимих рядків міряє, скільки разів запускали команду:{NEWLINE}{cold}"
    )


# --- координація -------------------------------------------------------------------------


def check_the_invisible_line_count_excludes_the_one_off_import() -> None:
    """FAILURE · невидимі рядки: разовий імпорт не входить у ціну прогону (AC-03)"""
    if not via_langgraph.available():
        raise NotVerified("langgraph не встановлено — невидимі рядки нема де взяти")

    # Перший прогін у СВІЖОМУ процесі виконує ще й рядки імпорту пакета. Без прогріву
    # число стрибало між процесами (1975 проти 1895), а перевірка мигтіння цього не бачила:
    # у неї всі двадцять прогонів ішли в одному процесі, де імпорт уже стався.
    cold = _client()
    with executed_lines("langgraph", "langchain_core") as first:
        via_langgraph.run(cold)
    warm = _client()
    with executed_lines("langgraph", "langchain_core") as second:
        via_langgraph.run(warm)

    assert len(second) <= len(first), (len(first), len(second))
    assert len(second) > 0, "прогрітий прогін не виконав жодного рядка пакета"

    # І число, яке потрапляє в таблицю, — саме прогріте.
    with _table() as (rows, _, _text):
        row = next(row for row in rows if row.module == "via_langgraph.py")
        assert row.invisible == len(second), (
            f"у таблиці {row.invisible} невидимих рядків, а прогрітий прогін дає "
            f"{len(second)} — колонка міряє, скільки разів ти запускав команду"
        )


def check_each_implementation_answers_why_a_step_ran_and_names_the_source() -> None:
    """координація: кожна реалізація каже, звідки береться відповідь «чому цей крок» (AC-06)"""
    with _table() as (rows, _, text):
        for row in _counted_rows(rows):
            assert row.coordination in ("явна", "неявна") or row.coordination.startswith("явна"), (
                row.name,
                row.coordination,
            )
            assert row.why_source, f"{row.name}: не названо, звідки береться відповідь"
            assert row.why_source in text, f"{row.name}: джерело не доїхало до таблиці"


def check_implicit_coordination_names_the_price_of_that_answer() -> None:
    """FAILURE · координація: ціна відповіді названа числом, а не твердженням (AC-06b)"""
    places = {name: compare.behaviour_prose(name) for name in IMPLEMENTATION}

    # Явна координація — нуль місць прози: наступний крок вирішує код.
    assert places["baseline.py"] == 0, places["baseline.py"]
    assert places["via_langgraph.py"] == 0, places["via_langgraph.py"]

    # Неявна — строго більше. Це вимір із ДЖЕРЕЛА, тож він є й для непригнаних реалізацій.
    assert places["via_crewai.py"] > places["via_langgraph.py"], places
    assert places["via_crewai.py"] >= 4, (
        f"у CrewAI {places['via_crewai.py']} місць прози — надто мало для двох агентів "
        "із ролями, метою й передісторією"
    )

    # Перелік має бачити описи ЗАДАЧ, а не лише ролей. Попередня редакція вимагала
    # «щонайменше чотири місця» — і звуження переліку до `{role, goal}` лишало рівно
    # чотири (двоє агентів × два поля), тобто мутація проходила наскрізь.
    for keyword in ("description", "instruction", "expected_output"):
        assert keyword in compare.BEHAVIOUR_PROSE, (
            f"{keyword!r} не рахується місцем прози — там живе поведінка ЗАДАЧІ, і без "
            "нього неявна координація виглядає дешевшою, ніж є"
        )

    # І вимір доводиться на синтетичному джерелі, а не лише на власних файлах.
    # Проба — у тимчасовий каталог, а не в дерево вихідників: убитий посеред прогону
    # набір лишав би там зайвий модуль, який далі побачить `ruff`.
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "probe.py"
        probe.write_text(
            "Agent(role='r', goal='g', backstory='b')"
            + NEWLINE
            + "Task(description='d')"
            + NEWLINE,
            encoding="utf-8",
        )
        assert compare.behaviour_prose(probe) == 4, compare.behaviour_prose(probe)

    with _table() as (rows, _, text):
        for row in rows:
            assert f"| {row.places} |" in text or str(row.places) in text, row.name


# --- третій стан і прапорець ---------------------------------------------------------------


def check_a_missing_package_yields_not_evaluated_never_a_failure() -> None:
    """третій стан: відсутній пакет дає «не перевірено» з названою причиною (AC-07)"""
    with _table() as (rows, _, text):
        missing = [row for row in rows if row.unverified]
        if not missing:
            raise NotVerified("усі пакети встановлено — гілку «не перевірено» не видно")
        for row in missing:
            assert row.unverified.strip(), f"{row.name}: причини не названо"
            assert compare.UNVERIFIED in row.cells(), row.cells()
            assert row.unverified in text, f"{row.name}: причина не доїхала до таблиці"
            # Вимір із джерела лишається навіть у непригнаного рядка.
            assert row.places == compare.behaviour_prose(row.module), row.name

    # Дві причини, а не одна: «не встановлено» й «не встановлюється» — різні події, і
    # злиття їх в одну робить пораду «постав пакет» знущанням із того, у кого він не
    # ставиться. Перевіряється саме РОЗРІЗНЕННЯ, а не наявність будь-якої причини.
    import sys  # noqa: PLC0415

    reason = via_crewai.unavailable_because()
    if sys.version_info[:2] > via_crewai.MAX_PYTHON:
        assert "Python" in reason, (
            f"на Python {sys.version_info[0]}.{sys.version_info[1]} причиною названо {reason!r} — "
            "читачеві радять поставити пакет, який на його інтерпретаторі не ставиться"
        )
        assert ".".join(map(str, via_crewai.MAX_PYTHON)) in reason, reason
    elif reason:
        assert "пакета немає" in reason, reason


def check_the_flag_on_without_credentials_fails_loudly() -> None:
    """FAILURE · прапорець: увімкнений ADK без креденшелів падає гучно (AC-07b)"""
    if via_adk.available():
        raise NotVerified("ADK доступний — гілку «просили й не змогли» не відтворити")

    was = os.environ.get(via_adk.FLAG)
    os.environ[via_adk.FLAG] = "1"
    try:
        assert via_adk.wanted(), "прапорець не читається"
        try:
            via_adk.demand()
        except via_adk.Demanded as loud:
            said = str(loud)
        else:
            raise AssertionError(
                "прапорець увімкнено, ADK недоступний, а харнес змовчав — читач попросив "
                "четвертий рядок, отримав три й не дізнався про це"
            )
        assert via_adk.FLAG in said and "неможливо" in said, said
    finally:
        if was is None:
            os.environ.pop(via_adk.FLAG, None)
        else:
            os.environ[via_adk.FLAG] = was

    # Дзеркальна половина: прапорець вимкнено — жодного шуму. Оточення читача при цьому
    # не діагностується: попередня редакція стверджувала `not wanted()` після `finally`,
    # тож у того, хто експортував прапорець, червоніла перевірка про власний харнес.
    without = {name: value for name, value in os.environ.items() if name != via_adk.FLAG}
    saved = dict(os.environ)
    os.environ.clear()
    os.environ.update(without)
    try:
        assert not via_adk.wanted()
        via_adk.demand()
    finally:
        os.environ.clear()
        os.environ.update(saved)


def check_a_changed_framework_api_reddens_that_implementations_smoke() -> None:
    """FAILURE · смоук: розрив API ловиться тут, а не на прогоні читача (AC-08, NFR-8)"""
    # Смоук — це ВИКОНАННЯ, а не імпорт: зникла точка входу має червоніти тут. І по ВСІХ
    # доступних реалізаціях: перевірка, названа за AC-08, знала одну, тож на машині з
    # CrewAI без LangGraph «смоук кожної реалізації» давав би НЕ ПЕРЕВІРЕНО для всіх.
    smoked = []
    for module, _name, _packages in IMPLEMENTATIONS:
        if module is baseline or module.unavailable_because():
            continue
        if hasattr(module, "wanted") and not module.wanted():
            continue
        result = module.run(_client())
        assert result.tools_used == contract.TOOLS, (module.NAME, result.tools_used)
        assert result.stopped_by == contract.ANSWERED, (module.NAME, result.stopped_by)
        smoked.append(module.NAME)
    if not smoked:
        raise NotVerified("жодного фреймворка не встановлено — смоук нема на чому прогнати")

    # NFR-8: **верхня** межа, а не підлога. Перевірка звіряла лише наявність рядка з
    # підлогою — тобто стверджувала протилежне тому, що вимагає NFR, і мовчала б, поки
    # читачеві приїжджає наступна мажорна версія.

    manifest = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    start = manifest.index("s09 = [")
    block = manifest[start : manifest.index("]", start)]
    pinned = re.findall(r'"([a-z-]+)>=([\d.]+),<([\d.]+)', block)
    assert {name for name, _, _ in pinned} == {"langgraph", "crewai"}, pinned
    for name, floor, ceiling in pinned:
        assert float(ceiling.split(".")[0]) > float(floor.split(".")[0]) or ceiling > floor, (
            f"{name}: межа {ceiling} не вища за підлогу {floor}"
        )
    assert "python_version < '3.14'" in block, (
        "маркер CrewAI зник — установка етапу на 3.14 знову впаде цілком і забере "
        "з собою LangGraph, який установився б чудово"
    )
    assert "langchain-openai" not in block, (
        "мертва залежність повернулась: жоден модуль етапу її не імпортує"
    )


# --- висновок ----------------------------------------------------------------------------


def check_the_table_carries_no_aggregate_score_and_no_winner() -> None:
    """висновок: жодного зведеного бала й жодного «найкращий» (AC-09)"""
    with _table() as (_rows, _, text):
        lowered = text.lower()
        for word in ("найкращ", "переможц", "переможе", "зведений бал", "загальний бал", "рейтинг"):
            assert word not in lowered, f"у таблиці зʼявилось {word!r} — ваги ніхто не обговорював"
        assert "## Правило вибору" in text, "висновку немає — читач по нього й прийшов"


def check_every_rule_of_choice_cites_a_column_of_the_table() -> None:
    """висновок: кожне правило називає колонку, з якої воно виведене (AC-09b)"""
    assert RULES, "правил вибору немає"
    for when, take, column in RULES:
        assert column in compare.COLUMNS, f"правило посилається на {column!r} — такої колонки немає"
        assert when.strip() and take.strip(), (when, take)

    with _table() as (_rows, _, text):
        for when, _take, column in RULES:
            assert when in text, f"правило {when!r} не доїхало до файлу"
            assert column in text, column


# --- зуби, межа провайдера, сусідній етап ---------------------------------------------------


def check_a_broken_implementation_reddens_the_check_that_asserts_about_it() -> None:
    """FAILURE · зуби: зламана реалізація червонить саме свою перевірку (AC-10)"""
    healthy = baseline.ask

    class _Mute:
        """Відповідь моделі без жодного виклику інструмента."""

        tool_calls = None
        content = "Поверніть, будь ласка, товар."

    def silent(client: Any, messages: list[dict[str, Any]], *, tools: bool = False) -> Any:
        """Зламано навмисно: модель більше не просить інструмента.

        Підробка розігрує сценарій **позиційно** й на прапорець `tools` не дивиться, тож
        просто вимкнути прапорець було б замало: перша редакція цієї мутації нічого не
        ламала, і перевірка на зуби сама зубів не мала.
        """
        client.chat.completions.create(model="fake", messages=messages)
        return _Mute()

    baseline.ask = silent
    try:
        import dataclasses  # noqa: PLC0415

        broken = contract.violations(dataclasses.replace(baseline.run(_client()), model_calls=2))
        assert broken, "базову лінію зламано, а контракт цього не побачив"
        assert any(name.startswith("інструменти") for name in broken), broken
    finally:
        baseline.ask = healthy

    # Полагоджено — контракт знову чистий.
    healed = contract.violations(dataclasses.replace(baseline.run(_client()), model_calls=2))
    assert healed == (), healed


def check_no_implementation_reaches_the_network_without_a_key() -> None:
    """FAILURE · межа: жодна реалізація не створює власного клієнта (AC-11)"""
    # Шукається **конструювання клієнта**, а не слово. `code_mentions` бачить `Name.id` та
    # `Attribute.attr` окремо, тож `"openai.openai"` не збігався ніколи — ассерт був
    # зеленим на джерелі, що дослівно містить `openai.OpenAI(...)`. А пошук самих слів дає
    # хибне спрацювання на `"openai/…"` — це префікс провайдера для LiteLlm, не клієнт.
    for name in IMPLEMENTATION:
        borrowed = _client_constructions((HERE / name).read_text(encoding="utf-8"))
        assert not borrowed, (
            f"{name} конструює власний транспорт ({borrowed}) — етап перестає проходитись "
            "офлайн, і робить це мовчки"
        )

    # Дзеркальна половина: пошук здатний знайти те, що шукає. Без неї «нічого не знайдено»
    # не відрізняється від «шукати не вміє» — саме цим і був попередній ассерт.
    planted = "import openai" + NEWLINE + "client = openai.OpenAI(api_key='x')" + NEWLINE
    assert _client_constructions(planted), "пошук не бачить навіть дослівного конструктора"

    # І доводиться ВИКОНАННЯМ. Неповне покриття віддається третім станом, а не зеленим:
    # звіт «ok» на двох доведених із чотирьох дає читачеві підстави думати, що доведено все.
    with _table() as (rows, _, _text):
        ran = _counted_rows(rows)
        for row in ran:
            assert row.asked > 0, f"{row.name}: лічильник не бачив жодного запиту — клієнт чужий"
        if len(ran) < len(IMPLEMENTATIONS):
            raise NotVerified(
                f"виконанням доведено {len(ran)} із {len(IMPLEMENTATIONS)}: "
                + "; ".join(row.unverified for row in rows if row.unverified)
            )


def check_the_stage_8_evaluator_extracts_more_than_one_trajectory() -> None:
    """крос-контекст: сусідній оцінювач читає трейс цього етапу (AC-12)"""
    from stages.s08_eval.trajectory import RUN_KEYS, extract, survey_run_keys  # noqa: PLC0415

    assert "case" in RUN_KEYS, (
        "ключ прогону цього етапу не входить у перелік, який знає оцінювач — вимір етапу 8 "
        "його не побачить"
    )

    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "s09.jsonl"
        rows = collect(traces)
        # Групування САМЕ за ключем прогону. Дефолтний `by_trace_id` дав би стільки ж
        # траєкторій і на коді, що ключа не пише взагалі, — тобто доводив би тотожність.
        walked = extract(traces, key=lambda step: step.get("case"))
        by_id = extract(traces)

    ran = [row for row in rows if row.counted]
    assert len(walked) == len(ran), (
        f"оцінювач витяг {len(walked)} траєкторій за ключем прогону на {len(ran)} прогонів"
    )
    assert {trajectory.key for trajectory in walked} == {row.name for row in ran}, (
        "ключі траєкторій не збігаються з іменами реалізацій — поле `case` пишеться не тим"
    )
    # Дзеркальна половина: без ключа групування дає те саме число, і саме тому попередня
    # редакція нічого не доводила.
    assert len(by_id) == len(walked), (len(by_id), len(walked))
    if len(ran) < 2:
        # На голій установці працює лише базова лінія. Рівність вище вже довела, що ключ
        # діє; «більше однієї» потребує двох прогонів, і чесніше сказати це, ніж послабити
        # твердження до одиниці.
        raise NotVerified(
            f"прогнано лише {len(ran)} реалізацію — «більше однієї траєкторії» нема на чому "
            'довести; постав `pip install -e ".[s09]"`'
        )
    assert len(walked) > 1, "менше двох траєкторій — твердження про ключ нема на чому довести"

    # Вимір етапу 8 сам себе не міряє (`s09 >= "s08"` він пропускає), тож ассерт про
    # `found["s09"]` не міг би впасти ніколи. Стверджуємо те, що справді перевірюване:
    # поле `case` є в переліку, який знає оцінювач, і воно справді пишеться в кроки.
    assert "s09" not in survey_run_keys(REPO_ROOT / "stages"), "оцінювач почав міряти етап 9"
    for module in ("baseline.py", "via_langgraph.py", "via_crewai.py", "via_adk.py"):
        source = (HERE / module).read_text(encoding="utf-8")
        assert "case=" in source, f"{module} не пише ключа прогону"


# --- урок і матеріали читача ---------------------------------------------------------------


def check_the_lesson_fits_the_reading_budget() -> None:
    """урок: не більше 2500 слів (NFR-3)"""
    words = len((HERE / "README.md").read_text(encoding="utf-8").split())
    assert words <= 2500, f"урок розрісся до {words} слів"


def check_the_lesson_numbers_match_the_bench() -> None:
    """FAILURE · урок: числа таблиці обчислені, а не набрані руками"""
    import json  # noqa: PLC0415

    # Числа уроку виводяться з УСІХ модулів реалізації **і з демо**, яке вирішує, що
    # потрапляє в таблицю. Під час мутації будь-якого з них ця перевірка червоніла б про
    # прозу, а не про властивість, яку мутація ламає, — і «червоних 2» читалося б як
    # «спіймали двічі» (PLAYBOOK §5).
    for name in (*IMPLEMENTATION, "run.py"):
        require_intact_source(name)

    lesson = (HERE / "README.md").read_text(encoding="utf-8")
    english = (HERE / "README.en.md").read_text(encoding="utf-8")
    checklist = (HERE / "CHECKLIST.md").read_text(encoding="utf-8")
    pinned = json.loads((HERE / "mutations.json").read_text(encoding="utf-8"))["mutations"]

    failures = sum(
        1 for check in CHECKS if (check.__doc__ or "").split(NEWLINE)[0].startswith("FAILURE")
    )
    flat = re.sub(r"\s+", " ", checklist)
    assert f"checks: {len(CHECKS)}, of them on failure modes: {failures}" in flat, (
        "чекліст називає інші числа, ніж дає набір"
    )
    for page in (lesson, english):
        assert f"{len(CHECKS)} " in page and f"{failures} " in page, (len(CHECKS), failures)

    # Розміри модулів — обчислені.
    for name in IMPLEMENTATION:
        lines = _executable_lines(name)
        assert f"`{lines} of {LINE_BUDGET}`" in lesson, (
            f"{name} має {lines} виконуваних рядків — урок називає інше число"
        )
        assert f"| {lines} |" in english, f"{name}: карта називає інший розмір, ніж {lines}"

    # Головні числа таблиці — теж вимір, а не проза.
    # Диз'юнкцій тут немає навмисно: `X in lesson or str(X) in lesson` тримається правою
    # половиною завжди, бо будь-яке число трапляється в тексті десь. Таблиця уроку
    # вирівняна пробілами, тож звіряється нормалізований рядок.
    flat_lesson = re.sub(r"[ 	]+", " ", lesson)
    with _table() as (rows, _, _text):
        # Урок цитує числа ПОВНОЇ установки. На голій вони інші й мають бути іншими, тож
        # звіряти нема з чим — це третій стан, а не розходження прози з кодом.
        if any(row.unverified for row in rows if row.module == "via_langgraph.py"):
            raise NotVerified(
                "langgraph is not installed — the lesson's table describes a full install; "
                'run `pip install -e ".[s09]"`'
            )

        # Число невидимих рядків залежить від інтерпретатора: та сама версія langgraph
        # виконує на 3.13 і на 3.14 різну кількість рядків. Тому урок називає, на чому
        # міряли, а перевірка звіряє це з тим, на чому біжить.
        #
        # Умова живе В УРОЦІ й читається звідти. Копія в коді розійшлася б із прозою
        # мовчки — а саме проти цього класу вад побудований весь етап.
        declared = re.search(r"measured on Python (\d+\.\d+)", lesson)
        assert declared, (
            "the lesson quotes an executed-line count without naming the interpreter it was "
            "measured on — a number without its conditions is not a measurement (stage 7)"
        )
        running = f"{sys.version_info.major}.{sys.version_info.minor}"
        if declared.group(1) != running:
            raise NotVerified(
                f"the lesson's numbers were measured on Python {declared.group(1)}, this run "
                f"is Python {running}; executed-line counts differ between interpreters"
            )
        for row in rows:
            cells = row.cells()
            wanted = f"| {row.name} | {cells[1]} | {cells[2]}"
            assert wanted in flat_lesson, (
                f"рядок {row.name!r} у таблиці уроку не той, що дає прогін: {wanted!r}"
            )
            assert f"| {row.places} |" in flat_lesson or f" {row.places} |" in flat_lesson, row.name

    assert f"| Mutations in the exercises | {len(pinned)} |" in lesson, len(pinned)


def check_the_exercises_match_the_pinned_mutations() -> None:
    """FAILURE · вправи: диф і числа беруться з mutations.json, а не пишуться"""
    import json  # noqa: PLC0415

    pinned = json.loads((HERE / "mutations.json").read_text(encoding="utf-8"))["mutations"]
    text_of = (HERE / "exercises.md").read_text(encoding="utf-8")

    for mutation in pinned:
        number = int(mutation["name"].split()[1])
        expected = mutation["expect_failed"]
        assert f"## Exercise {number} ·" in text_of, f"вправи {number} немає в прозі"
        assert f"**Red: {expected}.**" in text_of, number
        assert mutation["file"] in text_of, f"вправа {number}: файл не названо"
        for side in ("old", "new"):
            for line in mutation[side].split(NEWLINE):
                assert line.strip() in text_of, (
                    f"вправа {number}: рядка {line.strip()!r} немає в прозі — читач не "
                    "побачить, ЩО саме міняти"
                )

    assert text_of.count("## Exercise") == len(pinned), len(pinned)


def check_every_reader_file_exists() -> None:
    """матеріали: урок, карта, вправи, чеклісти й розвʼязок на місці"""
    for name in (
        "README.md",
        "README.en.md",
        "exercises.md",
        "CHECKLIST.md",
        "DECISION.md",
        "mutations.json",
        "solutions/exercise_3_where_the_overhead_hides.py",
        "solutions/README.md",
    ):
        path = HERE / name
        assert path.exists() and path.read_text(encoding="utf-8").strip(), name


# --- бюджети ------------------------------------------------------------------------------


def check_the_modules_fit_the_line_budget() -> None:
    """бюджет: кожен модуль реалізації вкладається у стелю рядків (NFR-1)"""
    for name in IMPLEMENTATION:
        require_intact_source(name)
        lines = _executable_lines(name)
        assert lines <= LINE_BUDGET, f"{name}: {lines} > {LINE_BUDGET} виконуваних рядків"


def check_the_demo_shows_every_scene_offline_within_its_budget() -> None:
    """e2e · демо: шість сцен, без ключа й без мережі, у межах часу (NFR-2b)"""
    import io  # noqa: PLC0415
    import time  # noqa: PLC0415
    from contextlib import redirect_stdout  # noqa: PLC0415

    from stages.s09_frameworks.run import main as demo_main  # noqa: PLC0415

    buffer = io.StringIO()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp, redirect_stdout(buffer):
        code = demo_main(table_path=Path(tmp) / "COMPARISON.md")
    took = time.perf_counter() - started
    output = buffer.getvalue()

    assert code == 0, code
    assert took <= 10, f"демо йшло {took:.1f} с — стеля 10 с (NFR-2b)"
    # Банер приходить із `shared.llm`, а не з літерала етапу: перевірка на літерал була
    # тавтологією й не побачила б, що демо каже «модель підроблена» читачеві з ключем.
    first = output.splitlines()[0]
    assert first.startswith("[") and get_model() in first, first
    for number in range(1, 7):
        assert f"{NEWLINE}{number}. " in output, f"сцена {number} не надрукувалась"

    # Числа сцен збігаються з тим, що дає прогін тут, а не набрані руками.
    with _table() as (rows, _, _text):
        for row in _counted_rows(rows):
            assert f"мої {row.mine:>4}   невидимі {row.invisible:>6}" in output, row.name
            assert f"просив {row.asked:>5}   понад запит {row.overhead:>5}" in output, row.name


def check_the_failure_modes_are_at_least_a_third() -> None:
    """перевірки: режимів відмови не менше третини (NFR-4)"""
    labels = [(check.__doc__ or "").split(NEWLINE)[0] for check in CHECKS]
    failures = [label for label in labels if label.startswith("FAILURE")]
    assert len(failures) * 3 >= len(CHECKS), (
        f"режимів відмови {len(failures)} із {len(CHECKS)} — менше третини"
    )


CHECKS = [
    check_one_command_yields_a_row_per_implementation,
    check_the_written_table_parses_back_to_the_same_numbers,
    check_exactly_one_row_carries_no_framework,
    check_all_implementations_honour_the_same_task_contract,
    check_an_implementation_that_breaks_the_contract_gets_no_numbers,
    check_my_lines_and_invisible_lines_are_two_separate_numbers,
    check_framework_lines_never_count_as_mine,
    check_tokens_are_counted_at_the_provider_boundary_both_numbers,
    check_the_overhead_counter_is_proven_at_both_ends,
    check_twenty_offline_runs_give_the_same_table,
    check_the_invisible_line_count_excludes_the_one_off_import,
    check_each_implementation_answers_why_a_step_ran_and_names_the_source,
    check_implicit_coordination_names_the_price_of_that_answer,
    check_a_missing_package_yields_not_evaluated_never_a_failure,
    check_the_flag_on_without_credentials_fails_loudly,
    check_a_changed_framework_api_reddens_that_implementations_smoke,
    check_the_table_carries_no_aggregate_score_and_no_winner,
    check_every_rule_of_choice_cites_a_column_of_the_table,
    check_a_broken_implementation_reddens_the_check_that_asserts_about_it,
    check_no_implementation_reaches_the_network_without_a_key,
    check_the_stage_8_evaluator_extracts_more_than_one_trajectory,
    check_the_modules_fit_the_line_budget,
    check_the_demo_shows_every_scene_offline_within_its_budget,
    check_the_lesson_fits_the_reading_budget,
    check_the_lesson_numbers_match_the_bench,
    check_the_exercises_match_the_pinned_mutations,
    check_every_reader_file_exists,
    check_the_failure_modes_are_at_least_a_third,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 9 · Frameworks")


if __name__ == "__main__":
    raise SystemExit(main())
