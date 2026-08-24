"""Стан і метрики: два ендпоінти, що відповідають на **різні** питання.

    стан      чи сервіс і кожна його залежність працюють ПРЯМО ЗАРАЗ
    метрики   скільки чого сталося за період і якого саме роду

**Жоден із них не відповідає на питання «чому агент так вирішив».** На нього відповідає трейс,
і плутати їх — найдорожча помилка спостережуваності: метрика скаже, що 3 % запитів відхилено,
і не скаже, чому саме ці три.

**Стан називає кожну залежність окремо.** «Сервіс живий» без переліку — це відповідь, після
якої монітор мовчить, поки користувач не поскаржиться: процес справді живий, просто база
недоступна вже годину.

**Стан відкритий, метрики закриті.** Стан читає зовнішній монітор, у якого ключа немає й не
має бути; тому він не називає ні версій, ні адрес, ні рядків підключення — лише імена
залежностей і їхній стан. Метрики закриті, бо агрегати теж розкривають: кількість запитів на
клієнта — це бізнес-інформація.

**Метрики — теж стан у пам'яті процесу.** Це третє обличчя причини з ADR-0002: за N воркерів
видача показує зріз одного з них. Тут це названо вголос, а не лишено читачеві як сюрприз;
багатопроцесний збирач — те, що робить продакшн, і він поза межами етапу.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

UP = "up"
DOWN = "down"


@dataclass
class Dependency:
    """Одна зовнішня залежність і спосіб спитати, чи вона жива."""

    name: str
    probe: Any

    def check(self) -> tuple[str, str]:
        """Стан і причина. Причина порожня, коли все гаразд."""
        try:
            self.probe()
        except Exception as error:  # noqa: BLE001 — будь-яка відмова означає «недоступна»
            # Тип помилки, а не її текст: текст psycopg несе адресу, користувача й порт,
            # а стан читає той, у кого ключа немає.
            return DOWN, type(error).__name__
        return UP, ""


@dataclass
class Health:
    """Стан сервісу. `ok` — лише коли **всі** залежності живі."""

    dependencies: list[Dependency] = field(default_factory=list)

    def report(self) -> dict[str, Any]:
        seen = {
            name: {"status": status, "reason": reason}
            for name, (status, reason) in ((d.name, d.check()) for d in self.dependencies)
        }
        return {
            "status": UP if all(d["status"] == UP for d in seen.values()) else DOWN,
            "dependencies": seen,
        }


@dataclass
class Metrics:
    """Лічильники подій. Типи відмов розрізняються — інакше метрика нічого не радить.

    Метрика «3 % запитів відхилено» однаково описує зламану автентифікацію, зловживання й
    вичерпаний бюджет. Це три різні події з трьома різними діями оператора, і зливати їх в
    одне число означає віддавати монітору те, за чим не можна діяти.
    """

    requests: Counter = field(default_factory=Counter)
    traces: int = 0

    def request(self, kind: str) -> None:
        self.requests[kind] += 1

    def trace_written(self) -> None:
        self.traces += 1

    def render(self) -> str:
        """Стандартний текстовий формат витягування: рядок на зразок, коментар на метрику."""
        lines = [
            "# HELP s06_requests_total Оброблені запити за родом результату.",
            "# TYPE s06_requests_total counter",
        ]
        for kind, count in sorted(self.requests.items()):
            lines.append(f's06_requests_total{{kind="{kind}"}} {count}')
        lines += [
            "# HELP s06_traces_total Записані трейси.",
            "# TYPE s06_traces_total counter",
            f"s06_traces_total {self.traces}",
        ]
        return "\n".join(lines) + "\n"
