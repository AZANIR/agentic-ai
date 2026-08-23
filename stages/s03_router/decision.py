"""Чекліст «чи потрібен тут supervisor» — правилами, а не на око.

Найчастіша відповідь — **не потрібен**, і саме тому чекліст існує. Граф із трьох агентів
виглядає як архітектура, а один агент із трьома інструментами — як щось недороблене; на цьому
відчутті будуються системи, у яких кожна відповідь коштує трьох викликів моделі замість одного.

Порядок правил — теж рішення. Спершу перевіряються **структурні обмеження**: якщо відповідь
одного має бути перевірена іншим, або частинами володіють різні команди, або їм потрібні різні
моделі — жодна економія цього не обійде. Далі йде **вартість**. І лише наприкінці — розмір,
тобто найслабший з аргументів, хоча саме він звучить найчастіше.

Три вердикти, а не два:

    ОДИН АГЕНТ     інструменти в одному реєстрі, один виклик моделі на відповідь
    КЛАСИФІКАТОР   дешевий вибір гілки без циклу ревізій — середина, яку пропускають
    SUPERVISOR     повний граф із передачами й ревізіями

Середній вердикт існує тому, що більшість систем, які будують як supervisor, насправді
потребують саме його: маршрут потрібен, а цикл ревізій — ні. Він приходить на етапі 6, коли
з'явиться бюджет.
"""

from __future__ import annotations

from dataclasses import dataclass, field

ONE_AGENT = "ОДИН АГЕНТ"
CLASSIFIER = "КЛАСИФІКАТОР"
SUPERVISOR = "SUPERVISOR"


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
    Rule("answer_needs_review", SUPERVISOR, "Відповідь одного має перевірятися іншим"),
    Rule("separate_ownership", SUPERVISOR, "Частинами володіють різні команди"),
    Rule("different_models", SUPERVISOR, "Частинам потрібні різні моделі або налаштування"),
    Rule("conflicting_descriptions", CLASSIFIER, "Описи інструментів конфліктують між собою"),
    Rule("latency_critical", CLASSIFIER, "Кожна зайва передача коштує помітної затримки"),
    Rule("many_tools", CLASSIFIER, "Інструментів більше, ніж модель тримає в голові"),
]

SITUATIONS = [
    Situation(
        name="Юридичні відповіді має вичитувати другий агент",
        expected=SUPERVISOR,
        why="Цикл ревізій — це і є supervisor. Один агент не перевіряє сам себе.",
        signals={"answer_needs_review": True},
    ),
    Situation(
        name="Платежі веде одна команда, каталог — інша",
        expected=SUPERVISOR,
        why="Межа агентів має збігатися з межею відповідальності, інакше кожна зміна спільна.",
        signals={"separate_ownership": True},
    ),
    Situation(
        name="Класифікації досить дешевої моделі, відповідям — ні",
        expected=SUPERVISOR,
        why="Різні моделі неможливо тримати в одному реєстрі інструментів.",
        signals={"different_models": True},
    ),
    Situation(
        name="Модель плутає два схожі інструменти",
        expected=CLASSIFIER,
        why="Маршрут потрібен, цикл ревізій — ні. Це середина, яку зазвичай пропускають.",
        signals={"conflicting_descriptions": True},
    ),
    Situation(
        name="Голосовий асистент: пауза понад секунду чутна",
        expected=CLASSIFIER,
        why="Кожна передача — виклик моделі. Supervisor тут купується часом користувача.",
        signals={"latency_critical": True},
    ),
    Situation(
        name="Сорок інструментів в одному реєстрі",
        expected=CLASSIFIER,
        why="Вибір розмивається задовго до сорока. Групувати треба, розділяти агентів — ні.",
        signals={"many_tools": True},
    ),
    Situation(
        name="П'ять інструментів, одна предметна область",
        expected=ONE_AGENT,
        why="Найчастіший випадок і найчастіша помилка: граф там, де вистачає реєстру.",
        signals={},
    ),
]


def decide(signals: dict[str, bool]) -> Verdict:
    """Пройти правила згори вниз і зупинитися на першому, що спрацювало."""
    for rule in RULES:
        if signals.get(rule.signal):
            return Verdict(answer=rule.answer, rule=rule.text)
    return Verdict(answer=ONE_AGENT, rule="Жоден сигнал не спрацював — почни з одного агента")


def table() -> str:
    """Той самий чекліст таблицею — з нього збирається DECISION.md."""
    rows = ["| Ситуація | Відповідь | Чому |", "|---|---|---|"]
    rows += [f"| {s.name} | **{decide(s.signals).answer}** | {s.why} |" for s in SITUATIONS]
    return "\n".join(rows)


if __name__ == "__main__":
    print(table())
