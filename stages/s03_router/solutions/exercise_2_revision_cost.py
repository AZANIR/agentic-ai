"""Розв'язок вправи 2: скільки коштує цикл ревізій без ліміту.

    python -m stages.s03_router.solutions.exercise_2_revision_cost

Скрипт не міняє `graph.py`. Він рахує **виклики моделі** на один запит при різних лімітах —
і показує те, що в перевірках видно лише як червоний рядок: помилка, яка нічого не ламає.

Ось у чому підступ вправи 2. Прибравши ліміт, ти отримуєш червону перевірку, бо сценарій
підробки скінчився. У продакшні сценарій не кінчається ніколи: там сидить справжня модель,
яка радо відповідатиме стільки разів, скільки її спитають. Жодного винятку, жодного рядка в
логах — лише число в рахунку наприкінці місяця.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from shared.fake_llm import FakeLLM, text
from shared.trace import trace_run
from stages.s02_rag.documents import PUBLIC
from stages.s03_router.graph import run_graph

QUESTION = "скільки днів на повернення товару"

# Ціна за виклик — умовна, порядок величини типовий для середньої моделі станом на 2026 рік.
# Підстав свою: суть не в числі, а в тому, на що воно множиться.
PRICE_PER_CALL = 0.002


class Counting:
    """Клієнт, який рахує виклики. Завжди каже «мало» — тобто supervisor ніколи не задоволений."""

    def __init__(self, route: str = "knowledge") -> None:
        self.calls = 0
        self._inner = FakeLLM(script=[text(route)], repeat_last=False)
        self._route = route

    @property
    def chat(self) -> Any:
        return self

    @property
    def completions(self) -> Any:
        return self

    def create(self, **_: Any) -> Any:
        self.calls += 1
        reply = self._route if self.calls == 1 else "мало"
        return FakeLLM(script=[text(reply)]).chat.completions.create(model="x", messages=[])


def measure(limit: int) -> tuple[int, int, str]:
    """Прогнати граф із заданим лімітом і повернути (виклики, ревізії, причина)."""
    client = Counting()
    with tempfile.TemporaryDirectory() as tmp:
        with trace_run("solution", path=Path(tmp) / "t.jsonl", stage="s03") as tracer:
            state = run_graph(
                QUESTION, access=PUBLIC, client=client, tracer=tracer, revision_limit=limit
            )
    return client.calls, state.revisions, state.finish_reason or "(немає)"


def main() -> int:
    print(f"Запит: «{QUESTION}»")
    print("Supervisor ніколи не задоволений відповіддю — тобто найгірший реальний випадок.\n")
    print("  ліміт   викликів моделі   ревізій   причина завершення   ціна прогону")
    print("  " + "-" * 68)

    for limit in (0, 1, 2, 5, 10):
        calls, revisions, reason = measure(limit)
        print(
            f"  {limit:>5}   {calls:>15}   {revisions:>7}   {reason:<20} "
            f"${calls * PRICE_PER_CALL:.3f}"
        )

    print(f"""
  Читай таблицю уважно: викликів = ліміт + 2. Тобто **кожна ревізія коштує рівно один
  зайвий виклик** — і це найдешевший можливий випадок, бо спеціаліст знань моделі не
  викликає взагалі (він шукає в індексі), а платить тут лише суддя.

  Заміни `knowledge` на `orders` у `Counting()` — і кожна ревізія почне коштувати
  стільки викликів, скільки кроків зробить цикл етапу 1. Множник перестане бути одиницею.

  Тепер найважливіше. Прибери ліміт зовсім (`if False:` у graph.py) — і в цій таблиці
  просто не буде останнього стовпця, бо прогін не завершиться. На підробці ти побачиш
  червону перевірку: сценарій скінчився. На справжній моделі не побачиш **нічого**:

      немає винятку          модель відповідає стільки разів, скільки спитають
      немає рядка в логах    кожне коло виглядає як нормальна робота
      немає тайм-ауту        якщо його не поставив ти

  Єдиний сигнал прийде наприкінці місяця, і він прийде числом ${1000 * PRICE_PER_CALL:.0f}
  за тисячу викликів на **один** запит користувача.

  Це і є той клас помилок, заради якого етап 1 ввів ліміт кроків, а етап 3 повторює його
  для ревізій: **помилка, яка нічого не ламає, — найдорожча.**""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
