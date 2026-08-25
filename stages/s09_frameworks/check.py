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
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from shared.check_runner import NotVerified, code_mentions, require_intact_source, run_checks
from shared.fake_llm import FakeLLM
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
    """ВІДМОВА · таблиця: розібраний файл дає ті самі числа, що й прогін (AC-01b)"""
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
        ran = _counted_rows(rows)
        assert ran, "жодної реалізації не прогнано — контракт нема на чому довести"
        for row in ran:
            assert not row.broken, (row.name, row.broken)

    # Контракт — **код**, а не проза: він виконується на результаті, а не читається очима.
    import dataclasses  # noqa: PLC0415

    client = _client()
    result = dataclasses.replace(baseline.run(client), model_calls=client.tally.calls)
    assert contract.violations(result) == (), contract.violations(result)


def check_an_implementation_that_breaks_the_contract_gets_no_numbers() -> None:
    """ВІДМОВА · контракт: порушник лишається в таблиці, але без чисел (AC-02b)"""
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
    """ВІДМОВА · рядки: код фреймворка не рахується моїм (AC-03b)"""
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
    """ВІДМОВА · детермінізм: двадцять прогонів дають ту саму таблицю (NFR-6, AC-04c)"""

    def fingerprint() -> tuple:
        with _table() as (rows, _, _text):
            return tuple(tuple(row.cells()) for row in rows)

    first = fingerprint()
    for run_index in range(1, 20):
        assert fingerprint() == first, f"прогін {run_index} дав іншу таблицю — числа мигтять"


# --- координація -------------------------------------------------------------------------


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
    """ВІДМОВА · координація: ціна відповіді названа числом, а не твердженням (AC-06b)"""
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

    # Число вимірюється, а не оголошується: підкинутий опис має його змінити.
    grown = compare.BEHAVIOUR_PROSE | {"persona"}
    assert "persona" not in compare.BEHAVIOUR_PROSE, "перелік уже містить те, чого не мав"
    assert grown != compare.BEHAVIOUR_PROSE

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

    # Дві причини, а не одна: «не встановлено» й «не встановлюється» — різні події.
    reason = via_crewai.unavailable_because()
    if reason:
        assert "Python" in reason or "пакета немає" in reason, reason


def check_the_flag_on_without_credentials_fails_loudly() -> None:
    """ВІДМОВА · прапорець: увімкнений ADK без креденшелів падає гучно (AC-07b)"""
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
        # Названо ІМʼЯ змінної, а не її значення (spec §6.1).
        for name in via_adk.CREDENTIALS:
            assert os.environ.get(name, "не задано") not in said or name in said, said
    finally:
        if was is None:
            os.environ.pop(via_adk.FLAG, None)
        else:
            os.environ[via_adk.FLAG] = was

    # Дзеркальна половина: прапорець вимкнено — жодного шуму.
    assert not via_adk.wanted(), "прапорець лишився ввімкненим після перевірки"
    via_adk.demand()


def check_a_changed_framework_api_reddens_that_implementations_smoke() -> None:
    """ВІДМОВА · смоук: розрив API ловиться тут, а не на прогоні читача (AC-08, NFR-8)"""
    if not via_langgraph.available():
        raise NotVerified("langgraph не встановлено — смоук нема на чому прогнати")

    # Смоук — це ВИКОНАННЯ, а не імпорт: зникла точка входу має червоніти тут.
    result = via_langgraph.run(_client())
    assert result.steps == ("research", "writer"), result.steps
    assert result.tools_used == contract.TOOLS, result.tools_used

    # Пін мінорною межею названий у маніфесті, а не в голові.
    manifest = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "crewai>=0.60; python_version < '3.14'" in manifest, (
        "маркер CrewAI зник — установка етапу на 3.14 знову впаде цілком і забере "
        "з собою LangGraph, який установився б чудово"
    )
    assert "langgraph>=0.2" in manifest, "LangGraph зник з extras етапу"


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
    """ВІДМОВА · зуби: зламана реалізація червонить саме свою перевірку (AC-10)"""
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
    """ВІДМОВА · межа: жодна реалізація не створює власного клієнта (AC-11)"""
    for name in IMPLEMENTATION:
        source = (HERE / name).read_text(encoding="utf-8")
        assert not code_mentions(source, {"openai.openai", "httpx.client", "requests.post"}), (
            f"{name} створює власний клієнт — етап перестає проходитись офлайн, і робить це мовчки"
        )

    # І доводиться ВИКОНАННЯМ: усі прогони йдуть на підробці, без ключа й без мережі.
    with _table() as (rows, _, _text):
        for row in _counted_rows(rows):
            assert row.asked > 0, f"{row.name}: лічильник не бачив жодного запиту — клієнт чужий"


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
        walked = extract(traces)

    ran = [row for row in rows if row.counted]
    assert len(walked) == len(ran), (
        f"оцінювач витяг {len(walked)} траєкторій на {len(ran)} прогонів — ключ прогону "
        "не працює, і етап 9 додав пʼятий випадок до чотирьох наявних"
    )
    if len(ran) < 2:
        # На голій установці працює лише базова лінія. Рівність вище вже довела, що ключ
        # діє; «більше однієї» потребує двох прогонів, і чесніше сказати це, ніж послабити
        # твердження до одиниці.
        raise NotVerified(
            f"прогнано лише {len(ran)} реалізацію — «більше однієї траєкторії» нема на чому "
            'довести; постав `pip install -e ".[s09]"`'
        )
    assert len(walked) > 1, "менше двох траєкторій — твердження про ключ нема на чому довести"

    # І сам вимір етапу 8 має побачити цей етап як позначений.
    found = survey_run_keys(REPO_ROOT / "stages")
    assert found.get("s09") is None or found["s09"] == "case", found.get("s09")


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
    assert output.startswith("[FakeLLM]"), output.splitlines()[0]
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
    failures = [label for label in labels if label.startswith("ВІДМОВА")]
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
    check_the_failure_modes_are_at_least_a_third,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 9 · Frameworks")


if __name__ == "__main__":
    raise SystemExit(main())
