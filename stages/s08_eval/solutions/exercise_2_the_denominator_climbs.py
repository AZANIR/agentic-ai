"""Що робить знаменник «від оцінених», коли суддя падає — на двох режимах відмови.

    python -m stages.s08_eval.solutions.exercise_2_the_denominator_climbs

Червона перевірка вправи 2 каже «знаменник узято від оцінених». Вона не показує **напрямок**,
у який тягне помилка, — і напрямків тут виявляється два, залежно від того, ЯК саме суддя
падає. Обидва погані, і другий гірший.

Агент не змінюється **жодного разу**: ті самі двадцять один кейс, ті самі вердикти там, де
вердикт узагалі є. Змінюється лише прилад.

**Режим 1 — квота вичерпалась.** Відмови рівномірні: суддя не розбирає, що саме не встиг
оцінити. Чесна частка падає — оцінити вдалося менше. Улеслива **стоїть на місці**, і в цьому
вся підступність: число виглядає незмінним, поки покриття валиться з двадцяти одного кейса до
трьох. Це брехня мовчанням, а не перебільшенням.

**Режим 2 — відмови корельовані.** Суддя спотикається саме на безладних відповідях: порожня
відповідь, обрізаний текст, нерозбірлива видача. Це не гіпотеза, а найчастіший спосіб
зламатись: короткий чи порожній зміст дає запит, який провайдер відхиляє. Тепер із набору
випадають переважно **провальні** кейси, і улеслива частка справді **росте** — тим вище, чим
гірше все насправді.

Перший режим знаходять, коли хтось питає «а скільки ми взагалі оцінили». Другий не знаходять
ніколи: він показує зростання якості.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from stages.s08_eval.cases import write
from stages.s08_eval.judge import BiasedJudge, Scored, Unavailable
from stages.s08_eval.levels import E2E, PASSED, UNSCORED, evaluate
from stages.s08_eval.report import Report, Row
from stages.s08_eval.trajectory import extract

# Скільки викликів із десяти суддя переживає. Не випадковість: та сама послідовність
# кейсів має давати ту саму таблицю, інакше її неможливо порівняти з учорашньою.
QUOTA_STEPS = (10, 8, 5, 3, 1)

# Довжина відповіді, нижче якої корельований суддя відмовляється. Росте — і разом із нею
# росте частка того, що з набору випадає.
FRAGILE_STEPS = (0, 20, 30, 40)


class QuotaJudge(BiasedJudge):
    """Режим 1: квота. `alive` викликів із десяти доходять до вердикта."""

    def __init__(self, alive: int) -> None:
        super().__init__(name=f"quota-{alive}")
        self.alive = alive

    def score(self, task: str, answer: str, expected: str) -> Scored:
        self.calls += 1
        if (self.calls - 1) % 10 >= self.alive:
            raise Unavailable("квота вичерпана")
        return Scored(self._points(answer, expected), "у межах квоти")


class FragileJudge(BiasedJudge):
    """Режим 2: суддя спотикається на коротких і безладних відповідях."""

    def __init__(self, floor: int) -> None:
        super().__init__(name=f"fragile-{floor}")
        self.floor = floor

    def score(self, task: str, answer: str, expected: str) -> Scored:
        self.calls += 1
        if len(answer.strip()) < self.floor:
            raise Unavailable("відповідь надто коротка — провайдер відхилив запит")
        return Scored(self._points(answer, expected), "розбірлива відповідь")


@dataclass
class Line:
    label: str
    total: int
    passed: int
    unscored: int

    @property
    def evaluated(self) -> int:
        return self.total - self.unscored

    @property
    def honest(self) -> float:
        """Знаменник — усі кейси. Так рахує `report.share`."""
        return self.passed / self.total

    @property
    def flattering(self) -> float:
        """Знаменник — лише оцінені. Так рахувала б мутація вправи 2."""
        return self.passed / self.evaluated if self.evaluated else 0.0


def measure(judge, label: str) -> Line:
    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "cases.jsonl"
        made = write(traces)
        report = Report(judge_name=judge.name)
        for trajectory in extract(traces):
            case = made[trajectory.key]
            report.rows.append(Row(case, evaluate(case, trajectory, judge)))
    return Line(
        label=label,
        total=report.total,
        passed=report.count(E2E, PASSED),
        unscored=report.count(E2E, UNSCORED),
    )


def _table(title: str, lines: list[Line], moral: list[str]) -> None:
    print(title)
    print(f"   {'':>10} {'оцінено':>8} {'пройшло':>8} {'чесна':>7} {'улеслива':>9}")
    for line in lines:
        print(
            f"   {line.label:>10} {line.evaluated:>8} {line.passed:>8} "
            f"{line.honest:>7.0%} {line.flattering:>9.0%}"
        )
    print()
    for row in moral:
        print(f"   {row}")
    print()


def main() -> int:
    print("Той самий агент, той самий набір. Змінюється лише прилад.")
    print()

    quota = [measure(QuotaJudge(alive), f"{alive * 10}%") for alive in QUOTA_STEPS]
    # Останній рядок рахується на трьох кейсах — це вже шум, а не вимір, тож смуга
    # стабільності береться по рядках, де ще є що міряти.
    steady = quota[:-1]
    band = max(line.flattering for line in steady) - min(line.flattering for line in steady)
    _table(
        "Режим 1 · квота вичерпалась — відмови рівномірні",
        quota,
        [
            f"Чесна впала з {quota[0].honest:.0%} до {quota[-1].honest:.0%}. Улеслива "
            f"трималась у смузі {band:.0%}, поки покриття",
            f"валилося з {steady[0].evaluated} кейсів до {steady[-1].evaluated}; на "
            f"{quota[-1].evaluated} кейсах вона вже шум, а не вимір.",
            "Число не збрехало — воно промовчало саме про те, що робить його осмисленим.",
        ],
    )

    fragile = [measure(FragileJudge(floor), f"<{floor}") for floor in FRAGILE_STEPS]
    _table(
        "Режим 2 · суддя спотикається на безладних відповідях — відмови корельовані",
        fragile,
        [
            "Тепер із набору випадають переважно провальні кейси, і улеслива піднялась з "
            f"{fragile[0].flattering:.0%}",
            f"до {fragile[-1].flattering:.0%} — при чесній {fragile[-1].honest:.0%} і "
            f"{fragile[-1].evaluated} оцінених кейсах із {fragile[-1].total}.",
            "Прилад зламався, а звіт показав ідеальну якість. Цю помилку не шукають:",
            "вона приходить із доброю новиною.",
        ],
    )

    print("   Знаменник — усі кейси, а «не оцінено» стоїть окремою колонкою. Читач має")
    print("   бачити, СКІЛЬКИ зважено, поруч із тим, скільки пройшло: перше число робить")
    print("   друге читабельним, і без нього друге не означає нічого.")

    # Дзеркальна половина: за повного мовчання судді обидві формули дають нуль. Саме тому
    # перевірка набору подає суддю, що відповідає ЧЕРЕЗ РАЗ, а не мовчить зовсім: помилка
    # ховається рівно на тому прогоні, з якого її найприродніше починати шукати.
    mute = measure(QuotaJudge(0), "0%")
    assert mute.honest == mute.flattering == 0.0, mute
    assert fragile[-1].flattering > fragile[0].flattering, fragile
    assert quota[-1].honest < quota[0].honest, quota
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
