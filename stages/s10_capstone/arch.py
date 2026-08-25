"""Розбір `ARCHITECTURE.md`: кожне рішення має джерело, і джерело існує (ADR-0005).

Бібліографія, якої ніхто не звіряє, — це прикраса. У цьому репозиторії так уже сталося двічі,
і обидва рази знайшло рев'ю, а не автор:

    повідомлення про TRACE_SINK    посилалось на ADR етапу 6, який рішення не ухвалював
    таблиця ADR-0008 етапу 8       суперечила власному блоку вимірів у тому самому файлі

Обидва тексти були правдоподібні, ніхто їх не виконував, і вони старіли мовчки.

Тому тут документ **розбирається кодом**. Стверджуються дві речі:

1. Кожне рішення має етап-джерело або стоїть у розділі власних рішень.
2. Кожен названий етап і кожен названий ADR **існують** у репозиторії.

**Межа названа прямо.** Перевірка каже, що джерело існує, а не що воно містить саме це
рішення. Друге неможливо без розуміння тексту; перше вже ловить увесь клас помилок, які тут
траплялись.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent

DECISIONS = "## Рішення й джерела"
OWN = "## Власні рішення капстоуна"
REVEALED = "## Що складання виявило"

# Рядок таблиці: `| рішення | джерело |`. Джерело — `sNN` і, за потреби, `ADR-NNNN`.
ROW = re.compile(r"^\| (?P<what>[^|]+?) \| (?P<source>[^|]+?) \|$")
SOURCE = re.compile(r"^(?P<stage>s\d{2})(?: · (?P<adr>ADR-\d{4}))?$")


@dataclass(frozen=True)
class Justification:
    """Одне рішення разом із джерелом."""

    what: str
    stage: str
    adr: str = ""


def _section(text: str, title: str) -> str:
    """Тіло розділу до наступного заголовка того ж рівня."""
    if title not in text:
        return ""
    body = text.split(title, 1)[1]
    return body.split("\n## ", 1)[0]


def _rows(body: str) -> list[tuple[str, str]]:
    """Рядки таблиці без заголовка й роздільника."""
    found = []
    for line in body.split("\n"):
        match = ROW.match(line.strip())
        if not match:
            continue
        what, source = match["what"].strip(), match["source"].strip()
        if set(what) <= {"-"} or what in ("Рішення", "Що", "Пункт"):
            continue
        found.append((what, source))
    return found


def justifications(text: str) -> list[Justification]:
    """Рішення з розділу «Рішення й джерела», розібрані на частини."""
    parsed = []
    for what, source in _rows(_section(text, DECISIONS)):
        match = SOURCE.match(source)
        if match is None:
            parsed.append(Justification(what=what, stage="", adr=""))
            continue
        parsed.append(Justification(what=what, stage=match["stage"], adr=match["adr"] or ""))
    return parsed


def stage_folder(stage: str) -> Path | None:
    """Тека етапу за коротким іменем, або `None`, якщо етапу немає."""
    found = sorted((REPO / "stages").glob(f"{stage}_*"))
    return found[0] if found else None


def feature_folder(stage: str) -> Path | None:
    """Тека артефактів етапу в `docs/features/`, або `None`."""
    found = sorted((REPO / "docs" / "features").glob(f"{stage}-*"))
    return found[0] if found else None


def dangling(text: str) -> list[str]:
    """Биті посилання. Порожньо — усі джерела на місці.

    Три різні вади, і кожна названа окремо: джерела немає взагалі, етапу не існує, ADR не
    існує. Злиття їх в одне повідомлення зробило б виправлення грою у вгадування.
    """
    broken = []
    for item in justifications(text):
        if not item.stage:
            broken.append(f"{item.what!r}: джерела не названо")
            continue
        if stage_folder(item.stage) is None:
            broken.append(f"{item.what!r}: етапу {item.stage} не існує")
            continue
        if not item.adr:
            continue
        feature = feature_folder(item.stage)
        number = item.adr.split("-")[1]
        if feature is None or not sorted((feature / "adr").glob(f"{number}-*.md")):
            broken.append(f"{item.what!r}: {item.adr} етапу {item.stage} не існує")
    return broken


def own_decisions(text: str) -> list[tuple[str, str]]:
    """Власні рішення капстоуна: рішення й причина, чому етапу-джерела немає."""
    return _rows(_section(text, OWN))


def revealed(text: str) -> list[str]:
    """Пункти розділу «що складання виявило». Порожньо — найпідозріліший результат."""
    body = _section(text, REVEALED)
    return [line.strip("- ").strip() for line in body.split("\n") if line.strip().startswith("- ")]


def read(path: Path | None = None) -> str:
    return (path or HERE / "ARCHITECTURE.md").read_text(encoding="utf-8")
