"""Міст: пошук по базі знань як звичайний інструмент агента з етапу 1.

Тут не з'являється нової архітектури. Реєстр, форма опису, валідація аргументів — усе те
саме, що на етапі 1; цикл агента не змінюється **жодним рядком** (є перевірка, яка це
стверджує через `git diff` до теґу `stage-01`). RAG приходить у агента як ще один інструмент,
а не як переписаний агент — і саме це варто побачити на власні очі.

**Одна деталь тут не косметична: рівня доступу немає серед параметрів інструмента.**

    parameters -> {"query": ...}          модель може попросити пошук
    partial(..., access=...)              хто питає — вирішує система

Якби `access` стояв у схемі, модель могла б передати `access="internal"` — і зробила б це не
зі зловмисності, а тому що так більше знайдеться. Рівень доступу — це факт про того, хто
поставив питання, а не аргумент, який хтось обирає під час відповіді. Тому він прив'язується
`partial` при складанні інструмента, а `additionalProperties: false` закриває чорний хід:
аргумент, якого немає у схемі, валідатор етапу 1 відхиляє, а не мовчки ігнорує.
"""

from __future__ import annotations

from functools import lru_cache, partial

from shared.embeddings import get_embedder
from stages.s01_agent_loop.tools import Tool
from stages.s02_rag.answer import NO_ANSWER
from stages.s02_rag.documents import PUBLIC, load_documents
from stages.s02_rag.store import KnowledgeBase

SIZE = 40
OVERLAP = 10
THRESHOLD = 0.2
TOP_K = 3


@lru_cache(maxsize=1)
def knowledge_base() -> KnowledgeBase:
    """Індекс будується один раз на процес: ембеддинги коштують, відповідь — ні."""
    base = KnowledgeBase(embedder=get_embedder(), threshold=THRESHOLD)
    base.index(load_documents(), size=SIZE, overlap=OVERLAP)
    return base


def search_knowledge_base(query: str, *, access: str = PUBLIC) -> str:
    """Знайти у базі знань те, що дозволено бачити питальнику, і повернути з мітками."""
    result = knowledge_base().search(query, access=access, top_k=TOP_K)
    if not result.hits:
        return f"{NO_ANSWER} Найближче — {result.best_score:.2f}, поріг — {result.threshold}."
    return "\n\n".join(f"[{hit.fragment.label}] {hit.fragment.text}" for hit in result.hits)


def tool_for(*, access: str) -> Tool:
    """Скласти інструмент для питальника з даним рівнем доступу.

    Рівень доступу зашивається у функцію, а не в схему: модель формулює запит, систему ніхто
    не питає, кому можна що бачити.
    """
    return Tool(
        name="search_knowledge_base",
        description=(
            "Шукає відповідь у базі знань магазину: політики, строки, опис товарів. "
            "Викликай, коли питання стосується правил магазину або товару."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Питання покупця словами, близькими до тексту документів.",
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        func=partial(search_knowledge_base, access=access),
        irreversible=False,
    )


def registry_with_search(*, access: str) -> dict[str, Tool]:
    """Реєстр етапу 1 плюс пошук. Той самий словник, тією ж формою."""
    from stages.s01_agent_loop.tools import REGISTRY

    tool = tool_for(access=access)
    return {**REGISTRY, tool.name: tool}
