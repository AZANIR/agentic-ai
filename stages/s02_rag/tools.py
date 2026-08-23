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
from stages.s02_rag.store import KnowledgeBase, SearchResult

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


def describe(result: SearchResult) -> str:
    """Перекласти результат пошуку в текст, який агент отримає як спостереження.

    Відмова розрізняє два стани, які легко злити в один: «розглянули, але далеко» і
    «розглядати не було чого». Одне число 0.00 в обох випадках виглядало б як виміряна
    близькість — тобто агент отримав би вигадану цифру замість чесного «нічого не було».
    """
    if result.hits:
        return "\n\n".join(f"[{h.fragment.label}] {h.fragment.text}" for h in result.hits)
    if result.closest:
        return f"{NO_ANSWER} Найближче — {result.best_score:.2f}, поріг — {result.threshold}."
    return f"{NO_ANSWER} Жодного доступного фрагмента не знайшлося, поріг — {result.threshold}."


def search_knowledge_base(query: str, *, access: str = PUBLIC) -> str:
    """Знайти у базі знань те, що дозволено бачити питальнику, і повернути з мітками."""
    return describe(knowledge_base().search(query, access=access, top_k=TOP_K))


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
