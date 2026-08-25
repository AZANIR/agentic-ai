"""Звіт: рядки, підсумки й третій стан. Файл, який читає людина (ADR-0003, ADR-0006).

**Жодного зведеного бала.** Три рівні — три частки. Зважена сума вимагала б ваг, а будь-які
ваги — це прихована думка про те, який рівень важливіший, вбудована в число.

**Знаменник — усі кейси.** Частка пройдених, порахована від **оцінених**, росте, коли суддя
падає: що менше вдалося оцінити, то кращий вигляд. Тому «не оцінено» стоїть окремою
колонкою, а ділиться на все.

**Звіт розбирається назад.** `parse()` читає **записаний файл** і рахує заново — щоб
перевірка звіряла два незалежні джерела, а не рахувала суму двічі тим самим кодом. Рівність,
обчислена з одного джерела, — тотожність, і кейс, який до звіту не доїхав, вона пропустить.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from stages.s08_eval.bias import Finding
from stages.s08_eval.cases import Case
from stages.s08_eval.levels import COMPONENT, E2E, FAILED, PASSED, PATH, UNSCORED, Verdict

LEVELS = (E2E, PATH, COMPONENT)
LEVELS_ORDER = LEVELS  # імʼя для читачів ззовні: порядок колонок сталий
STATES = (PASSED, FAILED, UNSCORED)

ROW = re.compile(r"^\| (?P<case>[^|]+?) \| (?P<cells>.+) \|$")


@dataclass(frozen=True)
class Row:
    case: Case
    verdicts: list[Verdict]

    def by_level(self, level: str) -> Verdict:
        return next(v for v in self.verdicts if v.level == level)


@dataclass
class Report:
    rows: list[Row] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    judge_calls: int = 0
    judge_name: str = ""

    @property
    def total(self) -> int:
        return len(self.rows)

    def count(self, level: str, state: str) -> int:
        return sum(1 for row in self.rows if row.by_level(level).state == state)

    def share(self, level: str, state: str = PASSED) -> float:
        """Частка **від усіх** кейсів. Знаменник не змінюється, коли суддя падає."""
        return self.count(level, state) / self.total if self.total else 0.0

    def evaluated_nothing(self) -> bool:
        """Усе в третьому стані — це не успіх, і звіт має сказати це прямо (AC-08)."""
        return self.total > 0 and all(
            row.by_level(level).state == UNSCORED for row in self.rows for level in LEVELS
        )


def render(report: Report) -> str:
    """Звіт як текст. Порядок сталий, чисел рівно стільки, скільки виміряно."""
    out = ["# Звіт оцінювання · s08", "", f"кейсів: {report.total}", ""]
    out += ["| кейс | " + " | ".join(LEVELS) + " |", "|---|" + "---|" * len(LEVELS)]
    for row in report.rows:
        cells = [f"{row.by_level(level).state} ({row.by_level(level).kind})" for level in LEVELS]
        out.append(f"| {row.case.name} | " + " | ".join(cells) + " |")

    out += ["", "## Підсумки", ""]
    out.append("| рівень | пройдено | провалено | не оцінено | частка пройдених |")
    out.append("|---|---|---|---|---|")
    for level in LEVELS:
        counts = [report.count(level, state) for state in STATES]
        out.append(
            f"| {level} | " + " | ".join(map(str, counts)) + f" | {report.share(level):.0%} |"
        )

    out += ["", f"викликів судді: {report.judge_calls} (суддя: {report.judge_name})", ""]
    if report.evaluated_nothing():
        out.append("**ПРОГІН НЕ Є УСПІШНИМ: не оцінено нічого.** Порожня зелень — не результат.")
        out.append("")
    if report.findings:
        out += ["## Знахідки про суддю", ""]
        out += [f"- {finding.line()}" for finding in report.findings]
        out += [f"  - {line}" for finding in report.findings for line in finding.detail]
        out.append("")
    failures = [
        (row.case.name, verdict)
        for row in report.rows
        for verdict in row.verdicts
        if verdict.state != PASSED
    ]
    if failures:
        out += ["## Що саме не так", ""]
        out += [f"- **{name}** · {v.level}: {v.state} — {v.reason}" for name, v in failures]
    return "\n".join(out) + "\n"


def save(report: Report, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(report), encoding="utf-8")
    return target


def parse(text: str) -> dict[str, dict[str, int]]:
    """Порахувати вердикти, **читаючи звіт**. Друге джерело для AC-01b.

    Свідомо не використовує жодного обʼєкта прогону: якщо рядок кейса не доїхав до файлу,
    ці числа розійдуться з лічильниками — а саме це й треба спіймати.
    """
    counted = {level: dict.fromkeys(STATES, 0) for level in LEVELS}
    for line in text.split("\n"):
        found = ROW.match(line)
        if not found or found["case"].strip() in {"кейс", "рівень"}:
            continue
        cells = [cell.strip() for cell in found["cells"].split("|")]
        if len(cells) != len(LEVELS):
            continue
        for level, cell in zip(LEVELS, cells, strict=True):
            state = cell.split(" (")[0]
            if state in counted[level]:
                counted[level][state] += 1
    return counted
