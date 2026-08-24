"""Пам'ять, що зберігає все, поруч із вибірковою — на тому самому наборі фактів.

    python -m stages.s05_memory.solutions.exercise_2_context_rot

Вправу 2 не видно з червоної перевірки повністю: перевірка каже «власний факт зник», але не
показує, **як** деградує відповідь у проміжних станах. Тут три пам'яті на одних і тих самих
даних, і різниця між ними — числом.

Головне не в тому, що наївна пам'ять «гірша». Вона **не падає**. Вона повертає більше, ніж
треба, кожна відповідь трохи гірша за попередню, і жоден лог про це не скаже.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from stages.s05_memory.facts import Fact, is_active
from stages.s05_memory.long_term import Memory
from stages.s05_memory.retrieval import get_retrieval

NOW = 1_700_000_000.0
DAY = 86_400.0
QUESTION = "куди доставляти замовлення"
OWNER = "olena"

# Один власний релевантний факт серед шуму — і серед чужих фактів, які релевантніші
# за формулюванням. Саме така форма й розрізняє три реалізації.
FACTS = (
    Fact(owner=OWNER, topic="address", text="Доставляти замовлення на Хрещатик 22", stored_at=NOW),
    Fact(owner=OWNER, topic="name", text="Звати Олена", stored_at=NOW),
    Fact(owner=OWNER, topic="weather", text="Учора був дощ", stored_at=NOW),
    Fact(owner=OWNER, topic="pet", text="Кота звати Мурчик", stored_at=NOW),
    Fact(owner=OWNER, topic="promo", text="Діє знижка", stored_at=NOW - DAY, ttl=DAY / 2),
    *(
        Fact(
            owner="petro",
            topic=f"address{i}",
            text="Куди доставляти замовлення — на Банкову 11",
            stored_at=NOW,
        )
        for i in range(3)
    ),
)


@dataclass
class Result:
    name: str
    taken: list[str]
    note: str


def keep_everything() -> Result:
    """Наївна: усе, що є у файлі. Нічого не ламається — просто все йде в промпт."""
    taken = [fact.text for fact in FACTS]
    return Result("зберігаю все", taken, "чуже, протухле й нерелевантне — усе в контексті")


def filter_after_selection() -> Result:
    """Вада вправи 2: спершу відібрати найкраще з усього, потім лишити своє."""
    alive = [f for f in FACTS if is_active(f, now=NOW)]
    scores = get_retrieval().score(QUESTION, [f.text for f in alive])
    ranked = sorted(zip(scores, alive, strict=True), key=lambda pair: pair[0], reverse=True)
    top = [fact for score, fact in ranked[:3] if score >= 0.3]
    taken = [fact.text for fact in top if fact.owner == OWNER]
    return Result("фільтр після відбору", taken, "витоку немає — зникла власна відповідь")


def filter_before_selection() -> Result:
    """Як у коді етапу: власник відсіюється до відбору."""
    with TemporaryDirectory() as tmp:
        memory = Memory(Path(tmp) / "m.jsonl")
        for fact in FACTS:
            memory.remember(fact)
        context = memory.context_for(OWNER, QUESTION, now=NOW)
    taken = [line["text"] for line in context.facts]
    return Result("фільтр до відбору", taken, "своє дійшло, чуже ні, причини названі")


def main() -> int:
    print("Питання:", QUESTION)
    mine = sum(1 for fact in FACTS if fact.owner == OWNER)
    print(f"У памʼяті: {len(FACTS)} фактів, із них власних {mine}")
    print()

    for result in (keep_everything(), filter_after_selection(), filter_before_selection()):
        print(f"{result.name:<24} у контексті: {len(result.taken)}")
        for text in result.taken:
            print(f"{'':<26}- {text}")
        if not result.taken:
            print(f"{'':<26}(порожньо)")
        print(f"{'':<26}{result.note}")
        print()

    print("Що тут читати:")
    print("  Перший рядок не є помилкою — він працює. Просто модель бачить сім зайвих фактів,")
    print("  серед них чужу адресу й протухлу акцію, і будує відповідь із них.")
    print()
    print("  Другий — вправа 2. Ані витоку, ані помилки, ані порожнього логу: просто пусто.")
    print("  У продакшні це виглядає як «агент забув», і шукати причину доведеться довго.")
    print()
    print("  Третій — код етапу. Різниця з першим не в тому, що він «правильніший», а в тому,")
    print("  що кожен відкинутий факт має названу причину, і її видно у трейсі.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
