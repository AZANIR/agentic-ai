"""Порівняльна таблиця: збирає, рендерить і **розбирає назад** (ADR-0003, ADR-0005).

**Жодного зведеного бала.** Шість колонок і жодного «найкращий». Ваги обмежень — це думка
про те, чиє обмеження важливіше, вбудована в число, яке ніхто не обговорював. Замість цього
висновок має форму «обмеження → інструмент», і кожне правило називає колонку, з якої воно
виведене.

**Таблиця розбирається назад.** `parse()` читає **записаний файл** і рахує заново — щоб
перевірка звіряла два незалежні джерела, а не рахувала суму двічі тим самим кодом. Рівність,
обчислена з одного джерела, — тотожність, і реалізація, що до файлу не доїхала, її пройде.

**Порушник контракту лишається в таблиці — без чисел.** Викинути його мовчки означало б
показати три рядки як усі; полагодити — означало б порівнювати виправлену задачу з іншими.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from stages.s09_frameworks import contract
from stages.s09_frameworks.counters import Tally

HERE = Path(__file__).resolve().parent

UNVERIFIED = "NOT EVALUATED"
NEWLINE = chr(10)

COLUMNS = (
    "реалізація",
    "мої рядки",
    "невидимі рядки",
    "викликів моделі",
    "токени запиту",
    "понад запит",
    "координація",
    "місць прози",
    "чому цей крок",
)

# Іменовані аргументи, значення яких описують ПОВЕДІНКУ прозою, а не кодом. Саме вони й
# роблять координацію неявною: наступний крок вирішує текст, який прочитала модель.
BEHAVIOUR_PROSE = frozenset(
    {"role", "goal", "backstory", "description", "instruction", "expected_output"}
)

ROW = re.compile(r"^\| (?P<cells>.+) \|$")


@dataclass
class Row:
    """Один рядок таблиці. Порушник контракту має причину замість чисел."""

    name: str
    module: str
    mine: int = 0
    invisible: int = 0
    # Кількість викликів моделі — **колонка**, а не обіцянка. Чотири тексти називали її
    # вимірюваною, а в таблиці її не було: реалізація, що пʼять разів шле той самий
    # контрактний промпт, мала `надбавка = 0` і була невідрізнима від ощадливої.
    calls: int = 0
    asked: int = 0
    overhead: int = 0
    coordination: str = ""
    places: int = 0
    why_source: str = ""
    unverified: str = ""
    broken: tuple[str, ...] = field(default_factory=tuple)

    @property
    def counted(self) -> bool:
        """Чи має цей рядок числа. Ні — і саме тому в ньому стоїть причина."""
        return not self.unverified and not self.broken

    def cells(self) -> list[str]:
        # «Місць прози» вимірюється з ДЖЕРЕЛА, тож стоїть навіть у рядка, який не вдалося
        # прогнати: обмеження інтерпретатора не робить код нечитабельним.
        # «Мої рядки» й «місць прози» вимірюються з ДЖЕРЕЛА, тож стоять і в рядка, який
        # не вдалося прогнати: обмеження інтерпретатора не робить код нечитабельним, і
        # прочерк на їхньому місці викинув би єдині чесні числа непригнаної реалізації.
        if self.unverified:
            return [
                self.name,
                str(self.mine),
                UNVERIFIED,
                "—",
                "—",
                "—",
                "—",
                str(self.places),
                self.unverified,
            ]
        if self.broken:
            return [
                self.name,
                str(self.mine),
                "контракт порушено",
                "—",
                "—",
                "—",
                "—",
                str(self.places),
                "; ".join(self.broken),
            ]
        return [
            self.name,
            str(self.mine),
            str(self.invisible),
            str(self.calls),
            str(self.asked),
            str(self.overhead),
            self.coordination,
            str(self.places),
            self.why_source,
        ]


def executable_lines(name: str) -> int:
    """Мої рядки: виконувані, без імпортів і рядків документації.

    Та сама одиниця, що й для невидимих рядків, і той самий спосіб, що на етапі 8 — інакше
    колонки були б у різних одиницях і виглядали б порівнянними.
    """
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


def behaviour_prose(name: str | Path) -> int:
    """Скільки місць прози описують поведінку — ціна відповіді «чому цей крок».

    Міряється з джерела розбором AST, а не оголошується числом: оголошене число було б
    прапорцем, який автор виставляє рукою (той самий урок, що на етапі 8).

    Явна координація дає **нуль**: наступний крок вирішує код, а не текст. Неявна дає
    стільки, скільки описів треба прочитати й уявити, як їх прочитала модель.
    """
    source = name if isinstance(name, Path) else HERE / name
    tree = ast.parse(source.read_text(encoding="utf-8"))
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.keyword)
        and node.arg in BEHAVIOUR_PROSE
        and isinstance(node.value, ast.Constant | ast.JoinedStr | ast.Call | ast.Attribute)
    )


def measured(
    result: contract.Result,
    tally: Tally,
    invisible: set[tuple[str, int]],
    module: str,
) -> Row:
    """Зібрати рядок із виміряного. Контракт звіряється **перед** тим, як з'являються числа."""
    import dataclasses  # noqa: PLC0415

    with_calls = dataclasses.replace(result, model_calls=tally.calls)
    return Row(
        name=result.name,
        module=module,
        mine=executable_lines(module),
        invisible=len(invisible),
        calls=tally.calls,
        asked=tally.asked,
        overhead=tally.overhead,
        coordination=result.coordination,
        places=behaviour_prose(module),
        why_source=result.why_source,
        broken=contract.violations(with_calls),
    )


