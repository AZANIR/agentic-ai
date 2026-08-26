"""Перевірки етапу 8.

    python -m stages.s08_eval.check

Працюють **без ключа й без мережі**. Суддя за замовчуванням — підробка з оголошеною
упередженістю (ADR-0002): вона грає роль зламаного приладу, щоб детекторові було що
виявляти, і робить доказ етапу відтворюваним.

Трейси **породжуються** тим самим `shared.trace`, що й етапи (ADR-0005), у тимчасовий
каталог: записаних фікстур немає, тож зміна формату ламає породження гучно, а не мовчки
лишає етап оцінювати формат, якого більше немає.
"""

from __future__ import annotations

import ast
import re
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from shared.check_runner import (
    NotVerified,
    code_mentions,
    require_intact_source,
    run_checks,
)
from shared.trace import iter_steps as shared_iter_steps
from shared.trace import trace_run
from stages.s08_eval import levels
from stages.s08_eval.bias import (
    LENGTH_PAIRS,
    POSITION_PAIRS,
    Finding,
    length_sweep,
    position_sweep,
)
from stages.s08_eval.cases import CASES, Act, Case, write
from stages.s08_eval.judge import (
    FIRST,
    SCALE,
    SECOND,
    TIE,
    BiasedJudge,
    ModelJudge,
    Scored,
    SteadyJudge,
    Unavailable,
    _is_unavailable,
)
from stages.s08_eval.levels import (
    COMPONENT,
    DETERMINISTIC,
    E2E,
    FAILED,
    JUDGED,
    PASSED,
    PATH,
    UNSCORED,
    evaluate,
)
from stages.s08_eval.online import (
    DEFAULT_SHARE,
    MIN_STREAM,
    TOLERANCE,
    blind_spots,
    sampled,
    watch,
)
from stages.s08_eval.report import LEVELS, STATES, Report, Row, parse, render, save
from stages.s08_eval.trajectory import (
    _traced_fields,
    by_ref,
    by_trace_id,
    extract,
    survey_run_keys,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent

# Стеля часу для `scripts/check_all.py` — проти розростання, не ціль швидкодії (NFR-2).
BUDGET_SECONDS = 30

NEWLINE = chr(10)

# Модулі **реалізації**. `run.py` — демо, `check.py` — цей набір; NFR-1 їх не рахує.
IMPLEMENTATION = (
    "trajectory.py",
    "cases.py",
    "levels.py",
    "judge.py",
    "bias.py",
    "report.py",
    "online.py",
)
LINE_BUDGET = 110

# Текст, який у трейсі сервісу грає роль написаного людиною. Він має не дійти до жодних
# матеріалів оцінювання — і саме його ми шукаємо у виводі (AC-07b).
SECRET_ASK = "мій пароль від банку Hunter2Zaporizhzhia"
SECRET_REPLY = "Ваш платіж на картку 1111 Hunter2Zaporizhzhia підтверджено."


@contextmanager
def _traced_cases(cases: list[Case] | None = None):
    """Породити трейс кейсів у тимчасовий файл і віддати шлях разом із відображенням."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cases.jsonl"
        yield path, write(path, cases)


def _report(judge=None, *, into: Path | None = None) -> tuple[Report, str]:
    """Прогнати набір і **записати** звіт. Повертає звіт і текст записаного файлу.

    `into` віддає власність над файлом викликові: перевірка, що стверджує про **файл**,
    має дивитись на нього, поки тимчасовий каталог ще живий.
    """
    judge = judge or BiasedJudge()
    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "cases.jsonl"
        made = write(traces)
        report = Report(judge_name=judge.name)
        for trajectory in extract(traces):
            case = made[trajectory.key]
            report.rows.append(Row(case, evaluate(case, trajectory, judge)))
        report.judge_calls = judge.calls
        target = save(report, into or Path(tmp) / "report.md")
        return report, target.read_text(encoding="utf-8")


def _service_trace(path: Path, *, requests: int = 3, secret: bool = False) -> None:
    """Трейс у стилі сервісу етапу 6: один `trace_run` на процес, `trace_ref` на запит.

    Пишеться тим самим `shared.trace`, що й сам етап 6 (`app.py`), — інакше перевірка
    доводила б властивість файлу, який зробила вона сама.
    """
    with trace_run("service", path=path, stage="s06") as tracer:
        for index in range(requests):
            ref = f"trc_req{index:04d}"
            tracer.step("received", trace_ref=ref, chars=len(SECRET_ASK) if secret else 12)
            if secret:
                tracer.step("intent", trace_ref=ref, question=SECRET_ASK)
                tracer.step("answered", trace_ref=ref, answer=SECRET_REPLY)
            else:
                tracer.step("intent", trace_ref=ref, branch="orders")
            tracer.step("done", trace_ref=ref, branch="orders", spent=0.01)


def _executable_lines(name: str) -> int:
    """Виконувані рядки модуля: без імпортів і без docstring."""
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


# --- три рівні й звіт --------------------------------------------------------------------


def check_one_case_yields_three_verdicts_and_three_evaluator_kinds() -> None:
    """рівні: один кейс дає три вердикти, і вид оцінювача стоїть біля кожного (AC-01)"""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "report.md"
        report, text = _report(into=target)
        assert target.exists() and target.stat().st_size > 0, "звіт не записано у файл"

    assert report.total == len(CASES), f"{report.total} рядків проти {len(CASES)} кейсів"
    for row in report.rows:
        seen = [verdict.level for verdict in row.verdicts]
        assert seen == list(LEVELS), f"{row.case.name}: рівні {seen}"
        for verdict in row.verdicts:
            assert verdict.kind in (DETERMINISTIC, JUDGED), verdict
            assert verdict.state in STATES, verdict

    for level in LEVELS:
        assert f"| {level} |" in text, f"у підсумках немає рівня {level}"
    # Вид оцінювача — у **записаному** файлі, а не лише в обʼєкті: читач бачить файл.
    assert f"({DETERMINISTIC})" in text and f"({JUDGED})" in text, (
        "у звіті немає виду оцінювача поруч із вердиктом — а це вимога AC-01, не оздоба"
    )


def check_the_written_report_parses_back_to_the_same_totals() -> None:
    """FAILURE · звіт: розібраний файл дає ті самі числа, що й лічильники (AC-01b)"""
    report, text = _report()

    counted = parse(text)
    for level in LEVELS:
        for state in STATES:
            assert counted[level][state] == report.count(level, state), (
                f"{level}/{state}: у файлі {counted[level][state]}, "
                f"у лічильниках {report.count(level, state)}"
            )

    # Знаменник — усі кейси. Суддя, що замовк ПОВНІСТЮ, цього не покаже: там і чисельник,
    # і знаменник нулі, і будь-яка формула дає нуль. Ламається воно на **частковій**
    # недоступності — і саме її треба подати.
    half, _ = _report(judge=_HalfJudge())
    assert half.total == report.total, "кількість рядків залежить від судді"
    unscored = half.count(E2E, UNSCORED)
    passed = half.count(E2E, PASSED)
    assert unscored and passed, f"половинчастий суддя дав {passed} пройдених і {unscored} без бала"
    assert half.share(E2E) == passed / half.total, (
        f"частка {half.share(E2E):.3f} проти {passed}/{half.total} = "
        f"{passed / half.total:.3f}: знаменник узято від оцінених, а мусить від усіх — "
        f"тоді він РОСТЕ, коли суддя падає ({passed / (half.total - unscored):.3f})"
    )

    # Дзеркальна половина: рядок, що не доїхав до файлу, розбір мусить спіймати.
    lost = NEWLINE.join(line for line in text.split(NEWLINE) if not line.startswith("| прямий"))
    assert parse(lost) != counted, "розбір не помітив зниклого рядка — він рахує не файл"


def check_a_case_passes_one_level_and_fails_another_in_the_same_row() -> None:
    """рівні: вердикти незалежні — один рядок несе і пройдено, і провалено (AC-03b)"""
    report, _ = _report()

    mixed = [
        row
        for row in report.rows
        if {verdict.state for verdict in row.verdicts} >= {PASSED, FAILED}
    ]
    assert mixed, (
        "у наборі немає жодного кейса, що проходить один рівень і провалює інший — "
        "тоді три рівні нічим не відрізняються від одного"
    )

    # І зворотне: жодного зведеного бала у звіті немає.
    _, text = _report()
    for word in ("загальний бал", "сумарний бал", "підсумковий бал"):
        assert word not in text.lower(), f"у звіті зʼявився {word} — ваги ніхто не обговорював"


def check_same_answer_different_paths_different_verdicts() -> None:
    """рівні: та сама відповідь, різні шляхи — різні вердикти (AC-03)"""
    report, _ = _report()
    rows = {row.case.name: row for row in report.rows}

    straight = rows["прямий шлях"]
    lucky = rows["щаслива випадковість: не той інструмент, та сама відповідь"]

    assert straight.case.answer == lucky.case.answer, "кейси мають нести ту саму відповідь"
    assert straight.by_level(E2E).state == lucky.by_level(E2E).state, (
        "e2e розрізнив кейси з однаковою відповіддю — тоді він дивиться не на відповідь"
    )
    assert straight.by_level(PATH).state == PASSED, straight.by_level(PATH)
    # «Остання ВІДПОВІДЬ і ні про що інше»: результат інструмента з полем `text` теж
    # рядок, і без обмеження за видом кроку він став би тим, що судить e2e.
    noisy = Case(
        name="інструмент віддав текст після відповіді",
        task="де моє замовлення",
        expected_tools=("get_order_status",),
        budget=4,
        answer="",
        expected_answer="замовлення в дорозі завтра",
        acts=(
            Act("llm_call", {"tool_calls": [], "answer": "Замовлення в дорозі, доставка завтра."}),
            Act("tool_call", {"tool": "get_order_status", "text": "СМІТТЯ З ІНСТРУМЕНТА"}),
        ),
    )
    with _traced_cases([noisy]) as (path, made):
        trajectory = extract(path)[0]
        assert trajectory.answer() == "Замовлення в дорозі, доставка завтра.", (
            f"останньою відповіддю став {trajectory.answer()!r} — крок інструмента "
            "визначає вердикт e2e, хоч правило каже «і ні про що інше»"
        )

    assert lucky.by_level(PATH).state == FAILED, (
        "щаслива випадковість пройшла рівень траєкторії — оцінювач не відрізняє "
        "інженерію від того, що просто зійшлося"
    )


def check_a_failed_step_is_named_by_its_kind_and_ordinal() -> None:
    """FAILURE · компонент: названо крок — його вид і номер, а не лише кейс (AC-03c)"""
    report, _ = _report()
    broken = [row for row in report.rows if row.by_level(COMPONENT).state == FAILED]
    assert broken, "жоден кейс не провалив компонентний рівень — набір без відмов"

    for row in broken:
        reason = row.by_level(COMPONENT).reason
        assert reason.startswith("крок "), f"{row.case.name}: причина {reason!r} без кроку"
        ordinal = reason.split()[1]
        assert ordinal.isdigit(), f"{row.case.name}: номер кроку {ordinal!r} не число"
        assert "·" in reason, f"{row.case.name}: у причині немає виду кроку — {reason!r}"


def check_a_trace_without_steps_of_that_kind_is_not_evaluated() -> None:
    """FAILURE · компонент: кроків немає — «не оцінено», а не «пройдено» (AC-03d)"""
    report, text = _report()
    empty = next(row for row in report.rows if row.case.name == "прогін без жодного кроку")

    verdict = empty.by_level(COMPONENT)
    assert verdict.state == UNSCORED, (
        f"порожній трейс отримав {verdict.state!r} — рівень, що зараховує відсутність "
        "даних як успіх, тим зеленіший, чим бідніший трейс"
    )
    assert verdict.kind == DETERMINISTIC, verdict
    assert UNSCORED in text, "третій стан не доїхав до записаного звіту"

    # Дзеркальна половина: трейс із кроками підсистем оцінюється, а не мовчить.
    filled = next(row for row in report.rows if row.case.name == "прямий шлях")
    assert filled.by_level(COMPONENT).state != UNSCORED, (
        "рівень каже «не оцінено» на трейсі з кроками — тоді він не оцінює ніколи"
    )


def check_deterministic_evaluators_call_the_judge_zero_times() -> None:
    """рівні: детермінований оцінювач не кличе суддю жодного разу (AC-04)"""
    with _traced_cases() as (path, made):
        trajectory = extract(path)[0]
        case = made[trajectory.key]

        judge = BiasedJudge()
        for evaluator in (levels.path, levels.component):
            before = judge.calls
            verdict = evaluator(case, trajectory)
            assert verdict.kind == DETERMINISTIC, verdict
            assert judge.calls == before, (
                f"{evaluator.__name__} покликав суддю — детермінований оцінювач, що "
                "платить за судження, робить вид оцінювача порожньою домовленістю"
            )

        judged = levels.e2e(case, trajectory, judge)
        assert judged.kind == JUDGED and judge.calls == 1, (judged, judge.calls)

    # Сумарна звірка: викликів рівно стільки, скільки оцінювачів, що судять, **мінус**
    # ті, кому не було що судити. Суддю не кличуть на трейс без відповіді — це не
    # розбіжність, а вся суть третього стану: за відсутні дані ніхто не платить.
    report, _ = _report()
    judging = sum(1 for row in report.rows for verdict in row.verdicts if verdict.kind == JUDGED)
    nothing = sum(
        1
        for row in report.rows
        for verdict in row.verdicts
        if verdict.reason == "відповіді в трейсі немає"
    )
    assert nothing, "жоден кейс не має трейсу без відповіді — гілку не перевірено"
    assert report.judge_calls == judging - nothing, (
        f"викликів {report.judge_calls}, оцінювачів, що судять — {judging}, з них "
        f"{nothing} без даних. Суддю кличуть про всяк випадок"
    )


# --- біас судді --------------------------------------------------------------------------


def check_swapping_the_order_flips_the_winner() -> None:
    """FAILURE · position bias: перестановка міняє вердикт (AC-05)"""
    found = position_sweep(BiasedJudge(), POSITION_PAIRS)

    assert found.checked == len(POSITION_PAIRS), found
    assert found.biased, (
        "детектор не знайшов перевороту на судді, чия позиційна надбавка оголошена в "
        "docstring — тоді він не виявляє нічого"
    )
    assert found.detail, "знахідка без деталей — читач не побачить, що саме перевернулось"
    for line in found.detail:
        assert "AB ->" in line and "BA ->" in line, line

    # Знахідка — про **прилад**, не про агента: у звіті вона стоїть окремо від рядків.
    report, text = _report()
    report.findings = [found]
    rendered = render(report)
    assert "## Знахідки про суддю" in rendered, "знахідку злито з оцінкою агента"
    assert "Знахідки про суддю" not in text.split("## Підсумки")[0], (
        "знахідка про суддю потрапила в таблицю кейсів"
    )


def check_a_stable_judge_yields_zero_flips() -> None:
    """position bias: на стабільному судді детектор мовчить (AC-05b)"""
    steady = position_sweep(SteadyJudge(), POSITION_PAIRS)

    assert steady.checked == len(POSITION_PAIRS), steady
    assert not steady.biased, (
        f"детектор знайшов {steady.found} переворотів на судді, чий вердикт не залежить "
        "від порядку — детектор, що спрацьовує завжди, не є детектором"
    )
    assert not steady.unavailable, steady.unavailable
    assert "згода" in steady.line(), steady.line()

    length = length_sweep(SteadyJudge(), LENGTH_PAIRS)
    assert not length.biased, f"length bias на стабільному судді: {length.detail}"


def check_padding_a_correct_answer_raises_its_score() -> None:
    """FAILURE · length bias: зайвий текст додає балів без виграшу в змісті (AC-06)"""
    judge = BiasedJudge()
    found = length_sweep(judge, LENGTH_PAIRS)

    assert found.biased, "детектор не побачив надбавки за довжину на судді, що її дає"
    assert found.found == found.checked, (
        f"надбавку знайдено лише на {found.found} парах із {found.checked} — пари для "
        "довжини побудовані так, що коротка й доповнена відрізняються ЛИШЕ зайвиною"
    )

    # Порога немає й бути не може: різниця називається **числом**.
    for pair, line in zip(LENGTH_PAIRS, found.detail, strict=True):
        assert "->" in line and "+" in line, line
        short = judge.score(pair.task, pair.first, pair.expected)
        padded = judge.score(pair.task, pair.second, pair.expected)
        assert padded.score > short.score, (pair.task, short, padded)
        assert pair.second.startswith(pair.first), (
            f"{pair.task}: доповнена відповідь не є коротшою плюс текст — тоді різниця "
            "балів може бути й за зміст, і демонстрація нічого не доводить"
        )
        assert padded.score <= SCALE, f"бал {padded.score} вийшов за шкалу {SCALE}"


def check_an_unavailable_judge_yields_not_evaluated_never_a_failure() -> None:
    """FAILURE · третій стан: недоступний суддя дає «не оцінено» (AC-08)"""
    report, text = _report(judge=_MuteJudge())

    assert report.count(E2E, UNSCORED) == report.total, (
        f"у третьому стані лише {report.count(E2E, UNSCORED)} з {report.total} — "
        "решту зараховано провалом, хоча провалився прилад, а не агент"
    )
    assert report.count(E2E, FAILED) == 0, "відмова судді порахована провалом агента"
    assert report.evaluated_nothing() is False, (
        "детерміновані рівні оцінились, а звіт каже, що не оцінено нічого"
    )

    # Дзеркальна половина: прогін, де НЕ оцінено нічого, звіт називає неуспішним прямо.
    blank = Report(judge_name="mute")
    blank.rows = [
        Row(CASES[0], [levels.Verdict(level, UNSCORED, JUDGED, "нема чим") for level in LEVELS])
    ]
    assert blank.evaluated_nothing(), "суцільне «не оцінено» не розпізнано"
    assert "НЕ Є УСПІШНИМ" in render(blank), "порожня зелень видана за результат"

    # Перелік ЗАКРИТИЙ: баг у самому харнесі мусить летіти далі, а не читатись як
    # «прилад недоступний». Без цього ассерту гілка `ModelJudge._ask` не виконується
    # жодного разу — обидва підроблені судді кидають `Unavailable` самі.
    assert not _is_unavailable(ZeroDivisionError("баг у харнесі")), (
        "будь-який виняток читається як «не оцінено» — тиха зелень замість гучного провалу"
    )
    assert not _is_unavailable(AttributeError("NoneType has no attribute choices")), (
        "зіпсована відповідь провайдера читається як недоступність приладу"
    )
    for named in (TimeoutError("збіг"), RuntimeError("rate limit exceeded"), ConnectionError()):
        assert _is_unavailable(named), f"{type(named).__name__} має бути в переліку"

    # Детектор біасу теж має третій стан, а не нуль знахідок.
    found = position_sweep(_MuteJudge(), POSITION_PAIRS)
    assert found.unavailable and not found.biased, found
    assert "НЕ ОЦІНЕНО" in found.line(), found.line()
    assert UNSCORED in text, "третій стан не доїхав до файлу"


# --- онлайн ------------------------------------------------------------------------------


def check_cheap_checks_cover_every_trajectory_the_judge_only_a_share() -> None:
    """онлайн: дешеві чеки на кожній траєкторії, суддя — на частці (AC-07)"""
    with _traced_cases() as (path, made):
        judge = BiasedJudge()
        seen = watch(path, key=by_trace_id, judge=judge, share=DEFAULT_SHARE)

        assert seen.checked == len(made), (
            f"дешеві чеки побачили {seen.checked} із {len(made)} траєкторій — «на всьому "
            "трафіку» означає на всьому"
        )
        assert seen.judged == judge.calls, (seen.judged, judge.calls)
        assert seen.problems, "жодного зауваження на наборі, де третина кейсів крайні"

    # Частка — на потоці зі СТАЛИМИ ідентифікаторами. Ідентифікатор трейсу випадковий,
    # тож на двадцяти одному прогоні `judged` мигтить між нулем і кількома: на десяти
    # відсотках нуль випадає приблизно раз на девʼять прогонів. Перевірка, що падає раз
    # на девʼять, буде вимкнена — і забере з собою єдиний доказ цього критерію.
    with tempfile.TemporaryDirectory() as tmp:
        service = Path(tmp) / "service.jsonl"
        _service_trace(service, requests=60)

        judge = BiasedJudge()
        seen = watch(service, key=by_ref, judge=judge, share=DEFAULT_SHARE)
        expected = sum(sampled(f"trc_req{index:04d}") for index in range(60))

        assert seen.checked == 60, seen.checked
        assert seen.sampled_count == expected, (seen.sampled_count, expected)
        assert seen.judged == expected, (seen.judged, expected)
        assert 0 < seen.sampled_count < seen.checked, (
            f"у семплі {seen.sampled_count} із {seen.checked}: або нікого, або всіх — "
            "тоді частка не є часткою"
        )
        # Відібрані й оцінені — різні числа. Суддя, у якого скінчилась квота, не
        # робить семплер неправильним, і частка не має від цього мінятись.
        blocked = watch(service, key=by_ref, judge=_MuteJudge(), share=DEFAULT_SHARE)
        assert blocked.sampled_count == expected and blocked.judged == 0, blocked
        assert blocked.share == seen.share, (
            f"частка змінилась з {seen.share:.3f} на {blocked.share:.3f}, коли замовк "
            "суддя — вона рахується від оцінених, а мусить від відібраних"
        )

        # Обидва числа названі в одному рядку — інакше «на частці» лишається обіцянкою.
        line = seen.line()
        assert f"перевірено {seen.checked}" in line, line
        assert f"у семплі {seen.sampled_count}" in line, line
        assert f"оцінено {seen.judged}" in line, line

    # Поза смугою: `watch` лише читає. Ані `trace_run`, ані запису в модулі немає.
    # Не греп по тексту, а розбір AST: `code_mentions` не бачить ані docstring, ані
    # коментарів, тож перевірка не червоніє на прозі, що САМЕ від запису й застерігає.
    source = (HERE / "online.py").read_text(encoding="utf-8")
    written = code_mentions(source, {"trace_run", "write_text", "write_bytes", "open"})
    assert not written, f"онлайн-модуль пише ({written}) — оцінювання стало доданком до відповіді"


def check_neither_request_nor_answer_text_reaches_the_report_or_the_trace() -> None:
    """FAILURE · приватність: тексту запиту й відповіді немає в матеріалах (AC-07b)"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "service.jsonl"
        _service_trace(path, secret=True)

        judge = BiasedJudge()
        seen = watch(path, key=by_ref, judge=judge, share=1.0)
        assert seen.checked == 3, seen.checked

        # МАТЕРІАЛИ — це записаний звіт і власний трейс прогону, як каже AC-07b, а не
        # обʼєкт `Watch`. Попередня редакція дивилась саме на нього, а він складається з
        # лічильників і сталих літералів: жодна мутація коду не змогла б занести туди
        # текст користувача, тож ассерт був істинним ЗА ПОБУДОВОЮ.
        # Кейс із секретом у **вільному** полі `reason` — єдиний реальний шлях витоку:
        # компонентний рівень колись копіював його значення просто у причину вердикта.
        leaky = Case(
            name="запит із чутливим текстом",
            task="запит користувача",
            expected_tools=(),
            budget=4,
            answer="",
            expected_answer="",
            acts=(Act("tool_rejected", {"tool": "pay", "reason": SECRET_ASK}),),
        )
        report = Report(judge_name=judge.name)
        with _traced_cases([leaky]) as (leaky_path, made):
            for trajectory in extract(leaky_path):
                case = made[trajectory.key]
                report.rows.append(Row(case, evaluate(case, trajectory, judge)))
        for trajectory in extract(path, key=by_ref):
            report.rows.append(Row(leaky, evaluate(leaky, trajectory, judge)))
        own = Path(tmp) / "own.jsonl"
        with trace_run("eval", path=own, stage="s08") as tracer:
            tracer.step("watched", checked=seen.checked, sampled=seen.sampled_count)

        materials = NEWLINE.join(
            [render(report), own.read_text(encoding="utf-8"), seen.line(), *seen.problems]
        )
        for text in (SECRET_ASK, SECRET_REPLY, "Hunter2Zaporizhzhia"):
            assert text not in materials, (
                f"текст користувача {text[:24]!r} потрапив у матеріали оцінювання"
            )

        # Сталий підпис — властивість СИГНАТУРИ, а не слово в docstring: підміна дефолта
        # на справжнє питання лишила б грепання по прозі зеленим.
        import inspect

        signature = inspect.signature(watch).parameters["task"].default
        assert signature == "запит користувача", (
            f"дефолт `task` став {signature!r} — у промпт судді пішов текст людини"
        )

    # Дзеркальна половина: фікстури демонстрації біасу під заборону НЕ підпадають —
    # без них знахідка стала б числом без прикладу.
    #
    # Знахідка складається тут вручну, а не береться з детектора: інакше перевірка
    # приватності червоніла б щоразу, коли детектор нічого не знайшов, — і звинувачувала б
    # у витоку поріг, якого хтось додав у сусідній модуль.
    shown = Finding("length bias", 1, 1, [f"{LENGTH_PAIRS[0].task}: 3 -> 5 (+2)"])
    report, _ = _report()
    report.findings = [shown]
    assert LENGTH_PAIRS[0].task in render(report), (
        "заборона на текст користувача вимела й фікстури автора"
    )
    assert all(pair.first for pair in LENGTH_PAIRS), "пари демонстрації спорожніли"


def check_the_sampled_share_matches_the_declared_one_within_the_stated_margin() -> None:
    """онлайн: фактична частка збігається із заявленою в межах зі специфікації (AC-07c)"""
    stream = [f"req_{index:08x}" for index in range(1_000)]
    assert len(stream) >= MIN_STREAM, "потік коротший за мінімальний — вимір нічого не значить"

    for target in (0.10, 0.25, 0.50):
        hit = sum(sampled(request, share=target) for request in stream)
        actual = hit / len(stream)
        assert abs(actual - target) <= TOLERANCE, (
            f"заявлено {target:.0%}, вийшло {actual:.1%} — поза межею ±{TOLERANCE:.0%}"
        )

    # Детермінізм: той самий ідентифікатор завжди дає те саме рішення.
    twice = [sampled(request) for request in stream]
    assert twice == [sampled(request) for request in stream], "відбір мигтить між прогонами"

    # І дзеркальна половина: частки справді різні. Семплер, що завжди каже «так», теж
    # «детермінований» і теж «збігається» — з будь-якою заявленою часткою нижче ста.
    assert sum(twice) < sum(sampled(r, share=0.50) for r in stream), (
        "десять відсотків і половина дали однакову вибірку — семплер не розрізняє частки"
    )


# --- траєкторії поверх чужих трейсів -----------------------------------------------------


def check_stage_traces_are_read_exactly_as_the_stages_wrote_them() -> None:
    """крос-контекст: читаємо трейси етапів, не змінюючи жодного етапу (AC-02)"""
    for name in (*IMPLEMENTATION, "run.py", "check.py"):
        source = (HERE / name).read_text(encoding="utf-8")
        # `code_mentions` розбирає AST, тож не червоніє на docstring, який сам застерігає
        # від імпорту сусіднього етапу. Греп по тексту робив саме це — форма, проти якої
        # цей помічник і написаний (`shared/check_runner.py`).
        borrowed = code_mentions(source, {f"stages.s0{stage}_" for stage in range(1, 8)})
        assert not borrowed, (
            f"{name} імпортує сусідній етап ({borrowed}) — етап, який довелося б "
            "інструментувати заради оцінювання, довів би, що трасування додали запізно (C-2)"
        )

    # Читання йде крізь спільний `shared.trace` — і це звіряється **тотожністю обʼєкта**,
    # а не наявністю підрядка з іменем імпорту.
    assert extract.__globals__["iter_steps"] is shared_iter_steps, (
        "траєкторії читаються не спільним читачем — власний розбір переживе зміну формату мовчки"
    )

    # І головне: харнес читає СПРАВЖНІЙ трейс, записаний етапами, а не лише той, що
    # написала ця перевірка. Без цього твердження «оцінювання поверх наявних трейсів»
    # доводиться файлом власного виробництва — і `_service_trace` про це прямо каже.
    written = sorted(REPO_ROOT.glob("traces/*.jsonl"))
    if not written:
        raise NotVerified("у traces/ порожньо — прогони будь-який етап і повтори")
    for path in written:
        walked = extract(path)
        assert walked, f"{path.name}: жодної траєкторії — читач не розуміє чужого формату"
        assert all(trajectory.steps for trajectory in walked), path.name


def check_the_input_trace_file_is_byte_identical_after_a_run() -> None:
    """FAILURE · оцінювання читає й не пише в те, що оцінює (AC-02b)"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "service.jsonl"
        _service_trace(path, requests=4)
        before = path.read_bytes()

        watch(path, key=by_ref, judge=BiasedJudge(), share=1.0)
        extract(path, key=by_ref)

        assert path.read_bytes() == before, (
            "файл трейсів змінився після прогону оцінювання — другий прогін знайшов би "
            "серед вхідних даних трейс першого й почав би оцінювати оцінювача"
        )

    # Друга половина: власний трейс пишеться лише в **явно** заданий шлях. Аргумент
    # `path` у `write()` обовʼязковий — за замовчуванням у спільний денний файл нічого
    # не йде.
    import inspect

    signature = inspect.signature(write)
    default = signature.parameters["path"].default
    assert default is inspect.Parameter.empty, (
        f"`write()` має шлях за замовчуванням ({default!r}) — оцінювач допише у спільний "
        "денний файл, і наступний прогін оцінюватиме попередній"
    )


def check_one_grouping_key_parameter_serves_both_stage_1_and_the_stage_6_service() -> None:
    """крос-контекст: ключ прогону — параметр, а не поле в коді (AC-11)"""
    with tempfile.TemporaryDirectory() as tmp:
        service = Path(tmp) / "service.jsonl"
        _service_trace(service, requests=5)

        by_request = extract(service, key=by_ref)
        assert len(by_request) == 5, (
            f"на трейсі сервісу вийшло {len(by_request)} траєкторій замість 5 — "
            "групування по запиту не працює там, де воно єдине правильне"
        )

        # Дзеркальна половина, без якої твердження порожнє: той самий файл, ключ етапу 1 —
        # і весь процес схлопується в ОДНУ траєкторію. Це «формально працює», яке
        # порахувало б підсумки по одному рядку.
        by_process = extract(service, key=by_trace_id)
        assert len(by_process) == 1, (
            f"{len(by_process)} траєкторій за `trace_id` — тоді ключ не має значення, "
            "і параметризувати не було чого"
        )

    with _traced_cases() as (path, made):
        # На етапі 1 все навпаки: `trace_id` дає прогін, `trace_ref` — нічого.
        assert len(extract(path, key=by_trace_id)) == len(made), "етап 1 не групується"
        assert extract(path, key=by_ref) == [], (
            "кроки без `trace_ref` потрапили в траєкторію — відкат на `trace_id` дає "
            "зайвий прогін, який кожен рівень мусив би ігнорувати окремо"
        )


def check_what_the_traces_lack_is_counted_not_assumed() -> None:
    """крос-контекст: чого бракує у трейсі — названо числом (AC-12)"""
    with tempfile.TemporaryDirectory() as tmp:
        service = Path(tmp) / "service.jsonl"
        _service_trace(service, requests=3)
        walked = extract(service, key=by_ref)

        blind = blind_spots(walked)
        assert len(blind) == 2, f"сліпих вимірів {len(blind)}, а трейс сервісу не дає двох: {blind}"
        assert any("відповід" in spot for spot in blind), blind
        assert any("термінального" in spot for spot in blind), blind

        # «Зауважень нуль» на такому файлі означало б «усе гаразд» замість «дивитись
        # нема на що»: сліпий вимір не має перетворюватись на зауваження.
        seen = watch(service, key=by_ref)
        assert seen.blind == blind, (seen.blind, blind)
        assert not any("не завершився" in problem for problem in seen.problems), (
            "відсутність термінального кроку порахована зауваженням — сліпе стало "
            "провалом, і звіт тим гірший, чим бідніший трейс"
        )
        assert "сліпих вимірів" in seen.line(), seen.line()

    # Дзеркальна половина: на трейсі етапу 1 сліпих вимірів немає — обидва поля там є.
    with _traced_cases() as (path, _):
        assert blind_spots(extract(path)) == [], "етап 1 теж оголошено сліпим"

    # І головне: «чого бракує» — це ВИМІР із джерел, а не число в прозі. Попередня
    # редакція називала чотири поля й два етапи без ключа, і помилялась двічі: рахувала
    # фазу відмови етапу 4 за ключ прогону й забула про етап 7.
    found = survey_run_keys(HERE.parent)
    named = sorted({field for field in found.values() if field})
    without = sorted(stage for stage, field in found.items() if field is None)

    assert "s08" not in found, "оцінювання міряє себе"
    assert named == ["scenario", "scene", "trace_ref"], named
    assert without == ["s02", "s03", "s04", "s07"], without
    assert "phase" not in named, (
        "фаза відмови етапу 4 порахована ключем прогону — на щасливому шляху вона None"
    )

    # Дзеркальна половина виміру: параметр функції не є полем трейсу. Саме на цьому
    # спіткнувся греп — `whole(run=run)` етапу 7 читався як ключ прогону.
    assert _traced_fields("tracer.step('x', scenario='a')") == {"scenario"}, "крок не читається"
    assert _traced_fields("whole(run=run)") == set(), "параметр функції порахований полем"


def check_the_step_order_is_restored_from_the_sequence_number() -> None:
    """FAILURE · траєкторія: порядок кроків береться з `seq`, а не з порядку в файлі"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "shuffled.jsonl"

        with trace_run("left", path=path, stage="s08") as left:
            with trace_run("right", path=path, stage="s08") as right:
                for index in range(3):
                    left.step("tool_call", tool=f"left_{index}")
                    right.step("tool_call", tool=f"right_{index}")

        # Рядки перевертаються НАВМИСНО. Поки один дописувач пише сам у себе, файловий
        # порядок збігається з `seq`, і сортування нічого не змінює — перевірка, що
        # читає щойно записаний файл, зелена й з сортуванням, і без нього.
        #
        # Порядок ламається там, де файл склали з кількох джерел: зшиті шарди, буферизований
        # відправник логів, догнаний хвіст після збою. Перевернутий файл — найдешевша
        # модель саме цього, і вона робить твердження docstring перевірюваним.
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text(NEWLINE.join(reversed(lines)) + NEWLINE, encoding="utf-8")

        walked = {trajectory.steps[0]["name"]: trajectory for trajectory in extract(path)}
        assert set(walked) == {"left", "right"}, sorted(walked)

        for name, trajectory in walked.items():
            tools = trajectory.tools()
            assert tools == [f"{name}_{index}" for index in range(3)], (
                f"{name}: кроки прийшли як {tools} — порядок узято з файлу, а не з `seq`"
            )
            seqs = [step["seq"] for step in trajectory.steps]
            assert seqs == sorted(seqs), f"{name}: {seqs}"
            assert trajectory.outcome() == "ok", (
                f"{name}: підсумок прогону загубився — його шукають з кінця, а кінець "
                "визначається порядком"
            )


# --- урок і матеріали читача -------------------------------------------------------------


def check_the_real_judge_refuses_an_unreadable_verdict() -> None:
    """FAILURE · суддя-модель: вердикт розбирається точно або не розбирається (AC-05, AC-08)

    Ця перевірка існує тому, що `ModelJudge` не виконувався **жодного разу**: обидва
    підроблені судді кидають `Unavailable` самі, а справжнього не було навіть у списку
    імпортів. Файл, який лише читають, — це файл, який не запускають (PLAYBOOK §5).
    """
    judge = ModelJudge()

    # Бал: одне ціле число, і нічого крім нього. Попередня редакція збирала ВСІ цифри
    # рядка, тож «оцінка: 3 з 10» ставало десяткою, а «0 з 10» — одиницею. Промпт сам
    # називає шкалу, тож її повторення — найімовірніша форма відповіді.
    for said, expected in (("8", 8), ("0", 0), (" 3 ", 3), ("10", SCALE), ("99", SCALE)):
        judge._ask = lambda _, text=said: text
        assert judge.score("t", "a", "b").score == expected, (said, expected)
    for said in ("8/10", "оцінка: 3 з 10", "0 з 10", "вісім", ""):
        judge._ask = lambda _, text=said: text
        try:
            scored = judge.score("t", "a", "b")
        except Unavailable:
            continue
        raise AssertionError(f"{said!r} розібрано як {scored.score} — нерозбірливе стало балом")

    # Вердикт: ТОЧНИЙ збіг. Пошук підрядка йшов у сталому порядку, тож «перемагає друга»
    # давало «перша» — і `position_sweep` рахував це переворотом, рапортуючи біас,
    # породжений власним парсером, на судді, який його не мав.
    for said, expected in (("перша", FIRST), ("Друга.", SECOND), (" НІЧИЯ ", TIE)):
        judge._ask = lambda _, text=said: text
        assert judge.compare("t", "a", "b").winner == expected, said
    for said in ("перша гірша, перемагає друга", "не перша, а друга", "важко сказати"):
        judge._ask = lambda _, text=said: text
        try:
            verdict = judge.compare("t", "a", "b")
        except Unavailable:
            continue
        raise AssertionError(f"{said!r} розібрано як {verdict.winner!r} — вердикт з повітря")

    # І дзеркальна половина: без ключа суддя чесно недоступний, а не мовчки зелений.
    from shared.config import settings  # noqa: PLC0415

    if settings.has_real_llm:
        raise NotVerified("ключ налаштовано — гілка «провайдера немає» не перевіряється")
    try:
        ModelJudge().score("t", "a", "b")
    except Unavailable:
        return
    raise AssertionError("без провайдера суддя видав бал — узятий нізвідки")


def check_the_lesson_fits_the_reading_budget() -> None:
    """урок: не більше 2500 слів (NFR-3)"""
    words = len((HERE / "README.md").read_text(encoding="utf-8").split())
    assert words <= 2500, f"урок розрісся до {words} слів"


def check_the_lesson_numbers_match_the_suite() -> None:
    """FAILURE · урок: числа складу набору обчислені, а не набрані руками"""
    import json

    # Числа уроку виводяться з УСІХ модулів реалізації, тож під час мутації будь-якого з
    # них ця перевірка червоніє про прозу, а не про властивість, яку мутація ламає.
    # «Червоних 2» замість «червоних 1» читається як «спіймали двічі» — і розчиняє сигнал
    # рівно там, де його вимірюють (PLAYBOOK §5).
    for name in IMPLEMENTATION:
        require_intact_source(name)

    lesson = (HERE / "README.md").read_text(encoding="utf-8")
    checklist = (HERE / "CHECKLIST.md").read_text(encoding="utf-8")
    pinned = json.loads((HERE / "mutations.json").read_text(encoding="utf-8"))["mutations"]

    failures = sum(
        1 for check in CHECKS if (check.__doc__ or "").split(NEWLINE)[0].startswith("FAILURE")
    )
    edge = sum(1 for case in CASES if case.edge)

    assert f"{len(CHECKS)} " in lesson, f"кількість перевірок ({len(CHECKS)}) не названа"
    assert f"{failures} " in lesson, f"кількість режимів відмови ({failures}) не названа"
    flat = re.sub(r"\s+", " ", checklist)
    assert f"{len(CHECKS)} checks, {failures} of them on failure modes" in flat, (
        "чекліст називає інші числа, ніж дає набір"
    )
    assert f"| Cases in the set / edge among them | {len(CASES)} / {edge} |" in lesson, (
        f"склад набору у прозі не збігається з набором: {len(CASES)} / {edge}"
    )
    assert f"| Mutations in the exercises | {len(pinned)} |" in lesson, len(pinned)

    # ГОЛОВНІ числа етапу — теж вимір. Без цього доказ лишався єдиним місцем уроку, де
    # числа набрані руками, попри власну доктрину «обчислені, а не написані».
    for found in (
        position_sweep(BiasedJudge(), POSITION_PAIRS),
        length_sweep(BiasedJudge(), LENGTH_PAIRS),
        position_sweep(SteadyJudge(), POSITION_PAIRS),
    ):
        assert found.line() in lesson, f"урок не називає того, що дає прогін: {found.line()}"
    stream = [f"req_{index:08x}" for index in range(1_000)]
    hit = sum(sampled(request) for request in stream)
    assert f"{hit} до судді = {hit / len(stream):.1%}" in lesson, (
        f"частка семплінгу в уроці не та, що дає прогін: {hit}"
    )

    # Три частки — з прогону, а не з попередньої редакції уроку. Таблиця уроку вирівняна
    # пробілами, тож звіряється нормалізований рядок, а не сира розмітка.
    report, _ = _report()
    flat_lesson = re.sub(r"[ 	]+", " ", lesson)
    for level in LEVELS:
        row = " ".join(
            [level, *(str(report.count(level, state)) for state in STATES)]
            + [f"{report.share(level):.0%}"]
        )
        assert row in flat_lesson, f"у таблиці уроку не той рядок, що дає прогін: {row!r}"


def check_the_lesson_line_counts_match_the_modules() -> None:
    """FAILURE · урок: розміри модулів у прозі — обчислені (NFR-1)"""
    lesson = (HERE / "README.md").read_text(encoding="utf-8")

    for name in IMPLEMENTATION:
        require_intact_source(name)
        lines = _executable_lines(name)
        assert f"`{lines} of {LINE_BUDGET}`" in lesson, (
            f"{name} має {lines} виконуваних рядків — урок називає інше число"
        )


def check_the_exercises_match_the_pinned_mutations() -> None:
    """FAILURE · вправи: диф і числа беруться з mutations.json, а не пишуться"""
    import json

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
        "exercises.md",
        "CHECKLIST.md",
        "DECISION.md",
        "mutations.json",
        "solutions/exercise_2_the_denominator_climbs.py",
        "solutions/README.md",
    ):
        path = HERE / name
        assert path.exists() and path.read_text(encoding="utf-8").strip(), name


