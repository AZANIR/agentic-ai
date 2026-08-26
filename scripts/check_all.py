"""Запустити всі перевірки репозиторію. Офлайн, без API-ключа, за секунди.

    python scripts/check_all.py            # усе
    python scripts/check_all.py s01 s03    # лише названі етапи

Кожна перевірка виконується ОКРЕМИМ процесом. Це навмисно: етап, що падає ще на імпорті,
не має вбивати весь прогін — інакше одна зламана залежність (наприклад CrewAI на етапі 9)
ховає результат решти дев'яти.

**Три стани, а не два.** Модуль, який не запустився через невстановлений **опційний** пакет,
позначається `НЕ ПЕРЕВІРЕНО`, а не `FAIL`: базова установка навмисно не тягне важких
бібліотек етапів 3, 4, 6 і 9, і червоніти на цьому означало б вимагати встановити все.

Але зворотна помилка дорожча, і вона вже траплялась: коли `numpy` лежав у extras етапу 2,
хоча `shared/embeddings.py` імпортує його безумовно, CI двічі червонів на `ModuleNotFoundError`
ще до першої перевірки. Якби цей файл тоді вже вмів казати «НЕ ПЕРЕВІРЕНО» на **будь-який**
відсутній пакет, зламана збірка читалась би як «етап не перевіряли». Тому опційність
визначається за `pyproject.toml`, а не за фактом відсутності (ADR-0007).
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path

from shared.check_runner import colors

REPO_ROOT = Path(__file__).resolve().parent.parent

_C = colors()
GREEN, RED, YELLOW = _C["GREEN"], _C["RED"], _C["YELLOW"]
BOLD, DIM, OFF = _C["BOLD"], _C["DIM"], _C["OFF"]

_MISSING = re.compile(r"""ModuleNotFoundError: No module named ['"]([\w.]+)['"]""")
NEWLINE = chr(10)

_DEP_NAME = re.compile(r"""['"]([A-Za-z][\w.-]*)(?:\[[^\]]*\])?\s*[><=!~]""")


def discover(selectors: list[str]) -> list[str]:
    """Знайти модулі перевірок: спершу ядро, далі етапи за номером."""
    modules: list[str] = []
    if (REPO_ROOT / "shared" / "check.py").exists():
        modules.append("shared.check")
    for package in sorted((REPO_ROOT / "stages").glob("s*_*")):
        if (package / "check.py").exists():
            modules.append(f"stages.{package.name}.check")
    if not selectors:
        return modules
    return [m for m in modules if any(s in m for s in selectors)]


def run_one(module: str) -> tuple[bool, float, str]:
    started = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", module],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    took = time.perf_counter() - started
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode == 0, took, output


_BUDGET = re.compile(r"^BUDGET_SECONDS\s*=\s*([0-9.]+)", re.MULTILINE)


def budget_for(module: str) -> float | None:
    """Стеля часу, яку модуль оголосив собі сам. Не оголосив — межі немає.

    Читається текстом, без імпорту: імпорт `check.py` виконав би його імпорти заради
    одного числа. Той самий підхід, що в `optional_packages()`.

    Це **стеля проти розростання**, а не ціль швидкодії. Бюджет ловить одне: перевірку,
    яка непомітно подорожчала вдесятеро. Число в прозі про час має властивість тихо
    розходитися з кодом — на етапі 4 воно розійшлось із 15.9 с до 32 с, і помітили це
    випадково.
    """
    path = REPO_ROOT / (module.replace(".", "/") + ".py")
    found = _BUDGET.search(path.read_text(encoding="utf-8"))
    return float(found.group(1)) if found else None


def optional_packages() -> set[str]:
    """Пакети з `[project.optional-dependencies]` — тобто ті, яких може не бути.

    Читається текстом, без парсера TOML: потрібні лише імена, і залежність заради двох
    рядків regex коштувала б більше за них.
    """
    body = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    parts = body.split("[project.optional-dependencies]", 1)
    if len(parts) < 2:
        return set()
    tail = parts[1].split("\n[tool.", 1)[0]
    return {name.lower().replace("-", "_") for name in _DEP_NAME.findall(tail)}


