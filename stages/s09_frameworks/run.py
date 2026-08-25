"""Демонстрація етапу 9: шість сцен підряд.

    python -m stages.s09_frameworks.run
    S09_ADK=1 python -m stages.s09_frameworks.run    # ADK, якщо є креденшели

Працює **без ключа й без мережі**. Модель — підробка зі спільним сценарієм: різні сценарії
зробили б токени неспівмірними ще до того, як фреймворк щось додав.

Сцени показують свої критерії приймання:

    1. контракт: п'ять елементів, однакових для всіх        AC-02
    2. таблиця: чотири рядки, вісім колонок                 AC-01, AC-05
    3. де живе координація                                  AC-06
    4. мої рядки проти невидимих                            AC-03
    5. токени: просив і пішло                               AC-04, AC-04b
    6. правило вибору: обмеження -> інструмент              AC-09, AC-09b

**Головна тут — четверта разом із пʼятою.** Кожна окремо підтверджує звичне твердження; разом
вони його спростовують: платять різні фреймворки різним, і саме тому переможця немає.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any

from shared.fake_llm import FakeLLM
from shared.llm import get_client
from stages.s09_frameworks import baseline, compare, contract, via_adk, via_crewai, via_langgraph
from stages.s09_frameworks.counters import counted, executed_lines

BANNER = (
    "[FakeLLM] Модель підроблена й сценарій спільний: інакше токени були б неспівмірні "
    "ще до того, як фреймворк щось додав. Висновки — про співвідношення, не про абсолютні числа."
)

# Реалізація, її модуль і пакети, чиї виконані рядки для неї є невидимими.
IMPLEMENTATIONS: tuple[tuple[Any, str, tuple[str, ...]], ...] = (
    (baseline, "baseline.py", ()),
    (via_langgraph, "via_langgraph.py", ("langgraph", "langchain_core")),
    (via_crewai, "via_crewai.py", ("crewai",)),
    (via_adk, "via_adk.py", ("google.adk",)),
)

# Правила вибору. Кожне називає колонку, з якої воно виведене (ADR-0005).
RULES = [
    ("треба розуміти порядок кроків під час інциденту", "явну координацію", "місць прози"),
    ("рахунок від провайдера болить", "те, що додає нуль понад запит", "понад запит"),
    ("код читатимуть новачки", "менше невидимих рядків", "невидимі рядки"),
    ("задача — два кроки без розгалужень", "нічого; базова лінія вже коротша", "мої рядки"),
    ("треба паралельні гілки, чекпоінти, стрімінг", "граф-оркестратор", "невидимі рядки"),
]


def _client() -> Any:
    """Клієнт із лічильником. Єдина межа провайдера на всі чотири реалізації (ADR-0007)."""
    inner = get_client(demo_script=contract.script())
    if isinstance(inner, FakeLLM):
        inner.repeat_last = True
    return counted(inner, contract.owned_texts())


def collect(traces: Path) -> list[compare.Row]:
    """Прогнати все, що можна прогнати, і зібрати рядки таблиці."""
    via_adk.demand()  # гучно, ДО таблиці: мовчазний прапорець гірший за його відсутність
    rows: list[compare.Row] = []
    for module, name, packages in IMPLEMENTATIONS:
        title = module.NAME
        # Питаємо всіх однаково. `hasattr` тут колись пропускав LangGraph повз перевірку —
        # у нього був `available()` замість `unavailable_because()`, і збірка мовчки
        # вважала його доступним, а падав він уже всередині побудови графа.
        if why := module.unavailable_because():
            rows.append(compare.skipped(title, name, why))
            continue
        if hasattr(module, "wanted") and not module.wanted():
            rows.append(compare.skipped(title, name, "прапорець вимкнено за замовчуванням"))
            continue
        client = _client()
        with executed_lines(*packages) as invisible:
            result = module.traced(client, traces)
        rows.append(compare.measured(result, client.tally, invisible, name))
    return rows


def scene_contract() -> None:
    print("1. Контракт задачі — п'ять елементів, однакових для всіх")
    print(f"   вхід          {contract.QUESTION}")
    print(f"   інструменти   {list(contract.TOOLS)}")
    print("   модель        клієнт подається ззовні; власного не створює жодна реалізація")
    print(f"   зупинка       {contract.ANSWERED!r}")
    print(f"   форма         відповідь згадує {list(contract.GROUNDING)}")
    print()
    print("   Контракт — код, а не проза. Реалізація, що відхилилась, лишається в таблиці")
    print("   БЕЗ чисел: мовчазне включення дало б число, яке виглядає порівнянним.")
    print()


def scene_table(rows: list[compare.Row], path: Path) -> None:
    print("2. Таблиця — чотири реалізації, і одна з них без фреймворка")
    width = max(len(row.name) for row in rows)
    for row in rows:
        cells = row.cells()
        print(f"   {row.name:<{width}}  {' | '.join(cells[1:5])}")
    print()
    counted_rows = [row for row in rows if row.counted]
    print(f"   виміряно {len(counted_rows)} із {len(rows)}; решта має причину в таблиці,")
    print("   а не порожнє місце: три рядки не мають виглядати як усі.")
    print()
    print(f"   Записано: {path.name}")
    print()


def scene_coordination(rows: list[compare.Row]) -> None:
    print("3. Де живе координація — і скільки прози треба прочитати")
    for row in rows:
        tail = row.why_source if row.counted else row.unverified
        print(f"   {row.name:<14} місць прози {row.places:>3}   {tail}")
    print()
    print("   Це число виміряне З ДЖЕРЕЛА, а не оголошене: рахуються іменовані аргументи,")
    print("   значення яких описують поведінку прозою. Тому воно є навіть у рядка, якого")
    print("   не вдалося прогнати — обмеження інтерпретатора не робить код нечитабельним.")
    print()
    print("   Нуль означає явну координацію: наступний крок вирішує код. Десять означає, що")
    print("   на питання «чому виконався цей крок» доведеться прочитати десять описів і")
    print("   уявити, як їх прочитала модель.")
    print()


def scene_lines(rows: list[compare.Row]) -> None:
    print("4. Мої рядки проти невидимих")
    for row in (row for row in rows if row.counted):
        print(f"   {row.name:<14} мої {row.mine:>4}   невидимі {row.invisible:>6}")
    print()
    print("   Друге число описує ЦЕЙ вхід: скільки рядків пакета справді виконалось, а не")
    print("   скільки їх встановлено. Інша задача виконає інші — і це властивість виміру.")
    print()
    print("   «Менше коду» без другої половини — аргумент без другої половини: код нікуди")
    print("   не подівся, він переїхав туди, де його не видно й не можна виправити.")
    print()


def scene_tokens(rows: list[compare.Row]) -> None:
    print("5. Токени: просив автор і пішло насправді")
    for row in (row for row in rows if row.counted):
        print(f"   {row.name:<14} просив {row.asked:>5}   понад запит {row.overhead:>5}")
    print()
    print("   Надбавка рахується НА МЕЖІ ПРОВАЙДЕРА: лічильник усередині реалізації бачить")
    print("   лише те, що вона попросила, — тобто саме надбавки й не бачить.")
    print()
    print("   Порівняй із четвертою сценою. Платять різним: оркестратор бере рядками й")
    print("   додає нуль токенів; фреймворк, що складає промпти з описів ролей, — навпаки.")
    print("   Саме тому переможця немає, а є обмеження.")
    print()


def scene_rules(path: Path) -> None:
    print("6. Правило вибору — обмеження, а не переможець")
    for when, take, column in RULES:
        print(f"   якщо {when}")
        print(f"      -> {take}   (колонка: {column})")
    print()
    print("   Кожне правило називає колонку, з якої воно виведене. Правило, яке неможливо")
    print("   застосувати поза цією таблицею, є переказом, а не правилом.")
    print()
    print(f"   Повна таблиця: {path.name}")
    print()


def main(*, table_path: Path | None = None) -> int:
    print(BANNER)
    print()
    with tempfile.TemporaryDirectory() as tmp:
        traces = Path(tmp) / "s09.jsonl"
        rows = collect(traces)
        target = compare.save(rows, RULES, table_path or Path(tmp) / "COMPARISON.md")

        scene_contract()
        scene_table(rows, target)
        scene_coordination(rows)
        scene_lines(rows)
        scene_tokens(rows)
        scene_rules(target)

    if table_path is None:
        print("Щоб лишити таблицю на диску:")
        print(
            '    python -c "from pathlib import Path;'
            " from stages.s09_frameworks.run import main;"
            " main(table_path=Path('COMPARISON.md'))\""
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except via_adk.Demanded as loud:
        print(f"[{via_adk.FLAG}] {loud}", file=sys.stderr)
        raise SystemExit(2) from loud
