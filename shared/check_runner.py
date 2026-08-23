"""Мінімальний раннер перевірок. Не фреймворк — і це свідомо (ADR-0006).

Кожен ``check.py`` описує функції-перевірки на голих ``assert`` і закінчується так:

    if __name__ == "__main__":
        raise SystemExit(run_checks([check_happy_path, check_step_limit], title="Етап 1"))

Правило етапу: серед перевірок має бути щонайменше одна на РЕЖИМ ВІДМОВИ.
Зелений щасливий шлях не доводить нічого про те, що станеться, коли піде не так.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from collections.abc import Callable


def colors() -> dict[str, str]:
    """ANSI-кольори лише коли вивід іде в термінал.

    У CI та в перехопленому виводі escape-послідовності перетворюються на сміття,
    крізь яке не видно причини падіння — а саме тоді лог найпотрібніший.
    """
    enabled = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    names = {"GREEN": "32", "RED": "31", "YELLOW": "33", "BOLD": "1", "DIM": "2"}
    if not enabled:
        return dict.fromkeys([*names, "OFF"], "")
    return {**{k: f"\033[{v}m" for k, v in names.items()}, "OFF": "\033[0m"}


_C = colors()
GREEN, RED, YELLOW, DIM, OFF = _C["GREEN"], _C["RED"], _C["YELLOW"], _C["DIM"], _C["OFF"]


class NotVerified(Exception):
    """Перевірку не виконано, і це не те саме, що «пройшла».

    Буває, коли для перевірки бракує чогось необов'язкового — не встановленої бібліотеки,
    відсутнього сервісу. Спокуса зробити `return` і лишити зелений вердикт велика, і
    саме через неї зелений набір починає означати менше, ніж здається: **різниця між
    «збіглося» і «не перевіряли» зникає з виводу**.

    Тут вона не зникає: такий вердикт рахується окремо, друкується жовтим і потрапляє в
    підсумковий рядок. Прогін від нього не червоніє — але й не вдає, що все перевірено.
    """


def run_checks(checks: list[Callable[[], None]], *, title: str) -> int:
    """Виконати перевірки по черзі. Повертає код виходу: 0 — жодна не впала."""
    print(f"\n{title}")
    print("-" * len(title))

    failures: list[tuple[str, str]] = []
    skipped: list[str] = []
    for check in checks:
        name = check.__name__
        summary = (check.__doc__ or "").strip().splitlines()
        label = summary[0] if summary else name
        started = time.perf_counter()
        try:
            check()
        except NotVerified as reason:
            skipped.append(label)
            print(f"  {YELLOW}—{OFF}     {label} {DIM}({reason}){OFF}")
        except Exception:
            failures.append((name, traceback.format_exc()))
            print(f"  {RED}FAIL{OFF}  {label}")
        else:
            took = (time.perf_counter() - started) * 1000
            print(f"  {GREEN}ok{OFF}    {label} {DIM}({took:.0f} ms){OFF}")

    passed = len(checks) - len(failures) - len(skipped)
    if failures:
        for name, tb in failures:
            print(f"\n{RED}--- {name} ---{OFF}\n{tb}")
        print(f"{RED}{len(failures)} з {len(checks)} перевірок впали{OFF}")
        return 1

    if skipped:
        print(f"{GREEN}{passed} перевірок пройшли{OFF}, {YELLOW}{len(skipped)} НЕ ПЕРЕВІРЕНО{OFF}:")
        for label in skipped:
            print(f"  {YELLOW}—{OFF} {label}")
        return 0

    print(f"{GREEN}усі {len(checks)} перевірок пройшли{OFF}")
    return 0