# --- набір, зуби перевірок і бюджети -----------------------------------------------------


def check_at_least_a_third_of_the_case_set_is_edge_by_observation() -> None:
    """набір: третина кейсів крайні, і крайність виводиться зі спостереження (AC-10)"""
    edge = [case for case in CASES if case.edge]
    need = -(-len(CASES) // 3)  # третина вгору

    assert len(CASES) >= 20, f"кейсів {len(CASES)} — менше двадцяти (NFR-7)"
    assert len(edge) >= need, f"крайніх {len(edge)} із {len(CASES)}, треба щонайменше {need}"

    # Самопроголошеної мітки немає: крайність — **обчислювана** властивість, а не поле,
    # яке автор виставляє руками. Інакше NFR задовольняється перемиканням прапорця.
    #
    # Стверджуємо про сам дата-клас, а не грепом по файлу: у цьому курсі пошук у тексті
    # вже чотири рази червонів на docstring, який САМЕ від цієї помилки й застерігає
    # (`shared/check_runner.code_mentions`).
    import dataclasses

    stored = {field.name for field in dataclasses.fields(Case)}
    assert "edge" not in stored, (
        "крайність стала полем кейса — набір із двадцяти щасливих шляхів лишиться "
        "зеленим, бо прапорець можна виставити"
    )
    assert isinstance(Case.edge, property), "крайність не обчислюється, а зберігається"

    # Дзеркальна половина, без якої попередній ассерт нічого не вартий: прапорець можна
    # перейменувати. Крайність має залежати ВИКЛЮЧНО від `acts`, тож зміна будь-якого
    # іншого поля не сміє її перемкнути — а `status="whatever"` колись перемикав.
    plain = next(case for case in CASES if case.name == "прямий шлях")
    assert not plain.edge, "щасливий шлях порахований крайнім — тоді крайні всі"
    for field in dataclasses.fields(Case):
        if field.name == "acts":
            continue
        current = getattr(plain, field.name)
        moved = dataclasses.replace(plain, **{field.name: "" if isinstance(current, str) else ()})
        assert moved.edge == plain.edge, (
            f"поле {field.name!r} змінює крайність — отже вона оголошується рукою, а не "
            "читається з трейсу"
        )


def check_a_broken_level_reddens_the_check_that_asserts_about_that_level() -> None:
    """FAILURE · зуби: зламаний рівень червонить саме свою перевірку (AC-09)"""
    healthy = levels.path

    def always_passes(case, trajectory):
        return levels.Verdict(PATH, PASSED, DETERMINISTIC, "зламано навмисно")

    levels.path = always_passes
    try:
        try:
            check_same_answer_different_paths_different_verdicts()
        except AssertionError as caught:
            assert "траєкторії" in str(caught), f"перевірка червоніє не про той рівень: {caught}"
        else:
            raise AssertionError(
                "рівень траєкторії зламано, а перевірка лишилась зеленою — вона не має "
                "зубів і не доводить нічого"
            )

        # І дзеркальна половина: перевірки ІНШИХ рівнів від цієї поломки не червоніють.
        check_a_trace_without_steps_of_that_kind_is_not_evaluated()
    finally:
        levels.path = healthy

    # Полагоджено — перевірка знову зелена.
    check_same_answer_different_paths_different_verdicts()


def check_the_report_is_deterministic_across_twenty_runs() -> None:
    """FAILURE · детермінізм: двадцять прогонів дають ті самі вердикти (NFR-6)"""
    from shared.config import settings  # noqa: PLC0415

    if settings.has_real_llm:
        # NFR-6b: із реальним суддею детермінізм не вимагається. Гілка мусить існувати —
        # інакше три сторінки прози обіцяють механізм, якого немає, і перевірка лишається
        # зеленою там, де мала б чесно сказати «не перевіряли».
        raise NotVerified("ключ налаштовано — з реальним суддею детермінізм не вимагається")

    def fingerprint() -> tuple:
        report, _ = _report()
        return tuple(
            (row.case.name, tuple((v.level, v.state, v.kind) for v in row.verdicts))
            for row in report.rows
        ) + tuple(
            (level, state, report.count(level, state)) for level in LEVELS for state in STATES
        )

    first = fingerprint()
    for run in range(1, 20):
        assert fingerprint() == first, f"прогін {run} дав інші вердикти — набір мигтить"

    # Побайтової тотожності НЕ вимагаємо: ідентифікатори й час у порівняння не входять.
    _, text = _report()
    assert "trc_" not in text, "у звіт потрапив ідентифікатор трейсу — файл мигтітиме"


def check_the_modules_fit_the_line_budget() -> None:
    """бюджет: кожен модуль реалізації вкладається у стелю рядків (NFR-1)"""
    for name in IMPLEMENTATION:
        lines = _executable_lines(name)
        assert lines <= LINE_BUDGET, f"{name}: {lines} > {LINE_BUDGET} виконуваних рядків"


def check_the_demo_shows_every_scene_offline_within_its_budget() -> None:
    """e2e · демо: вісім сцен, без ключа й без мережі, у межах часу (NFR-2b)"""
    import io
    import time
    from contextlib import redirect_stdout

    from stages.s08_eval.run import main as demo_main

    buffer = io.StringIO()
    started = time.perf_counter()
    with redirect_stdout(buffer):
        code = demo_main()
    took = time.perf_counter() - started
    output = buffer.getvalue()

    assert code == 0, code
    assert took <= 10, f"демо йшло {took:.1f} с — стеля 10 с (NFR-2b)"
    assert output.startswith("[BiasedJudge]"), output.splitlines()[0]
    for number in range(1, 9):
        assert f"{NEWLINE}{number}. " in output, f"сцена {number} не надрукувалась"

    # Числа сцен мають збігатися з тим, що дає прогін тут, а не бути набраними руками.
    report, _ = _report()
    assert f"{report.share(E2E):.0%}" in output, "частка e2e у виводі не та, що дає прогін"
    assert f"кейсів: {len(CASES)}, крайніх: {sum(1 for c in CASES if c.edge)}" in output, (
        "склад набору у виводі не збігається з набором — підрядковий ассерт цього не ловив: "
        "у виводі десятки цифр, тож перевірка проходила за будь-якої девʼятки"
    )

    # Демо не тягне ані мережі, ані ключа: обидва біаси знайдено підробленим суддею.
    for word in ("ЗНАЙДЕНО", "згода", "position bias", "length bias"):
        assert word in output, f"демо без {word!r} — доказ етапу не показаний"

    source = (HERE / "run.py").read_text(encoding="utf-8")
    for network in ("requests", "httpx", "urlopen"):
        assert network not in source, f"демо тягне мережу ({network})"


def check_the_failure_modes_are_at_least_a_third() -> None:
    """перевірки: режимів відмови не менше третини (NFR-4)"""
    labels = [(check.__doc__ or "").split(NEWLINE)[0] for check in CHECKS]
    failures = [label for label in labels if label.startswith("FAILURE")]
    assert len(failures) * 3 >= len(CHECKS), (
        f"режимів відмови {len(failures)} із {len(CHECKS)} — менше третини"
    )


@dataclass
class _HalfJudge(BiasedJudge):
    """Суддя, що відповідає через раз. Роль: вичерпана квота посеред прогону.

    Потрібен саме він: повна відмова робить знаменник нулем і ховає помилку, з якої
    починається брехливий звіт.
    """

    name: str = "half-fake"

    def score(self, task: str, answer: str, expected: str) -> Scored:
        self.calls += 1
        if self.calls % 2:
            raise Unavailable("квота вичерпана")
        return Scored(super()._points(answer, expected), "через раз")


class _MuteJudge:
    """Суддя, який не може винести жодного вердикта. Роль: відсутній ключ."""

    name = "mute-fake"
    calls = 0

    def compare(self, task, first, second, *, expected=""):
        raise Unavailable("провайдера не налаштовано")

    def score(self, task: str, answer: str, expected: str) -> Scored:
        raise Unavailable("провайдера не налаштовано")


CHECKS = [
    check_one_case_yields_three_verdicts_and_three_evaluator_kinds,
    check_the_written_report_parses_back_to_the_same_totals,
    check_a_case_passes_one_level_and_fails_another_in_the_same_row,
    check_same_answer_different_paths_different_verdicts,
    check_a_failed_step_is_named_by_its_kind_and_ordinal,
    check_a_trace_without_steps_of_that_kind_is_not_evaluated,
    check_deterministic_evaluators_call_the_judge_zero_times,
    check_swapping_the_order_flips_the_winner,
    check_a_stable_judge_yields_zero_flips,
    check_padding_a_correct_answer_raises_its_score,
    check_an_unavailable_judge_yields_not_evaluated_never_a_failure,
    check_the_real_judge_refuses_an_unreadable_verdict,
    check_cheap_checks_cover_every_trajectory_the_judge_only_a_share,
    check_neither_request_nor_answer_text_reaches_the_report_or_the_trace,
    check_the_sampled_share_matches_the_declared_one_within_the_stated_margin,
    check_stage_traces_are_read_exactly_as_the_stages_wrote_them,
    check_the_input_trace_file_is_byte_identical_after_a_run,
    check_one_grouping_key_parameter_serves_both_stage_1_and_the_stage_6_service,
    check_what_the_traces_lack_is_counted_not_assumed,
    check_the_step_order_is_restored_from_the_sequence_number,
    check_at_least_a_third_of_the_case_set_is_edge_by_observation,
    check_a_broken_level_reddens_the_check_that_asserts_about_that_level,
    check_the_report_is_deterministic_across_twenty_runs,
    check_the_modules_fit_the_line_budget,
    check_the_demo_shows_every_scene_offline_within_its_budget,
    check_the_lesson_fits_the_reading_budget,
    check_the_lesson_numbers_match_the_suite,
    check_the_lesson_line_counts_match_the_modules,
    check_the_exercises_match_the_pinned_mutations,
    check_every_reader_file_exists,
    check_the_failure_modes_are_at_least_a_third,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 8 · Evaluation")


if __name__ == "__main__":
    raise SystemExit(main())
