"""MCP-сервер NovaShop: оголошує інструменти етапів 1–2 й виконує їх.

    python -m stages.s04_mcp.server        # запускається як окремий процес, говорить по stdio

Це справжній сервер, а не мок. Він живе в **іншому процесі**, і саме тому етап нетривіальний:
усе, що перетинає цю межу, стає текстом, який комусь треба розібрати, а сам процес може не
запуститись, замовкнути або померти.

Три речі варто прочитати повільно.

**Опис інструмента — це те, за чим модель обирає.** Він іде в промпт клієнта дослівно. Тут
його пишемо ми, бо сервер свій; у житті його пише той, кому належить сервер, — і клієнт не
має права на нього покладатися (ADR етапу 0003).

**Рівень доступу приїжджає в payload, а не живе в сесії.** Специфікація протоколу зробила його
stateless: сервер не зобов'язаний пам'ятати, хто питав минулого разу. Наслідок практичний —
виклик відтворюваний: узяв рядок із трейсу, повторив, отримав те саме (ADR етапу 0004).

**Пошук навмисно відповідає з прозою навколо даних.** Не тому, що так треба, а тому, що так
роблять справжні сервери: додають підсумок, попередження, згадку про інший інструмент. Клієнт,
який робить `json.loads` на всій відповіді, ламається на першому ж такому. Розбір — половина
уроку етапу, і на мовчазному сервері його не показати.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server import MCPServer

from stages.s01_agent_loop.tools import REGISTRY
from stages.s02_rag.documents import LEVELS, PUBLIC
from stages.s02_rag.tools import knowledge_base

server = MCPServer(name="novashop", instructions="Інструменти магазину NovaShop.")


def _block(payload: Any) -> str:
    """Дані у виділеному блоці. Клієнт бере саме його, а не всю відповідь."""
    return "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"


@server.tool(description="Статус замовлення за його номером. Потрібен номер вигляду ord_NNNN.")
def get_order_status(order_id: str) -> str:
    return _block({"order_id": order_id, "answer": REGISTRY["get_order_status"].func(order_id)})


@server.tool(
    description=(
        "Оформити повернення замовлення. НЕЗВОРОТНА дія: гроші йдуть назад, "
        "скасувати не можна. Потрібні номер замовлення й причина."
    )
)
def initiate_return(order_id: str, reason: str) -> str:
    done = REGISTRY["initiate_return"].func(order_id, reason)
    return _block({"order_id": order_id, "reason": reason, "answer": done})


@server.tool(
    description=(
        "Пошук у базі знань магазину: правила, строки, опис товарів. "
        "Рівень доступу питальника передається явно й обмежує видачу."
    )
)
def search_knowledge_base(query: str, access: str = PUBLIC) -> str:
    if access not in LEVELS:
        return f"Невідомий рівень доступу {access!r}. Дозволені: {', '.join(sorted(LEVELS))}."
    found = knowledge_base().search(query, access=access, top_k=3)
    payload = {
        "query": query,
        "access": access,
        "hits": [{"source": h.fragment.label, "text": h.fragment.text} for h in found.hits],
    }
    # Проза навколо даних — навмисно. Справжні сервери роблять саме так.
    return (
        f"Знайшов {len(found.hits)} фрагментів для рівня доступу {access}.\n\n"
        f"{_block(payload)}\n\n"
        "Якщо потрібні внутрішні документи, зверніться з відповідним рівнем доступу."
    )


@server.resource("novashop://policies/returns")
def returns_policy() -> str:
    """Resource — це дані для читання, не дія. Клієнт бере їх сам, модель їх не викликає."""
    return (
        knowledge_base().search("повернення товару", access=PUBLIC, top_k=1).hits[0].fragment.text
    )


@server.prompt(description="Заготовка відповіді покупцю: тон і структура, без фактів.")
def support_reply(question: str) -> str:
    """Prompt — це заготовка, а не інструмент. Плутати три поняття — найчастіша помилка."""
    return (
        "Відповідай коротко й по суті, українською. Спочатку відповідь, потім джерело.\n\n"
        f"Питання покупця: {question}"
    )


if __name__ == "__main__":
    server.run(transport="stdio")
