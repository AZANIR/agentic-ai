"""Демонстрація етапу 8: вісім сцен підряд.

    python -m stages.s08_eval.run
    python -m stages.s08_eval.run --real    # суддя-модель, якщо ключ налаштовано

Працює **без ключа й без мережі**. Суддя за замовчуванням — підробка з задокументованою
упередженістю: вона грає роль зламаного приладу, щоб детекторові було що виявляти.

Сцени показують свої критерії приймання:

    1. три рівні на одному кейсі                          AC-01, AC-04
    2. та сама відповідь, різні шляхи                     AC-03, AC-03b
    3. звіт: три частки й третій стан                     AC-01b, AC-08
    4. position bias: перестановка міняє вердикт          AC-05
    5. length bias: зайвий текст додає балів              AC-06
    6. дзеркало: стабільний суддя дає згоду               AC-05b
    7. онлайн: дешеві чеки на всьому, суддя на частці     AC-07, AC-07c
    8. чого бракує у трейсі — виміряно                    AC-12

**Головна тут — четверта.** Перші три дають числа; четверта показує, що прилад, який їх
дає, залежить від порядку подачі.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from shared.trace import iter_steps
from stages.s08_eval.bias import LENGTH_PAIRS, POSITION_PAIRS, length_sweep, position_sweep
from stages.s08_eval.cases import CASES, write
from stages.s08_eval.judge import SCALE, SteadyJudge, get_judge
from stages.s08_eval.levels import UNSCORED, evaluate
from stages.s08_eval.online import DEFAULT_SHARE, MIN_STREAM, TOLERANCE, sampled, watch
from stages.s08_eval.report import LEVELS_ORDER, Report, Row, save
from stages.s08_eval.trajectory import by_ref, by_trace_id, extract, survey_run_keys

BANNER = (
    "[BiasedJudge] Суддя підроблений і упереджений НАВМИСНО: він грає роль зламаного "
    "приладу. Це не доказ, що справжні судді упереджені, — це матеріал для детектора."
)

# Довжина синтетичного потоку для виміру частки. Не менша за `MIN_STREAM`: коротший
# потік не відрізняє десять відсотків від нуля.
STREAM = 1_000


def _walk(path: Path, judge) -> Report:
    made = write(path)
    report = Report(judge_name=judge.name)
    for trajectory in extract(path):
        case = made[trajectory.key]
        report.rows.append(Row(case, evaluate(case, trajectory, judge)))
    report.judge_calls = judge.calls
    return report


def scene_levels(report: Report) -> None:
    print("1. Три рівні на одному кейсі")
    row = report.rows[0]
    print(f"   кейс: {row.case.name}")
    for verdict in row.verdicts:
        print(f"   {verdict.level:<12} {verdict.state:<11} ({verdict.kind}) — {verdict.reason}")
    print()
    print("   Вид оцінювача стоїть поруч із вердиктом, а не мається на увазі. Детермінований")
    print("   не кличе суддю жодного разу — це перевіряється лічильником, не читанням коду.")
    print()


def scene_same_answer(report: Report) -> None:
    print("2. Та сама відповідь — різні шляхи")
    wanted = ("прямий шлях", "та сама відповідь через відновлення", "щаслива випадковість")
    for row in report.rows:
        if not row.case.name.startswith(wanted):
            continue
        marks = "  ".join(f"{v.level}: {v.state}" for v in row.verdicts)
        print(f"   {row.case.name[:44]:<46} {marks}")
    print()
    print("   Останнє повідомлення в усіх трьох однакове. Дивлячись лише на нього, ти не")
    print("   відрізниш інженерію від щасливої випадковості — і саме тому рівнів три.")
    print()


def scene_report(report: Report, path: Path) -> None:
    print("3. Звіт — три частки, і знаменник не змінюється")
    print(f"   {'рівень':<12} {'пройд':>6} {'провал':>7} {'не оцін':>8} {'частка':>7}")
    for level in LEVELS_ORDER:
        counts = [report.count(level, s) for s in ("пройдено", "провалено", UNSCORED)]
        share = f"{report.share(level):.0%}"
        print(f"   {level:<12} {counts[0]:>6} {counts[1]:>7} {counts[2]:>8} {share:>7}")
    print()
    print(f"   Знаменник — усі {report.total} кейсів, а не лише оцінені. Частка, порахована")
    print("   від оцінених, РОСТЕ, коли суддя падає: що менше вдалось оцінити, то кращий вигляд.")
    print()
    print(f"   Звіт записано: {path.name}")
    print()


def scene_position(found) -> None:
    print("4. Position bias — перестановка міняє вердикт")
    print(f"   {found.line()}")
    for line in found.detail:
        print(f"      {line}")
    print()
    print("   Пари зважені навмисно: обидві відповіді однаково обґрунтовані й однакові за")
    print("   довжиною. Розрізнити їх може лише порядок подачі — і суддя його розрізняє.")
    print()


def scene_length(found) -> None:
    print("5. Length bias — зайвий текст додає балів")
    print(f"   {found.line()}   (шкала 0..{SCALE})")
    for line in found.detail:
        print(f"      {line}")
    print()
    print("   Обидві відповіді правильні; друга відрізняється лише зайвиною. Тому порогу")
    print("   тут немає й бути не може: БУДЬ-ЯКА перевага довшої — це бал за довжину.")
    print()


def scene_mirror() -> None:
    print("6. Дзеркальна половина — на стабільному судді детектор мовчить")
    steady = SteadyJudge()
    for found in (position_sweep(steady, POSITION_PAIRS), length_sweep(steady, LENGTH_PAIRS)):
        print(f"   {found.line()}")
    print()
    print("   Детектор, що знаходить біас завжди, не відрізняє упередженого суддю від")
    print("   чесного — і тому детектором не є. Без цієї сцени попередні дві нічого не варті.")
    print()


def scene_online(path: Path) -> None:
    print("7. Онлайн — дешеві чеки на всьому, суддя на частці")
    seen = watch(path, key=by_trace_id)
    print(f"   дешеві чеки: перевірено {seen.checked}, зауважень {len(seen.problems)}")
    # Зведення за видом, а не перелік ідентифікаторів. Ідентифікатор траєкторії
    # випадковий, тож перелік мигтів би між прогонами — а звіт, який щоразу інший,
    # неможливо порівняти з учорашнім.
    kinds: dict[str, int] = {}
    for problem in seen.problems:
        kind = problem.split(": ", 1)[-1]
        kinds[kind] = kinds.get(kind, 0) + 1
    for kind, count in sorted(kinds.items()):
        print(f"      {count} x {kind}")
    print()

    # Частка МІРЯЄТЬСЯ на довгому потоці, а не на двадцяти прогонах. Перша редакція цієї
    # сцени рахувала її на двадцяти одному кейсі з випадковими ідентифікаторами — і число
    # мигтіло між прогонами: то нуль у семплі, то пʼять. Двадцять одне спостереження не
    # відрізняє десять відсотків від нуля, і жоден допуск цього не полагодить.
    stream = [f"req_{index:08x}" for index in range(STREAM)]
    hit = sum(sampled(request, share=DEFAULT_SHARE) for request in stream)
    print(f"   семпл на {STREAM} запитах: {hit} до судді = {hit / STREAM:.1%}")
    print(f"   заявлено {DEFAULT_SHARE:.0%}, межа ±{TOLERANCE:.0%}, мінімальний потік {MIN_STREAM}")
    print()
    print("   Відбір детермінований — за хешем ідентифікатора. Той самий потік завжди дає")
    print("   ту саму частку, тож її можна звірити із заявленою, а не повірити їй.")
    print()
    print("   Усе поза смугою: жоден крок оцінювання не стоїть між запитом і відповіддю.")
    print("   Ціна названа — запит, який до трейсера не дійшов, не оцінюється ніяк.")
    print()


def scene_gaps() -> None:
    print("8. Чого бракує у трейсі — виміряно, а не припущено")

    # Читаємо ВСЕ, що лежить у `traces/`, і групуємо за метаполем `stage`, яке пише кожен
    # крок. Перша редакція шукала `traces/s01.jsonl` — назви, якої `shared.trace` не
    # створює ніколи (там `traces/<дата>.jsonl`), тож обидві гілки друкували «трейсу
    # немає», а відповідь на AC-12 стояла нижче сталою прозою. Демо не має друкувати
    # числа, якого не отримало.
    seen_any = False
    for path in sorted(Path("traces").glob("*.jsonl")):
        stages = sorted({step.get("stage") for step in iter_steps(path)} - {None})
        # Один рядок на ФАЙЛ, а не на етап у ньому. Числа траєкторій і зауважень
        # файлові, і друкувати їх окремо під кожним етапом означало б показати те саме
        # число тричі так, ніби це три різні виміри.
        key = by_ref if "s06" in stages else by_trace_id
        seen = watch(path, key=key)
        if not seen.checked:
            continue
        seen_any = True
        print(
            f"   {path.name} ({', '.join(stages) or 'без мітки етапу'}): "
            f"траєкторій {seen.checked}, зауважень {len(seen.problems)}"
        )
        for blind in seen.blind:
            print(f"      сліпе: {blind}")
    if not seen_any:
        print("   у traces/ порожньо — прогони будь-який етап і повтори")
    print()

    # Головне число сцени — теж вимір, а не проза (AC-12).
    found = survey_run_keys(Path("stages"))
    named = sorted({field for field in found.values() if field})
    blind = sorted(stage for stage, field in found.items() if field is None)
    print(f"   ключем прогону слугують {len(named)} різні поля: {', '.join(named)}")
    print(f"   {len(blind)} етапи не позначають прогін ніяк: {', '.join(blind)}")
    print()
    print("   Етап 4 має `phase`, але це фаза ВІДМОВИ: на щасливому шляху вона None, тож")
    print("   ключем прогону бути не може. Це і є відповідь на питання, яке етап 6 двічі")
    print("   відклав сюди (ADR-0008).")
    print()


def main(*, real: bool = False, report_path: Path | None = None) -> int:
    from shared.config import settings  # noqa: PLC0415

    judge = get_judge(real=real)
    if not real:
        print(BANNER)
    elif settings.has_real_llm:
        print(f"[{judge.name}] Суддя справжній: числа мигтітимуть.")
    else:
        # Банер за прапорцем брехав: без ключа сцени 4 і 5 друкували НЕ ОЦІНЕНО, звіт —
        # «прогін не є успішним», а перший рядок обіцяв справжню модель.
        print(f"[{judge.name}] Просили справжнього суддю, але провайдера не налаштовано.")
        print("   Усе, що потребує судження, буде НЕ ОЦІНЕНО. Прибери --real або дай ключ.")
    print(f"   кейсів: {len(CASES)}, крайніх: {sum(1 for c in CASES if c.edge)}")
    print()

    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "cases.jsonl"
        report = _walk(traces, judge)
        # Свіпи проганяються ОДИН раз і передаються у сцени. Перша редакція рахувала їх
        # двічі — для звіту й для сцен, — тож суддя робив 41 виклик, а звіт друкував 21.
        # З --real це двадцять зайвих оплачених викликів на кожен прогін демо.
        position = position_sweep(judge, POSITION_PAIRS)
        length = length_sweep(judge, LENGTH_PAIRS)
        report.findings = [position, length]
        report.judge_calls = judge.calls
        target = save(report, report_path or Path(tmp) / "report.md")

        scene_levels(report)
        scene_same_answer(report)
        scene_report(report, target)
        scene_position(position)
        scene_length(length)
        scene_mirror()
        scene_online(traces)
    scene_gaps()

    if report_path is None:
        print("Щоб лишити звіт на диску:")
        print(
            '    python -c "from pathlib import Path;'
            " from stages.s08_eval.run import main;"
            " main(report_path=Path('report.md'))\""
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(real="--real" in sys.argv))
