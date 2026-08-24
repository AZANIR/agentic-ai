"""Розв'язок вправи 1: три парсери на тих самих відповідях.

    python -m stages.s04_mcp.solutions.exercise_1_naive_parsers

Скрипт не міняє `parse.py`. Він проганяє **три** способи розбору через п'ять відповідей і
показує таблицею, де кожен ламається.

Головне тут — середній стовпчик. `json.loads` на всій відповіді падає голосно, і це чесно:
ти одразу знаєш, що щось не так. Регулярка по тексту **не падає ніколи** — вона знаходить
щось майже завжди, і одного дня це «щось» буде прикладом із документації.

Помилка, яка падає, коштує години. Помилка, яка повертає правдоподібне сміття, коштує
довіри до системи.
"""

from __future__ import annotations

import json
import re
from typing import Any

from stages.s04_mcp.parse import NoPayload, extract_payload

FENCED = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.S)
ANYTHING_JSONISH = re.compile(r"[{\[].*?[}\]]", re.S)

CASES: dict[str, str] = {
    "самі дані": '{"order_id": "ord_4471", "status": "in_transit"}',
    "дані у блоці": 'Ось що знайшов.\n\n```json\n{"order_id": "ord_4471"}\n```\n\nЩе питання?',
    "порожній перелік": "Пошук виконано.\n\n```json\n[]\n```",
    "лише проза": "Система замовлень не відповідає. Спробуйте пізніше.",
    "приклад у прозі": (
        'Формат відповіді такий: {"order_id": "...", "status": "..."} — але зараз '
        "даних немає, бо замовлення не знайдено."
    ),
}


def naive_whole(response: str) -> Any:
    """Спосіб 1: розібрати всю відповідь. Падає на першому ж сервері, який привітався."""
    return json.loads(response)


def naive_regex(response: str) -> Any:
    """Спосіб 2: узяти перше, що схоже на JSON. Не падає ніколи — і в цьому вся біда."""
    found = ANYTHING_JSONISH.search(response)
    if not found:
        raise ValueError("нічого схожого")
    return json.loads(found.group(0))


def _outcome(parser, response: str) -> str:
    try:
        value = parser(response)
    except NoPayload as error:
        return f"відмова: {str(error)[:23]}"
    except Exception as error:  # noqa: BLE001 — саме поведінка при збої і є предметом
        return f"{type(error).__name__}"
    return f"дані: {str(value)[:26]}"


def main() -> int:
    print("Три парсери на п'яти відповідях справжнього сервера.\n")
    header = f"  {'випадок':<18} {'вся відповідь':<24} {'регулярка':<34} наш"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for name, response in CASES.items():
        whole = _outcome(naive_whole, response)
        regex = _outcome(naive_regex, response)
        ours = _outcome(extract_payload, response)
        print(f"  {name:<18} {whole:<24} {regex:<34} {ours}")

    print("""
  Читай останній рядок таблиці — «приклад у прозі».

      вся відповідь   JSONDecodeError        падає, і це чесно
      регулярка       дані: {'order_id':…}   ПОВЕРТАЄ ПРИКЛАД ІЗ ДОКУМЕНТАЦІЇ
      наш             відмова                каже, що даних немає

  Регулярка не помилилась технічно: вона знайшла те, про що її просили. Вона повернула
  структуру правильної форми з неправильним змістом — і жоден лог про це не скаже.

  Другий рядок знизу — «лише проза» — показує другу половину. `json.loads` і регулярка
  падають з однаковим виглядом і на зламаному сервері, і на справному, який просто нічого
  не знайшов. Наш парсер розрізняє: відмова несе текст сервера всередині.

  Мораль, яка коштувала цьому етапу окремої перевірки: **помилка, яка падає, дешевша за
  помилку, яка повертає правдоподібне.**""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
