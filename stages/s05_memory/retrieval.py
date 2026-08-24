"""Дві вибірки на одному інтерфейсі: за словами й за змістом.

Теза модуля коротка: **вибірка з памʼяті — це та сама задача, що пошук на етапі 2.** Не
схожа, не споріднена — та сама. Є питання, є набір текстів, треба оцінити, які з них
стосуються питання, і взяти найкращі понад порогом.

Тому реалізацій дві, і вони живуть під одним інтерфейсом:

    Overlap    спільні слова питання й факту; нічого не потребує
    Semantic   косинус на ембеддері етапу 2; вмикається, коли ембеддер є

Друга не обовʼязкова: без неї етап проходиться до кінця. Але поставити її поруч варто, бо
вона показує ту саму межу, що й етап 2 — синоніми. «Де я живу» і «моя адреса» не мають
спільних слів; словникова вибірка на цьому сліпа, і це видно числом, а не поясненням.

**Поріг тут важливіший, ніж на етапі 2.** Там нижче порога означало «нічого не знайшли» —
чесна відповідь. Тут нижче порога означає «не клади це в контекст», і кожен зайвий факт,
який пройшов, робить відповідь трохи гіршою. Контекст не має обмеження на дурниці — лише
на токени.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

_WORD = re.compile(r"\w+", re.UNICODE)

# Слова, спільні для будь-яких двох реплік українською. Без них «мене» і «моє» дають
# збіг там, де спільного змісту немає.
_NOISE = frozenset(
    {
        "я",
        "ти",
        "він",
        "вона",
        "воно",
        "ми",
        "ви",
        "вони",
        "мене",
        "мені",
        "мій",
        "моя",
        "моє",
        "мої",
        "це",
        "цей",
        "ця",
        "той",
        "та",
        "те",
        "і",
        "й",
        "але",
        "що",
        "як",
        "де",
        "коли",
        "чи",
        "не",
        "на",
        "в",
        "у",
        "з",
        "до",
        "для",
        "про",
        "за",
        "є",
        "був",
        "була",
        "буде",
        "бути",
        "має",
        "мати",
    }
)


class Retrieval(Protocol):
    """Спільний інтерфейс. `long_term` знає лише його."""

    name: str

    def score(self, question: str, texts: list[str]) -> list[float]:
        """Оцінки релевантності, по одній на текст. Більше — ближче."""
        ...


def _words(text: str) -> set[str]:
    return {w for w in _WORD.findall(text.lower()) if w not in _NOISE and len(w) > 2}


@dataclass
class Overlap:
    """Спільні слова. Нічого не потребує й нічого не розуміє — і в цьому урок."""

    name: str = "overlap"

    def score(self, question: str, texts: list[str]) -> list[float]:
        asked = _words(question)
        if not asked:
            return [0.0] * len(texts)
        return [len(asked & _words(text)) / len(asked) for text in texts]


@dataclass
class Semantic:
    """Косинус на ембеддері етапу 2. Та сама задача, той самий інструмент."""

    embedder: Any
    name: str = ""

    def __post_init__(self) -> None:
        self.name = f"semantic:{self.embedder.name}"

    def score(self, question: str, texts: list[str]) -> list[float]:
        from shared.embeddings import cosine

        if not texts:
            return []
        vectors = self.embedder.embed([question, *texts])
        return [float(value) for value in cosine(vectors[0], vectors[1:])]


def get_retrieval(*, semantic: bool = False) -> Retrieval:
    """Вибірка за конфігурацією. Дефолт — словникова: вона працює завжди."""
    if not semantic:
        return Overlap()
    from shared.embeddings import get_embedder

    return Semantic(embedder=get_embedder())
