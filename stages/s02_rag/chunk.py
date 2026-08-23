"""Нарізка документа на фрагменти.

Індексується й знаходиться **не документ, а фрагмент**. Причина проста: якщо покласти у
вектор увесь документ, його зміст усереднюється — сторінка про десять різних речей стає
однаково не схожою на жодну з них.

Розмір фрагмента — це рішення, а не технічна дрібниця:

    дрібні фрагменти  ->  точне влучання, але відповідь може загубити контекст навколо
    великі фрагменти  ->  контекст на місці, але зміст розмивається і влучність падає

Правильного розміру немає — є той, що краще працює на твоїх документах і твоїх питаннях.
Саме тому демо показує дві нарізки поруч і не каже, яка краща.

**Межа цієї реалізації:** ріжемо за кількістю слів, не за структурою документа. Нарізка за
заголовками зберігала б думку цілою й майже завжди краща — але вона перетворює цей модуль
на парсер markdown. Це вправа, а не реалізація (SAD §11).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WORD = re.compile(r"\S+")


@dataclass(frozen=True)
class Fragment:
    """Шматок документа разом із тим, звідки він узявся."""

    text: str
    source: str
    position: int

    @property
    def label(self) -> str:
        """Як фрагмент називається у відповіді — саме це побачить читач як джерело."""
        return f"{self.source}#{self.position}"


def split(text: str, *, source: str, size: int, overlap: int = 0) -> list[Fragment]:
    """Порізати текст на фрагменти по ``size`` слів із перекриттям ``overlap``.

    Перекриття існує через межі: думка, що припала на стик двох фрагментів, інакше не
    знайдеться в жодному з них. Ціна — той самий текст індексується двічі.
    """
    if overlap >= size:
        raise ValueError(f"перекриття {overlap} має бути меншим за розмір {size}")

    words = _WORD.findall(text)
    if not words:
        return []  # порожній документ — це нуль фрагментів, а не помилка

    step = size - overlap
    fragments = []
    for position, start in enumerate(range(0, len(words), step)):
        window = words[start : start + size]
        if not window:
            break
        fragments.append(Fragment(text=" ".join(window), source=source, position=position))
        if start + size >= len(words):
            break  # останнє вікно вже накрило хвіст — інакше перекриття плодило б дублі
    return fragments
