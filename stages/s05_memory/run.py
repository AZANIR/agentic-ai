"""Демонстрація етапу 5: шість сцен підряд.

    python -m stages.s05_memory.run
    python -m stages.s05_memory.run --prompt    # показати ще й промпт із фактами

Працює **без API-ключа**: витяг фактів і сумаризацію дає підробка за записаним сценарієм.
Перший рядок виводу каже, що саме працює.

Сцени показують свої критерії приймання:

    1. вікно: хвіст дослівно, підсумок накопичується   AC-01, AC-01b
    2. дві сесії: факт першої доходить у другу          AC-02
    3. нерелевантний факт НЕ доходить — і видно чому    AC-03
    4. суперечність і протухання                        AC-04, AC-05
    5. чужа памʼять не доходить, своя доходить          AC-06, AC-06b
    6. чекліст «що запамʼятовувати»                     AC-08

**Головна тут — сцена 3.** Решта показують, що памʼять працює; вона показує, що памʼять
**не спрацьовує там, де не має**. Перше легко, друге — власне етап.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from shared.fake_llm import FakeLLM, text
from shared.llm import banner, get_client
from shared.trace import trace_run
from stages.s05_memory.decision import RULES, Situation, decide
from stages.s05_memory.facts import Fact
from stages.s05_memory.long_term import Memory, extract
from stages.s05_memory.short_term import Window

DAY = 86_400.0
NOW = 1_700_000_000.0

SESSION_ONE = [
    {"role": "user", "content": "привіт, я Олена, живу в Києві"},
    {"role": "assistant", "content": "вітаю, Олено"},
    {"role": "user", "content": "доставляти на Хрещатик 22"},
]
EXTRACTED = (
    '[{"topic": "name", "text": "Звати Олена"},'
    ' {"topic": "address", "text": "Доставляти на Хрещатик 22"}]'
)

NOISE = Fact(owner="olena", topic="weather", text="Учора був дощ", stored_at=NOW)
QUESTION = "куди доставляти замовлення"


def _client(*replies: str) -> FakeLLM:
    return FakeLLM(script=[text(r) for r in replies])


def _texts(context) -> list[str]:
    return [fact["text"] for fact in context.facts]


def scene_window(tracer) -> None:
    print("1. Вікно: хвіст лишається дослівно, підсумок накопичується")
    window = Window(size=2)
    for number in range(1, 6):
        window.add({"role": "user", "content": f"репліка {number}"})

    first = window.compress(client=_client("Обговорили репліки 1-3."))
    for number in range(6, 9):
        window.add({"role": "user", "content": f"репліка {number}"})
    second = window.compress(client=_client("Далі обговорили репліки 4-6."))

    print(f"  стиснуто:   {first.compressed}, потім ще {second.compressed}")
    print(f"  дослівно:   {[m['content'] for m in window.recent()]}")
    print(f"  підсумок:   {window.summary!r}")
    tracer.step("memory", scene="window", compressed=first.compressed + second.compressed)
    print()
    print("  Другий підсумок ДОПИСАНО, а не переписано. Найпростіша реалізація стискає")
    print("  «все поза вікном» — разом із попереднім підсумком, — і текст лишається")
    print("  звʼязним, поступово перестаючи бути правдою.")
    print()


def scene_two_sessions(tracer, path: Path) -> None:
    print("2. Дві сесії: те, що сказано в першій, доходить у другу")
    found = extract(SESSION_ONE, client=_client(EXTRACTED))
    memory = Memory(path)
    for item in found:
        memory.remember(Fact(owner="olena", stored_at=NOW, **item))

    # Навмисно ІНШИЙ обʼєкт: друга сесія читає файл, а не те, що лишилось у процесі.
    context = Memory(path).context_for("olena", QUESTION, now=NOW)
    print(f"  витягнуто:  {[fact['topic'] for fact in found]}")
    print(f"  у файлі:    {len(Memory(path).all_facts())} записів")
    print(f"  у контекст: {_texts(context)}")
    tracer.step("memory", scene="recall", taken=len(context.facts))
    print()
    print("  Друга сесія читає ЗАПИСАНЕ — не обʼєкт, що лишився в памʼяті процесу. Саме")
    print("  тому тут окремий Memory на той самий файл, а не той самий обʼєкт.")
    print()


def scene_selectivity(tracer, path: Path) -> None:
    print("3. Нерелевантний факт НЕ доходить — і видно, чому саме")
    memory = Memory(path)
    memory.remember(NOISE)
    context = memory.context_for("olena", QUESTION, now=NOW)

    print(f"  у памʼяті:  {len(memory.all_facts())} записів")
    print(f"  у контекст: {_texts(context)}")
    for skipped in context.skipped:
        print(f"  відкинуто:  {skipped.text!r} — {skipped.reason}")
    tracer.step("memory", scene="skip", skipped=len(context.skipped))
    print()
    print("  «Учора був дощ» лишилось за бортом із названою причиною. Без причини памʼять")
    print("  просто «забула», і пояснити це користувачеві нічим.")
    print()


def scene_contradiction_and_ttl(tracer, path: Path) -> None:
    print("4. Суперечність витісняє стару правду; протухле не бере участі")
    memory = Memory(path)
    retired = memory.remember(
        Fact(
            owner="olena",
            topic="address",
            text="Тепер доставляти на Володимирську 5",
            stored_at=NOW + DAY,
        )
    )
    memory.remember(
        Fact(
            owner="olena",
            topic="promo",
            text="Діє знижка на доставку",
            stored_at=NOW,
            ttl=DAY / 2,
        )
    )
    context = memory.context_for("olena", QUESTION, now=NOW + DAY)

    print(f"  замінено:   {retired.text!r} → статус {retired.status}")
    print(f"  у файлі:    {len(memory.all_facts())} записів — історія заміни лишилась")
    print(f"  у контекст: {_texts(context)}")
    for skipped in context.skipped:
        if "протух" in skipped.reason or "замінено" in skipped.reason:
            print(f"  відкинуто:  {skipped.text!r} — {skipped.reason}")
    tracer.step("memory", scene="contradiction", retired=retired.topic)
    print()
    print("  Обидва записи лишились у файлі; у вибірку йде один. Видалення при записі було")
    print("  б дешевшим — і втратило б відповідь на питання «а що було раніше».")
    print()


def scene_isolation(tracer, path: Path) -> None:
    print("5. Чужа памʼять не доходить — і своя при цьому доходить")
    memory = Memory(path)
    memory.remember(
        Fact(owner="petro", topic="address", text="Доставляти на Лесі Українки 8", stored_at=NOW)
    )
    hers = memory.context_for("olena", QUESTION, now=NOW + DAY)
    his = memory.context_for("petro", QUESTION, now=NOW + DAY)

    print(f"  Олена бачить: {_texts(hers)}")
    print(f"  Петро бачить: {_texts(his)}")
    tracer.step("memory", scene="isolation", owners=2)
    print()
    print("  Два твердження, не одне: чуже не дійшло І своє дійшло. Фільтр власника стоїть")
    print("  ДО відбору top-k — після нього чужий факт зайняв би слот, його прибрали б, і")
    print("  власна відповідь зникла б. Витоку немає; відповіді теж немає.")
    print()


def scene_checklist(tracer) -> None:
    print("6. Чекліст «що запамʼятовувати»: шість реплік, дві збережено")
    situations = (
        Situation("мій пароль — hunter2", secret=True, asked=True),
        Situation("столиця Франції — Париж", about_world=True),
        Situation("отже, мені 34 роки", derivable=True),
        Situation("запамʼятай: я вегетаріанець", asked=True),
        Situation("я живу в Києві", durable=True),
        Situation("порахуй 17 плюс 4"),
    )
    for situation in situations:
        decision = decide(situation)
        mark = "так" if decision.keep else " ні"
        print(f"  [{mark}] {situation.text:<30} {decision.why}")
    tracer.step("memory", scene="checklist", rules=len(RULES))
    print()
    print("  «Запамʼятай мій пароль» — водночас секрет і пряме прохання. Відповідь залежить")
    print("  винятково від того, яке питання стоїть у чекліста раніше. Порядок і є чеклістом.")
    print()


def main(*, show_prompt: bool = False, trace_path: Path | None = None) -> int:
    client = get_client(demo_script=[text("")])
    print(banner(client))
    print(f"правил у чеклісті: {len(RULES)}")
    print()

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "memory.jsonl"
        with trace_run("Етап 5 · Memory", path=trace_path, stage="s05") as tracer:
            scene_window(tracer)
            scene_two_sessions(tracer, path)
            scene_selectivity(tracer, path)
            scene_contradiction_and_ttl(tracer, path)
            scene_isolation(tracer, path)
            scene_checklist(tracer)

        if show_prompt:
            context = Memory(path).context_for("olena", QUESTION, now=NOW + DAY)
            print("--- промпт із фактами " + "-" * 52)
            for line in context.as_prompt().splitlines():
                print(f"| {line}")
            print("-" * 74)
            print()

    if trace_path is None:
        print("Трейси прогонів: traces/ — їх читатиме етап 8.")
    if not show_prompt:
        print("Щоб побачити, як факти лягають у промпт:")
        print("    python -m stages.s05_memory.run --prompt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(show_prompt="--prompt" in sys.argv))
