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
from pathlib import Path


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


def code_mentions(source: str, words: set[str]) -> list[str]:
    """Чи згадує **код** ці слова. Проза модуля не рахується.

    Перевірка виду «модуль X не має знати про Y» природно пишеться як пошук у тексті —
    і природно червоніє на власному docstring, де про Y саме й застерігають. У цьому
    курсі так сталося **чотири рази**: годинник на етапі 5, профіль і бюджет на етапі 6,
    маркери даних на етапі 2.

    Тому помічник спільний: розбір AST бачить імена, атрибути й рядкові літерали, що
    беруть участь в обчисленні, і не бачить ані docstring, ані коментарів.

    :returns: перелік згадок виду ``рядок N: імʼя``; порожній перелік означає «чисто».
    """
    import ast

    tree = ast.parse(source)
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }

    found = []
    for node in ast.walk(tree):
        seen = None
        if isinstance(node, ast.Name):
            seen = node.id
        elif isinstance(node, ast.Attribute):
            seen = node.attr
        elif isinstance(node, ast.arg):
            seen = node.arg
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            seen = node.value
        if seen is None:
            continue
        lowered = seen.lower()
        for word in words:
            if word in lowered:
                found.append(f"рядок {node.lineno}: {seen!r}")
                break
    return found


def require_intact_source(name: str) -> None:
    """Відмовитись міряти файл, який зараз навмисно зламано мутаційним прогоном.

    Перевірка розміру модуля реагує на будь-яку правку, тож під час мутації вона дає
    червоне, яке нічого не означає. Гірше: воно розчиняє сигнал. «Червоних 2» замість
    «червоних 1» читається як «спіймали двічі», хоча друга перевірка стверджує про
    бюджет рядків, а не про властивість, яку мутація ламає.

    :raises NotVerified: якщо триває мутаційний прогін саме цього файлу.
    """
    marker = Path(__file__).resolve().parent.parent / ".mutation-in-progress"
    if not marker.exists():
        return
    mutated = marker.read_text(encoding="utf-8").strip()
    if mutated.endswith(name):
        raise NotVerified(f"{name} зараз зламано навмисно — бюджет рядків не міряється")


def require_tag(tag: str) -> None:
    """Переконатися, що теґ доступний, або чесно сказати, що перевірку не виконано.

    Перевірки «нижній етап не змінено» звіряються з теґом попереднього етапу. У свіжому
    клоні його може не бути: `actions/checkout` тягне неглибоку історію **без теґів**, і
    `git diff stage-02` там падає з `bad revision`.

    Це не збій коду й не привід червоніти — це відсутній вхідний матеріал, тобто рівно
    той стан, заради якого існує `NotVerified`. Але сам по собі він недостатній: якщо теґів
    немає ніде, перевірка не виконається ніколи. Тому CI тягне повну історію
    (`fetch-depth: 0`), і там вона справді працює.
    """
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{tag}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise NotVerified(f"немає теґа {tag} — потрібна повна історія: git fetch --tags")
