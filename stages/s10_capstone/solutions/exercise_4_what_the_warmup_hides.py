"""Розв'язок вправи 4: скільки коштує відсутній прогрів — у свіжому процесі.

    python -m stages.s10_capstone.solutions.exercise_4_what_the_warmup_hides

Червона перевірка вправи 4 каже «роботу виконано 1 раз — прогріву немає» і на цьому
зупиняється. Наскільки міняється **число**, вона не каже навмисно: у наборі перевірок ефект уже
з'їдений. Поки черга дійде до виміру, попередні перевірки все поімпортували, і `sys.modules`
віддає готове.

Тому вимір робиться тут — у **свіжому процесі**, де перший виклик справді перший. Дитячий
процес міряє двічі підряд:

    холодний   перший виклик у процесі, БЕЗ прогріву
    теплий     те саме, але після прогріву — тобто так, як міряє етап

Різниця — це рядки, які трапляються **раз на процес**: тіла лениво імпортованих модулів. У ціні
одного запиту їм не місце, і саме тому `measure()` виконує роботу двічі.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Дитячий процес. Порядок обов'язковий: холодний вимір мусить бути ПЕРШИМ викликом, інакше
# міряти нема чого — прогріє його сам теплий.
CHILD = """
import tempfile
from pathlib import Path

from shared.trace import trace_run
from stages.s10_capstone import assemble, scenarios, seams
from stages.s10_capstone.run import _judge, measured

base = seams.build_search()
with tempfile.TemporaryDirectory() as tmp:
    traces = Path(tmp) / "s10.jsonl"
    with trace_run("cold", path=traces, stage="s10", case="cold") as tracer:
        service = scenarios.build(Path(tmp), tracer, base=base)

        def work():
            answers = [
                service.ask(scenarios.KEY, item.question, now=scenarios.NOW)
                for item in scenarios.SCENARIOS
            ]
            return [*answers, _judge(traces)]

        with assemble.watching() as seen:
            work()
        # `_by_stage` приватний навмисно: етап дає число через `measure()`. Тут воно потрібне
        # без прогріву, а такого входу назовні немає — і не має бути.
        cold = sum(assemble._by_stage(seen).values())
        warm = measured(service, traces).worked

print(cold, warm)
"""


def main() -> int:
    done = subprocess.run(
        [sys.executable, "-c", CHILD],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        # Без стелі часу зависання дитячого процесу зависає й розв'язок — мовчки й назавжди.
        timeout=300,
    )
    if done.returncode != 0:
        print(done.stderr.strip()[-2000:])
        return 1

    # Останні два числа, а не всі: банер чи попередження в stdout інакше валили б
    # розв'язок трасуванням замість причини.
    cold, warm = (int(number) for number in done.stdout.split()[-2:])

    print("Вправа 4 · що ховає прогрів")
    print()
    print(f"   холодний вимір (перший виклик у процесі): {cold:>4} рядків")
    print(f"   теплий вимір (так міряє етап):            {warm:>4} рядків")
    print(f"   різниця:                                  {cold - warm:>4} рядків")
    print()
    print("   Різниця — це рядки, які трапляються РАЗ НА ПРОЦЕС: тіла лениво імпортованих")
    print("   модулів. Вони виконуються один раз за весь час життя сервісу, а холодне")
    print("   число списує їх на ОДИН запит.")
    print()
    print("   Напрямок помилки той самий, що на етапі 9: складання виглядає дорожчим,")
    print("   ніж воно є, і теза «частини були зрілі» слабшає без жодної підстави.")
    print()
    print("   Чого цей розв'язок не доводить: що різниця однакова на іншій машині або на")
    print("   іншому наборі сценаріїв. Він доводить, що вона НЕ НУЛЬ — а саме це й ховала")
    print("   перевірка, у якій прогрів уже стався.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
