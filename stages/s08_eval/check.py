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
import tempfile
from contextlib import contextmanager
from pathlib import Path

from shared.check_runner import run_checks
from shared.trace import trace_run
from stages.s08_eval import levels
from stages.s08_eval.bias import (
    LENGTH_PAIRS,
    POSITION_PAIRS,
    length_sweep,
    position_sweep,
)
from stages.s08_eval.cases import CASES, Case, write
from stages.s08_eval.judge import (
    SCALE,
    BiasedJudge,
    Scored,
    SteadyJudge,
    Unavailable,
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
from stages.s08_eval.trajectory import by_ref, by_trace_id, extract

HERE = Path(__file__).resolve().parent

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
    """ВІДМОВА · звіт: розібраний файл дає ті самі числа, що й лічильники (AC-01b)"""
    report, text = _report()

    counted = parse(text)
    for level in LEVELS:
        for state in STATES:
            assert counted[level][state] == report.count(level, state), (
                f"{level}/{state}: у файлі {counted[level][state]}, "
                f"у лічильниках {report.count(level, state)}"
            )

    # Знаменник — усі кейси. Прогін, у якому суддя не дав жодного бала, не має показати
    # частку **вищу** за той самий прогін із працездатним суддею.
    fallen, _ = _report(judge=_MuteJudge())
    assert fallen.total == report.total, "кількість рядків залежить від судді"
    assert fallen.share(E2E) <= report.share(E2E), (
        f"частка виросла з {report.share(E2E):.0%} до {fallen.share(E2E):.0%}, коли суддя "
        "перестав відповідати — знаменник рахується від оцінених, а має від усіх"
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
    assert lucky.by_level(PATH).state == FAILED, (
        "щаслива випадковість пройшла рівень траєкторії — оцінювач не відрізняє "
        "інженерію від того, що просто зійшлося"
    )


def check_a_failed_step_is_named_by_its_kind_and_ordinal() -> None:
    """ВІДМОВА · компонент: названо крок — його вид і номер, а не лише кейс (AC-03c)"""
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
    """ВІДМОВА · компонент: кроків немає — «не оцінено», а не «пройдено» (AC-03d)"""
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

        judged = levels.e2e(case, judge)
        assert judged.kind == JUDGED and judge.calls == 1, (judged, judge.calls)

    # Сумарна звірка: викликів рівно стільки, скільки оцінювачів, що судять.
    report, _ = _report()
    judging = sum(1 for row in report.rows for verdict in row.verdicts if verdict.kind == JUDGED)
    assert report.judge_calls == judging, (
        f"викликів {report.judge_calls}, оцінювачів, що судять — {judging}. Суддю кличуть "
        "про всяк випадок"
    )


# --- біас судді --------------------------------------------------------------------------


def check_swapping_the_order_flips_the_winner() -> None:
    """ВІДМОВА · position bias: перестановка міняє вердикт (AC-05)"""
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
    """ВІДМОВА · length bias: зайвий текст додає балів без виграшу в змісті (AC-06)"""
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
    """ВІДМОВА · третій стан: недоступний суддя дає «не оцінено» (AC-08)"""
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
        assert 0 < seen.judged < seen.checked, (
            f"суддя бачив {seen.judged} із {seen.checked}: або нікого, або всіх — тоді "
            "частка не є часткою"
        )
        assert seen.judged == judge.calls, (seen.judged, judge.calls)
        assert seen.problems, "жодного зауваження на наборі, де третина кейсів крайні"

        # Обидва числа названі в одному рядку — інакше «на частці» лишається обіцянкою.
        line = seen.line()
        assert str(seen.checked) in line and str(seen.judged) in line, line

    # Поза смугою: `watch` лише читає. Ані `trace_run`, ані запису в модулі немає.
    source = (HERE / "online.py").read_text(encoding="utf-8")
    for written in ("trace_run", "write_text", "open("):
        assert written not in source, (
            f"онлайн-модуль пише ({written}) — оцінювання стало доданком до відповіді"
        )


def check_neither_request_nor_answer_text_reaches_the_report_or_the_trace() -> None:
    """ВІДМОВА · приватність: тексту запиту й відповіді немає в матеріалах (AC-07b)"""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "service.jsonl"
        _service_trace(path, secret=True)

        judge = BiasedJudge()
        seen = watch(path, key=by_ref, judge=judge, share=1.0)
        assert seen.checked == 3, seen.checked

        materials = NEWLINE.join([seen.line(), *seen.problems, *seen.blind])
        for text in (SECRET_ASK, SECRET_REPLY, "Hunter2Zaporizhzhia"):
            assert text not in materials, (
                f"текст користувача {text[:24]!r} потрапив у матеріали оцінювання"
            )

        # Судді подають сталий підпис, а не питання людини.
        assert "запит користувача" in watch.__doc__, "стала підпису не названа в контракті"

    # Дзеркальна половина: фікстури демонстрації біасу під заборону НЕ підпадають —
    # без них демонстрація показувала б самі лише довжини.
    report, _ = _report()
    report.findings = [length_sweep(BiasedJudge(), LENGTH_PAIRS)]
    assert any(pair.task in render(report) for pair in LENGTH_PAIRS), (
        "заборона на текст користувача вимела й фікстури автора — знахідка стала числом "
        "без прикладу"
    )


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
        for stage in range(1, 8):
            assert f"stages.s0{stage}_" not in source, (
                f"{name} імпортує етап {stage} — етап, який довелося б інструментувати "
                "заради оцінювання, довів би, що трасування додали запізно (C-2)"
            )

    # Читання йде крізь спільний `shared.trace`, а не крізь власний розбір JSON.
    reader = (HERE / "trajectory.py").read_text(encoding="utf-8")
    assert "from shared.trace import iter_steps" in reader, (
        "траєкторії читаються не спільним читачем — власний розбір переживе зміну формату мовчки"
    )
    assert "json.loads" not in reader, "модуль розбирає рядки сам, повз shared.trace"


def check_the_input_trace_file_is_byte_identical_after_a_run() -> None:
    """ВІДМОВА · оцінювання читає й не пише в те, що оцінює (AC-02b)"""
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
        f"крайність стала полем кейса ({stored & {chr(101) + 'dge'}}) — набір із двадцяти "
        "щасливих шляхів лишиться зеленим, бо прапорець можна виставити"
    )
    assert isinstance(Case.edge, property), "крайність не обчислюється, а зберігається"

    # Дзеркальна половина: кейс без жодної спостережної ознаки крайнім не рахується.
    plain = next(case for case in CASES if case.name == "прямий шлях")
    assert not plain.edge, "щасливий шлях порахований крайнім — тоді крайні всі"


def check_a_broken_level_reddens_the_check_that_asserts_about_that_level() -> None:
    """ВІДМОВА · зуби: зламаний рівень червонить саме свою перевірку (AC-09)"""
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
    """ВІДМОВА · детермінізм: двадцять прогонів дають ті самі вердикти (NFR-6)"""

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
    assert str(len(CASES)) in output and str(sum(1 for c in CASES if c.edge)) in output, (
        "склад набору у виводі не збігається з набором"
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
    failures = [label for label in labels if label.startswith("ВІДМОВА")]
    assert len(failures) * 3 >= len(CHECKS), (
        f"режимів відмови {len(failures)} із {len(CHECKS)} — менше третини"
    )


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
    check_cheap_checks_cover_every_trajectory_the_judge_only_a_share,
    check_neither_request_nor_answer_text_reaches_the_report_or_the_trace,
    check_the_sampled_share_matches_the_declared_one_within_the_stated_margin,
    check_stage_traces_are_read_exactly_as_the_stages_wrote_them,
    check_the_input_trace_file_is_byte_identical_after_a_run,
    check_one_grouping_key_parameter_serves_both_stage_1_and_the_stage_6_service,
    check_what_the_traces_lack_is_counted_not_assumed,
    check_at_least_a_third_of_the_case_set_is_edge_by_observation,
    check_a_broken_level_reddens_the_check_that_asserts_about_that_level,
    check_the_report_is_deterministic_across_twenty_runs,
    check_the_modules_fit_the_line_budget,
    check_the_demo_shows_every_scene_offline_within_its_budget,
    check_the_failure_modes_are_at_least_a_third,
]


def main() -> int:
    return run_checks(CHECKS, title="Етап 8 · Evaluation")


if __name__ == "__main__":
    raise SystemExit(main())
