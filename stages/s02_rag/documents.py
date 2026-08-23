"""Читання бази знань: файли, метадані, рівень доступу.

Окремо від пошуку навмисно. Це дві різні відповідальності: тут — розібрати файл і
зрозуміти, кому його можна показувати; там — порахувати близькість і відсортувати.
Спільного між ними рівно нічого, крім того, що перше годує друге.

SAD §11 передбачав, що ліміт рядків упреться, і пропонував винести **фільтр доступу**.
Коли код був написаний, стало видно, що це нашкодило б: фільтр — чотири рядки, і вся
суть ADR етапу 0002 у тому, що вони стоять усередині пошуку, до відбору. Винести їх
означало б сховати саме те, що має бути на видноті. Тому винесено завантаження.

Формат метаданих навмисно примітивний — кілька рядків `ключ: значення` між лініями з
трьох дефісів. Повноцінний YAML тут був би залежністю заради двох полів.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PUBLIC = "public"
INTERNAL = "internal"

KB_DIR = Path(__file__).parent / "data" / "kb"

# Якір кінця тут не потрібен: із re.S крапка вже поглинає все до кінця файлу.
# Попередня версія мала екранований долар замість якоря — тобто шукала літеральний
# символ, ніколи не збігалася, і кожен документ мовчки ставав публічним. Перевірка
# фільтра доступу впала одразу; без неї це поїхало б як повний витік внутрішніх документів.
_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.S)


@dataclass(frozen=True)
class Document:
    """Документ бази знань разом із рівнем доступу."""

    name: str
    title: str
    access: str
    body: str


def load_documents(directory: Path | None = None) -> list[Document]:
    """Прочитати базу знань. Метадані — у простому frontmatter на початку файлу."""
    documents = []
    for path in sorted((directory or KB_DIR).glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        match = _FRONTMATTER.match(raw)
        meta, body = (match.group(1), match.group(2)) if match else ("", raw)
        fields = dict(line.split(":", 1) for line in meta.splitlines() if ":" in line)
        documents.append(
            Document(
                name=path.stem,
                title=fields.get("title", path.stem).strip(),
                access=fields.get("access", PUBLIC).strip(),
                body=body,
            )
        )
    return documents
