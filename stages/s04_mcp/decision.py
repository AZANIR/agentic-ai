"""Чекліст «окремий MCP-інструмент чи ще один ендпоінт» — правилами, а не на око.

Найпоширеніша помилка з MCP виглядає як старанність: узяти своє REST API й оголосити кожен
ендпоінт інструментом. Виходить сервер із сорока інструментами, у якому модель обирає гірше,
ніж обирала б у п'яти — і це та сама вада, що на етапі 3, лише прийшла з іншого боку.

> **MCP-інструмент — це не ендпоінт. Це завдання, яке хтось хоче виконати.**

`GET /orders/{id}`, `GET /orders/{id}/items` і `GET /orders/{id}/shipping` — три ендпоінти й
**один** інструмент: «розкажи про замовлення». Модель не хоче трьох викликів; вона хоче
відповіді.

Порядок правил — теж рішення. Спершу перевіряється, чи є **дія** окремим завданням, і лише
потім усе інше: розмір відповіді, права, частота. Розмір відповіді звучить переконливо й
насправді найслабший — його майже завжди можна полагодити параметром.

Три вердикти:

    ОКРЕМИЙ ІНСТРУМЕНТ   завдання самостійне, модель обирає його свідомо
    ПАРАМЕТР             те саме завдання, інший обсяг чи фільтр
    НЕ ВИСТАВЛЯТИ        модель не має причин це викликати
"""

from __future__ import annotations

from dataclasses import dataclass, field

TOOL = "ОКРЕМИЙ ІНСТРУМЕНТ"
PARAMETER = "ПАРАМЕТР"
HIDE = "НЕ ВИСТАВЛЯТИ"


@dataclass(frozen=True)
class Rule:
    signal: str
    answer: str
    text: str


@dataclass(frozen=True)
class Verdict:
    answer: str
    rule: str


@dataclass(frozen=True)
class Situation:
    name: str
    expected: str
    why: str
    signals: dict[str, bool] = field(default_factory=dict)


RULES = [
    Rule("no_reason_to_call", HIDE, "Модель не має жодної причини це викликати"),
    Rule("irreversible_without_confirm", HIDE, "Незворотна дія без способу підтвердити"),
    Rule("distinct_task", TOOL, "Це самостійне завдання, а не варіант іншого"),
    Rule("different_permissions", TOOL, "Потрібні інші права, ніж у сусідньої дії"),
    Rule("same_task_other_shape", PARAMETER, "Те саме завдання, інший обсяг чи фільтр"),
    Rule("one_of_many_endpoints", PARAMETER, "Один із багатьох ендпоінтів однієї сутності"),
]

SITUATIONS = [
    Situation(
        name="Внутрішній ендпоінт міграції даних",
        expected=HIDE,
        why="Модель не має причин це викликати, а ціна помилки — вся база.",
        signals={"no_reason_to_call": True},
    ),
    Situation(
        name="Видалення акаунта без гейта підтвердження",
        expected=HIDE,
        why="Незворотне без підтвердження не виставляють. Спершу гейт, потім інструмент.",
        signals={"irreversible_without_confirm": True},
    ),
    Situation(
        name="Оформити повернення замовлення",
        expected=TOOL,
        why="Самостійне завдання з власним результатом. Модель обирає його свідомо.",
        signals={"distinct_task": True},
    ),
    Situation(
        name="Пошук у внутрішніх документах для операторів",
        expected=TOOL,
        why="Інші права, ніж у публічного пошуку. Одним інструментом із прапорцем — не можна.",
        signals={"different_permissions": True},
    ),
    Situation(
        name="Список замовлень за останній місяць замість усіх",
        expected=PARAMETER,
        why="Те саме завдання, інший фільтр. Другий інструмент лише розмиває вибір.",
        signals={"same_task_other_shape": True},
    ),
    Situation(
        name="GET /orders/{id}/items поруч із GET /orders/{id}",
        expected=PARAMETER,
        why="Модель хоче відповіді про замовлення, а не трьох викликів по його частинах.",
        signals={"one_of_many_endpoints": True},
    ),
    Situation(
        name="Одна дія, яку користувач просить словами щодня",
        expected=TOOL,
        why="Найпростіший випадок, і його теж варто мати в переліку: якщо просять — виставляй.",
        signals={"distinct_task": True},
    ),
]


def decide(signals: dict[str, bool]) -> Verdict:
    """Пройти правила згори вниз і зупинитися на першому, що спрацювало."""
    for rule in RULES:
        if signals.get(rule.signal):
            return Verdict(answer=rule.answer, rule=rule.text)
    return Verdict(answer=PARAMETER, rule="Жоден сигнал не спрацював — це параметр, не інструмент")


def table() -> str:
    """Той самий чекліст таблицею — з нього збирається DECISION.md."""
    rows = ["| Ситуація | Відповідь | Чому |", "|---|---|---|"]
    rows += [f"| {s.name} | **{decide(s.signals).answer}** | {s.why} |" for s in SITUATIONS]
    return "\n".join(rows)


if __name__ == "__main__":
    print(table())
