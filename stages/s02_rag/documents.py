"""Читання бази знань: файли, метадані, рівень доступу.

Окремо від пошуку навмисно. Це дві різні відповідальності: тут — розібрати файл і
зрозуміти, кому його можна показувати; там — порахувати близькість і відсортувати.
Спільного між ними рівно нічого, крім того, що перше годує друге.

Формат метаданих навмисно примітивний — кілька рядків `ключ: значення` між лініями з
трьох дефісів. Повноцінний YAML тут був би залежністю заради двох полів.

**Розбір метаданих fail-closed, і це головне рішення модуля.** Документ, у якому рівень
доступу не вдалося прочитати впевнено, стає `internal`, а не `public`. Причина та сама, що
у валідаторі етапу 1: зворотний дефолт означав би, що захист працює лише поки автор
документа нічого не наплутав.

Наплутати тут легко, і кожен зі способів мовчазний:

    ---            без закривальної лінії весь frontmatter їде в тіло
    BOM            невидимий байт на початку — і відкривальна лінія вже не перша
    acces:         одна літера в ключі
     access:       відступ
    Access:        інший регістр
    access: pubic  друкарська помилка у значенні

Жоден із них не схожий на помилку на око. Усі шість перевіряються, і всі шість дають
`internal`. Втратити доступ до документа помітно одразу; віддати внутрішній документ
покупцю непомітно ніколи.

Історія цього модуля пояснює, чому перевірок тут стільки. Перша версія регулярки шукала
літеральний знак долара замість якоря, ніколи не збігалась — і кожен документ мовчки ставав
публічним. Друга версія полагодила регулярку й лишила дефолт `public`, тобто ту саму ваду
іншим шляхом. Знайшло її незалежне рев'ю, не автор.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PUBLIC = "public"
INTERNAL = "internal"
LEVELS = frozenset({PUBLIC, INTERNAL})

# Сентинел «без фільтра». Названий рядок, а не None: None — це рівно те значення, яке
# дає будь-яка нерозв'язана резолюція «хто питає», і збіг «доступ невідомий» із
# «доступ повний» — це не зручність, а відкриті двері.
NO_FILTER = "__all__"

KB_DIR = Path(__file__).parent / "data" / "kb"

# Якір кінця не потрібен: із re.S крапка вже поглинає все до кінця файлу.
_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?(.*)", re.S)


@dataclass(frozen=True)
class Document:
    """Документ бази знань разом із рівнем доступу."""

    name: str
    title: str
    access: str
    body: str


def _fields(meta: str) -> dict[str, str]:
    """Ключі зводяться до нижнього регістру без пробілів — щоб ` Access:` теж прочиталось."""
    pairs = (line.split(":", 1) for line in meta.splitlines() if ":" in line)
    return {key.strip().lower(): value.strip() for key, value in pairs}


def _access(fields: dict[str, str]) -> str:
    """Рівень доступу або `internal`. Невпізнане значення — це не привід відкрити документ."""
    declared = fields.get("access", "").lower()
    return declared if declared in LEVELS else INTERNAL


def load_documents(directory: Path | None = None) -> list[Document]:
    """Прочитати базу знань. Метадані — у простому frontmatter на початку файлу."""
    documents = []
    for path in sorted((directory or KB_DIR).glob("*.md")):
        # utf-8-sig, а не utf-8: BOM інакше стає частиною першої лінії, frontmatter
        # не збігається, і документ їде далі як текст без метаданих.
        raw = path.read_text(encoding="utf-8-sig")
        match = _FRONTMATTER.match(raw)
        meta, body = (match.group(1), match.group(2)) if match else ("", raw)
        fields = _fields(meta)
        documents.append(
            Document(
                name=path.stem,
                title=fields.get("title") or path.stem,
                access=_access(fields),
                body=body,
            )
        )
    return documents
