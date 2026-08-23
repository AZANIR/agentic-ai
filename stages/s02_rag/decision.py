"""Чекліст «RAG, донавчання чи просто промпт» — правилами, а не на око.

Питання «RAG чи fine-tuning» майже завжди поставлене неправильно, бо це не два способи
зробити одне й те саме. RAG **додає факти**, донавчання **міняє поведінку**. Питання «які в
нас факти й чия це поведінка» має відповідь; питання «що краще» — не має.

Правила перевіряються згори вниз і зупиняються на першому, що спрацювало. Порядок — це теж
рішення: сигнали про факти стоять вище за сигнали про форму, бо переплутати їх дорого в один
бік і дешево в інший. Донавчити модель, якій насправді бракувало свіжих даних, — це тижні
роботи й та сама неправильна відповідь наприкінці.

Третя відповідь у переліку найважливіша: якщо база маленька й стала, **не треба нічого** —
поклади її в промпт. RAG на восьми сторінках, які не міняються, це інфраструктура заради
інфраструктури.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RAG = "RAG"
FINE_TUNING = "ДОНАВЧАННЯ"
PROMPT = "ПРОСТО ПРОМПТ"


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
    Rule("data_changes", RAG, "Дані змінюються швидше, ніж встигаєш перенавчати модель"),
    Rule("needs_citations", RAG, "Під відповіддю має стояти документ, який можна відкрити"),
    Rule("access_levels", RAG, "Різні люди мають бачити різне з тих самих джерел"),
    Rule("volume_too_big", RAG, "Матеріалу більше, ніж влізе у вікно контексту"),
    Rule("fixed_format", FINE_TUNING, "Потрібен сталий формат чи тон, а не нові факти"),
    Rule("domain_language", FINE_TUNING, "Модель не володіє мовою предметної області"),
]

SITUATIONS = [
    Situation(
        name="Політику повернень переписують щокварталу",
        expected=RAG,
        why="Донавчання зафіксує стан на день навчання й тихо застаріє.",
        signals={"data_changes": True},
    ),
    Situation(
        name="Юристи вимагають посилання під кожною відповіддю",
        expected=RAG,
        why="Модель не може послатися на документ, якого не бачила під час відповіді.",
        signals={"needs_citations": True},
    ),
    Situation(
        name="Оператори бачать внутрішні пороги, покупці — ні",
        expected=RAG,
        why="Донавчена модель не вміє забути частину себе для одного співрозмовника.",
        signals={"access_levels": True},
    ),
    Situation(
        name="Дванадцять тисяч сторінок документації",
        expected=RAG,
        why="У вікно контексту не влізе; вибирати потрібне під питання — це і є пошук.",
        signals={"volume_too_big": True},
    ),
    Situation(
        name="Відповідь завжди має бути в тому самому суворому форматі",
        expected=FINE_TUNING,
        why="Це поведінка, а не факт. Пошук не змінює того, як модель говорить.",
        signals={"fixed_format": True},
    ),
    Situation(
        name="Вісім сторінок правил, які не мінялися два роки",
        expected=PROMPT,
        why="Усе влізе в промпт. RAG тут — інфраструктура заради інфраструктури.",
        signals={},
    ),
]


def decide(signals: dict[str, bool]) -> Verdict:
    """Пройти правила згори вниз і зупинитися на першому, що спрацювало."""
    for rule in RULES:
        if signals.get(rule.signal):
            return Verdict(answer=rule.answer, rule=rule.text)
    return Verdict(answer=PROMPT, rule="Жоден сигнал не спрацював — поклади все у промпт")


def table() -> str:
    """Той самий чекліст у вигляді таблиці — з нього збирається DECISION.md."""
    rows = ["| Ситуація | Відповідь | Чому |", "|---|---|---|"]
    rows += [f"| {s.name} | **{decide(s.signals).answer}** | {s.why} |" for s in SITUATIONS]
    return "\n".join(rows)


if __name__ == "__main__":
    print(table())