def unavailable_optional(output: str) -> str | None:
    """Назва відсутнього опційного пакета — або ``None``, якщо причина інша.

    Різниця несуча. «Немає LangGraph» — це нормальний стан базової установки; «немає
    numpy» був зламаною збіркою, бо `shared/` імпортує його безумовно. Обидва виглядають
    однаково у трейсбеку, і розрізняє їх лише таблиця extras.
    """
    found = _MISSING.search(output)
    if not found:
        return None
    package = found.group(1).split(".")[0].lower().replace("-", "_")
    return package if package in optional_packages() else None


def _echo_unverified(output: str) -> None:
    """Показати рядки «НЕ ПЕРЕВІРЕНО» із зеленого модуля.

    Вивід успішного модуля інакше ковтається — і разом із ним зникає єдина ознака, що
    щось лишилось невиконаним. CI-крок, який шукає це слово, промахувався б завжди.
    """
    for line in output.splitlines():
        if "НЕ ПЕРЕВІРЕНО" in line or line.lstrip().startswith("—"):
            print(f"{YELLOW}{line.rstrip()}{OFF}")


# Перевірки, яким дозволено лишатись третім станом у повному оточенні, і причина
# кожної. Порожній словник означав би «третіх станів не буває» — а вони бувають, і
# частина з них не закривається ніколи: прогін проти справжнього HTTPS-домену потребує
# живої машини, а не пакета.
#
# Числа сюди КОПІЮЮТЬСЯ З ПРОГОНУ, як `expect_failed` у mutations.json. Руками писати
# їх не можна: запис, вигаданий з голови, стверджує про перевірку, якої ніхто не бачив.
#
# Ключ — модуль, значення — {назва перевірки: причина}. Розбіжність в БУДЬ-ЯКИЙ бік
# валить збірку. Зайвий третій стан — регрес. Запис, який більше не збігається, —
# теж: перевірка почала проходити, а реєстр досі обіцяє, що вона мовчить.
#
# Реєстр описує ОДНЕ оточення — те, що піднімає робота `optional-extras`: її extras,
# її сервіси, її інтерпретатор. На іншій машині набір буде інший, і це не помилка:
# перевірка, чиє число зміряне на 3.14, мовчить на 3.13 і навпаки. Тому `--strict-
# unverified` призначений для тієї роботи, а не для щоденного локального прогону —
# і саме тому скарга друкує готовий блок, а не просто «не збіглося».
ALLOWED_UNVERIFIED: dict[str, dict[str, str]] = {}

_UNVERIFIED_HEAD = re.compile(r"\d+ перевірок пройшли, \d+ НЕ ПЕРЕВІРЕНО:")
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def unverified_names(output: str) -> list[str]:
    """Назви перевірок, що лишились третім станом, із підсумкового блоку модуля.

    Береться саме підсумок, а не рядки по ходу прогону: у підсумку назва чиста, а по
    ходу до неї дописано причину в дужках, і причина змінюється з оточенням. Ключ, що
    залежить від оточення, зробив би реєстр нестабільним рівно там, де він потрібен.
    """
    names: list[str] = []
    collecting = False
    for raw in output.splitlines():
        line = _ANSI.sub("", raw).rstrip()
        if _UNVERIFIED_HEAD.search(line):
            collecting = True
            continue
        if not collecting:
            continue
        stripped = line.strip()
        if stripped.startswith("—"):
            names.append(stripped.lstrip("—").strip())
        elif stripped:
            break
    return names


def compare_unverified(actual: dict[str, list[str]]) -> str | None:
    """Звірити третій стан із реєстром. Повертає скаргу або None, якщо збіглося."""
    lines: list[str] = []
    for module in sorted(set(actual) | set(ALLOWED_UNVERIFIED)):
        allowed = ALLOWED_UNVERIFIED.get(module, {})
        seen = set(actual.get(module, []))
        for name in sorted(seen - set(allowed)):
            lines.append(f"  ЗАЙВИЙ  {module} · {name}")
        for name in sorted(set(allowed) - seen):
            lines.append(f"  ЗАСТАРІЛИЙ  {module} · {name}")
    if not lines:
        return None

    block = ["", f"{RED}{BOLD}третій стан розійшовся з реєстром{OFF}", *lines, ""]
    block.append("Готовий до вставки блок за цим прогоном — причину впиши сам:")
    block.append("ALLOWED_UNVERIFIED = {")
    for module in sorted(actual):
        if not actual[module]:
            continue
        block.append(f'    "{module}": {{')
        for name in actual[module]:
            was = ALLOWED_UNVERIFIED.get(module, {}).get(name, "<причина>")
            block.append(f'        "{name}": "{was}",')
        block.append("    },")
    block.append("}")
    return "\n".join(block)


