"""Витяг фактів із розмови — єдине місце етапу, якому потрібна модель.

Окремим модулем не заради чистоти. `long_term.py` має бюджет у 90 виконуваних рядків, і
реєстр ризиків SAD передбачив саме цей момент дослівно: **виносити треба буде не вибірку
(вона вже окремо), а витяг — він єдиний потребує моделі**. Ризик спрацював, мітигація
виявилась правильною, і винесення робиться за нею, а не навмання.

Межа тут природна й без бюджету. Усе в `long_term.py` — детерміноване: прочитати файл,
відсіяти, відсортувати, віддати. Витяг — єдине, що ходить у модель, тобто єдине, що може
відповісти по-різному на той самий вхід. Ця різниця варта окремого файлу.

**Порожній перелік — нормальна відповідь.** У розмові часто немає нічого, що варто
памʼятати надовго, і памʼять, яка за таких умов щось вигадує, гірша за порожню.
"""

from __future__ import annotations

import json
from typing import Any

from shared.llm import get_model

_EXTRACT = """Витягни з розмови факти, які варто памʼятати про співрозмовника надовго.

Поверни JSON-масив обʼєктів із полями `topic` і `text`. Тема — одне слово про що факт
(`name`, `address`, `preference`). Якщо памʼятати нічого — поверни порожній масив.

{lines}"""


def extract(
    conversation: list[dict[str, str]], *, client: Any, model: str | None = None
) -> list[dict[str, str]]:
    """Спитати модель, що з розмови варто памʼятати. Порожній перелік — нормальна відповідь."""
    lines = "\n".join(f"- {m['role']}: {m['content']}" for m in conversation)
    reply = client.chat.completions.create(
        model=model or get_model(),
        messages=[{"role": "user", "content": _EXTRACT.format(lines=lines)}],
    )
    raw = (reply.choices[0].message.content or "").strip()
    try:
        found = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(found, list):
        return []
    return [
        {"topic": str(item["topic"]), "text": str(item["text"])}
        for item in found
        if isinstance(item, dict) and item.get("topic") and item.get("text")
    ]