def skipped(name: str, module: str, reason: str) -> Row:
    """Рядок, який не вдалося порахувати. Причина стоїть у таблиці, а не в голові автора.

    «Місць прози» лишається виміряним: воно читається з коду, а не з прогону, і саме тому
    непригнана реалізація все одно дає один справжній вимір замість суцільних прочерків.
    """
    return Row(
        name=name,
        module=module,
        unverified=reason,
        mine=executable_lines(module),
        places=behaviour_prose(module),
    )


def render(rows: list[Row], rules: list[tuple[str, str, str]]) -> str:
    """Таблиця як текст. Порядок колонок сталий, чисел рівно стільки, скільки виміряно."""
    out = ["# Порівняння · s09", "", f"реалізацій: {len(rows)}", ""]
    out += ["| " + " | ".join(COLUMNS) + " |", "|---" * len(COLUMNS) + "|"]
    out += ["| " + " | ".join(row.cells()) + " |" for row in rows]

    out += ["", "## Правило вибору", ""]
    out.append("Жодного зведеного бала тут немає й бути не може: ваги обмежень — це думка.")
    out.append("")
    out.append("| Якщо твоє обмеження | Бери | Колонка, з якої це видно |")
    out.append("|---|---|---|")
    out += [f"| {when} | {take} | {column} |" for when, take, column in rules]

    if unverified := [row for row in rows if row.unverified]:
        out += ["", "## Чого не виміряно, і чому", ""]
        out += [f"- **{row.name}** — {row.unverified}" for row in unverified]
    if broken := [row for row in rows if row.broken]:
        out += ["", "## Контракт порушено", ""]
        out += [f"- **{row.name}** — {'; '.join(row.broken)}" for row in broken]
    return NEWLINE.join(out) + NEWLINE


def save(rows: list[Row], rules: list[tuple[str, str, str]], path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(rows, rules), encoding="utf-8")
    return target


def parse(text: str) -> dict[str, list[str]]:
    """Прочитати **записану** таблицю: `{реалізація: клітинки}`. Друге джерело для AC-01b.

    Свідомо не використовує жодного об'єкта прогону: якщо рядок реалізації не доїхав до
    файлу, ці числа розійдуться з лічильниками — а саме це й треба спіймати.
    """
    found: dict[str, list[str]] = {}
    for line in text.split(NEWLINE):
        match = ROW.match(line)
        if not match:
            continue
        cells = [cell.strip() for cell in match["cells"].split("|")]
        if len(cells) != len(COLUMNS) or cells[0] in (COLUMNS[0], "Якщо твоє обмеження"):
            continue
        if set(cells[0]) <= {"-"}:
            continue
        found[cells[0]] = cells[1:]
    return found