def lint() -> tuple[bool, str]:
    """Лінт і формат — тими самими командами, що у CI.

    Раніше `check_all` їх не запускав, і локальна команда відрізнялась від CI на два
    кроки. Наслідок передбачуваний: перевірки зелені, пуш, CI червоний на довгому рядку
    — і виправлення коштує повного циклу замість двох секунд.

    Гейт, який відрізняється від того, що вирішує, — це не гейт, а репетиція.
    """
    import shutil

    # Поруч із поточним Python, потім у PATH. Голе `ruff` знаходиться у CI й не
    # знаходиться у venv на Windows — а гейт, що падає від власного запуску, вимикають.
    ruff = shutil.which("ruff", path=str(Path(sys.executable).parent)) or shutil.which("ruff")
    if ruff is None:
        return True, ""

    problems = []
    for command in ([ruff, "check", "."], [ruff, "format", "--check", "."]):
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            problems.append(" ".join(command) + ":" + NEWLINE + (result.stdout or result.stderr))
    return not problems, NEWLINE.join(problems)


def main(argv: list[str]) -> int:
    strict = "--strict-unverified" in argv
    modules = discover([arg for arg in argv if arg != "--strict-unverified"])
    if not modules:
        print(f"{YELLOW}перевірок не знайдено{OFF}")
        print("очікувались shared/check.py і stages/s*_*/check.py")
        return 1

    clean, complaint = lint()
    if not clean:
        print(f"{RED}лінт{OFF}")
        print(complaint.rstrip())
        print()

    print(f"{BOLD}check_all · {len(modules)} модул(ів){OFF}")

    failed: list[tuple[str, str]] = []
    skipped: list[tuple[str, str]] = []
    unverified: list[str] = []
    third_states: dict[str, list[str]] = {}
    total = 0.0
    for module in modules:
        ok, took, output = run_one(module)
        total += took

        missing = None if ok else unavailable_optional(output)
        if missing:
            skipped.append((module, missing))
            print(f"  {YELLOW}—{OFF}     {module} {DIM}(немає {missing}){OFF}")
            continue

        limit = budget_for(module)
        if ok and limit is not None and took > limit:
            ok = False
            output += f"""

БЮДЖЕТ ЧАСУ: {took:.1f} с при стелі {limit} с.
Перевірки пройшли, але подорожчали. Або зменш вартість, або підніми
BUDGET_SECONDS свідомо — і онови число в NFR тим самим рухом.
"""

        mark = f"{GREEN}PASS{OFF}" if ok else f"{RED}FAIL{OFF}"
        print(f"  {mark}  {module} {DIM}({took:.2f} s){OFF}")
        if not ok:
            failed.append((module, output))
        elif "НЕ ПЕРЕВІРЕНО" in output:
            unverified.append(output)
            third_states[module] = unverified_names(output)

    print()
    if failed or not clean:
        for module, output in failed:
            print(f"{RED}{'=' * 70}{OFF}")
            print(f"{RED}{module}{OFF}")
            print(f"{RED}{'=' * 70}{OFF}")
            print(output.rstrip())
            print()
        names = ", ".join(module for module, _ in failed)
        print(f"{RED}{BOLD}впало: {names}{OFF}  {DIM}({total:.2f} s){OFF}")
        return 1

    for output in unverified:
        _echo_unverified(output)
    if skipped:
        names = ", ".join(f"{module} (немає {package})" for module, package in skipped)
        print(f"{YELLOW}{BOLD}НЕ ПЕРЕВІРЕНО: {names}{OFF}")

    if strict:
        complaint = compare_unverified(third_states)
        if complaint:
            print(complaint)
            return 1

    green = len(modules) - len(skipped)
    print(f"{GREEN}{BOLD}усе зелене{OFF} {DIM}({green} модул(ів), {total:.2f} s){OFF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
