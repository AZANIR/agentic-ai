"""Демонстрація етапу 10: сім сцен підряд.

    python -m stages.s10_capstone.run

Працює **без ключа й без мережі** — правило, яке трималось дев'ять етапів, і зламати його
найлегше саме на десятому.

Сцени показують свої критерії приймання:

    1. пʼять сценаріїв: гілка І фінальний стан           AC-05, AC-11
    2. хто працював на кожному запиті                    AC-01
    3. скільки рядків кожного етапу виконалось           AC-02, AC-02b
    4. ціна складання: перехідники проти виконаного      AC-03, AC-03b
    5. шви: що з чим не зійшлося й чому                  AC-04
    6. оцінювач етапу 8 судить капстоун                  AC-09
    7. обґрунтування: кожне рішення має джерело          AC-06, AC-10

**Головна тут — третя.** Решта показують, що зібралось; третя показує, **скільки з кожного
етапу справді працює** — і саме там ховається різниця між «імпортує» й «використовує».
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from shared.llm import banner
from shared.trace import trace_run
from stages.s10_capstone import arch, assemble, scenarios, seams


def _judge(traces: Path) -> tuple[int, list[str]]:
    """Оцінювач етапу 8 читає трейси капстоуна — без жодної зміни в собі (AC-09)."""
    from stages.s08_eval.trajectory import extract  # noqa: PLC0415

    walked = extract(traces, key=lambda step: step.get("case"))
    return len(walked), [trajectory.key for trajectory in walked]


def measured(service: Any, traces: Path) -> assemble.Assembly:
    """Вимір складання на всіх пʼятьох сценаріях плюс оцінювання.

    Одна функція на демо й на перевірку. Два різні замикання дали б два різні числа —
    і перевірка «числа демо збігаються з виміром» порівнювала б два виміри, а не число
    з його джерелом.
    """
    return assemble.measure(
        lambda: (
            [
                service.ask(scenarios.KEY, item.question, now=scenarios.NOW)
                for item in scenarios.SCENARIOS
            ]
            + [_judge(traces)]
        )
    )


def scene_scenarios(outcomes: list[scenarios.Outcome]) -> None:
    print("1. Пʼять сценаріїв — гілка І фінальний стан")
    for outcome in outcomes:
        mark = "OK" if not outcome.mismatch else "НІ"
        print(f"   {mark}  {outcome.scenario.name:<34} гілка={outcome.branch or '—':<7}")
        for wrong in outcome.mismatch:
            print(f"       {wrong}")
    print()
    print("   Звіряється не відповідь, а гілка, склад частин і те, що лишилось у памʼяті.")
    print("   Курс двічі ловив правильний текст, отриманий хибним шляхом.")
    print()


def scene_parts(outcomes: list[scenarios.Outcome]) -> None:
    print("2. Хто працював на кожному запиті")
    for outcome in outcomes:
        parts = ", ".join(outcome.parts) or "—"
        print(f"   {outcome.scenario.name:<34} {parts}")
    print()
    print("   Без цього «сервіс відповів» не відрізняється від «одна частина відповіла за всіх».")
    print()


def scene_executed(got: assemble.Assembly) -> None:
    print("3. Скільки рядків кожного етапу ВИКОНАЛОСЬ")
    for name in assemble.PARTS:
        count = got.executed.get(name, 0)
        mark = "" if count else "   <- жодного рядка"
        print(f"   {name}: {count:>4}{mark}")
    for name, why in assemble.NOT_WIRED.items():
        print(f"   {name}:    —  свідомо не ввімкнено: {why}")
    print()
    print("   Етап 6 імпортує етап 2 і виконує з нього НУЛЬ рядків: `PUBLIC` — константа,")
    print("   яка їде далі як аргумент. Перелік імпортів цього не показує, а ця таблиця —")
    print("   одразу. «Імпортує» — не те саме, що «використовує».")
    print()


def scene_price(got: assemble.Assembly) -> None:
    print("4. Ціна складання")
    print(f"   виконано рядків етапів: {got.worked}")
    print(f"   рядків перехідників:    {got.adapters}  ({got.ratio:.0%})")
    print()
    print("   Межа жанру — пʼята частина. Капстоун, чиї перехідники важать як частини, уже")
    print("   не збирає, а переписує, і теза «частини були зрілі» стає недоказовою.")
    print()


def scene_seams() -> None:
    print("5. Шви — що з чим не зійшлося")
    for seam in seams.SEAMS:
        print(f"   {seam.name:<32} {' + '.join(seam.between)}")
        print(f"      {seam.why}")
    print()
    print("   Кожна невідповідність пішла в перехідник, жодна — в частину. Правка в етапі")
    print("   була б дешевшою тут і дорожчою скрізь: урок, перевірки, тег, стаття.")
    print()


def scene_evaluated(found: int, keys: list[str]) -> None:
    print("6. Оцінювач етапу 8 судить капстоун")
    print(f"   траєкторій витягнуто: {found}")
    print(f"   ключі прогонів: {', '.join(sorted(set(keys))[:4])}")
    print()
    print("   Інструмент, зроблений на етапі 8, працює на системі, якої тоді не існувало, —")
    print("   і без жодної зміни в собі. Ключ прогону в трейсі стоїть із першого рядка.")
    print()


def scene_justified(text: str) -> None:
    print("7. Обґрунтування — кожне рішення має джерело")
    print(f"   рішень із джерелом: {len(arch.justifications(text))}")
    print(f"   битих посилань:     {len(arch.dangling(text))}")
    print(f"   власних рішень:     {len(arch.own_decisions(text))}")
    print(f"   пунктів «що складання виявило»: {len(arch.revealed(text))}")
    print()
    print("   Посилання звіряються з репозиторієм: етап існує, ADR існує. Двічі в цьому")
    print("   репозиторії документ посилався в нікуди й старів мовчки, поки його не почали")
    print("   виконувати.")
    print()


def main(*, base: Any = None) -> int:
    print(banner(None))
    print("   Дев'ять етапів зібрано в один сервіс. Міряється саме складання.")
    print()

    prepared = base or seams.build_search()
    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "s10.jsonl"
        with trace_run("capstone", path=traces, stage="s10", case="demo") as tracer:
            outcomes = scenarios.play_all(Path(tmp), tracer, base=prepared)

        # Вимір іде окремим прогоном: трасування дороге, і вмикати його на демо цілком
        # означало б міряти ще й друк.
        with trace_run("measure", path=traces, stage="s10", case="measure") as tracer:
            got = measured(scenarios.build(Path(tmp), tracer, base=prepared), traces)
        found, keys = _judge(traces)

    text = arch.read()
    scene_scenarios(outcomes)
    scene_parts(outcomes)
    scene_executed(got)
    scene_price(got)
    scene_seams()
    scene_evaluated(found, keys)
    scene_justified(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
