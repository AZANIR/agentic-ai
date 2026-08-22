"""Запустити всі перевірки репозиторію. Офлайн, без API-ключа, за секунди.

    python scripts/check_all.py            # усе
    python scripts/check_all.py s01 s03    # лише названі етапи

Кожна перевірка виконується ОКРЕМИМ процесом. Це навмисно: етап, що падає ще на імпорті,
не має вбивати весь прогін — інакше одна зламана залежність (наприклад CrewAI на етапі 9)
ховає результат решти дев'яти.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from shared.check_runner import colors

REPO_ROOT = Path(__file__).resolve().parent.parent

_C = colors()
GREEN, RED, YELLOW = _C["GREEN"], _C["RED"], _C["YELLOW"]
BOLD, DIM, OFF = _C["BOLD"], _C["DIM"], _C["OFF"]


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


def main(argv: list[str]) -> int:
    modules = discover(argv)
    if not modules:
        print(f"{YELLOW}перевірок не знайдено{OFF}")
        print("очікувались shared/check.py і stages/s*_*/check.py")
        return 1

    print(f"{BOLD}check_all · {len(modules)} модул(ів){OFF}")

    failed: list[tuple[str, str]] = []
    total = 0.0
    for module in modules:
        ok, took, output = run_one(module)
        total += took
        mark = f"{GREEN}PASS{OFF}" if ok else f"{RED}FAIL{OFF}"
        print(f"  {mark}  {module} {DIM}({took:.2f} s){OFF}")
        if not ok:
            failed.append((module, output))

    print()
    if failed:
        for module, output in failed:
            print(f"{RED}{'=' * 70}{OFF}")
            print(f"{RED}{module}{OFF}")
            print(f"{RED}{'=' * 70}{OFF}")
            print(output.rstrip())
            print()
        names = ", ".join(module for module, _ in failed)
        print(f"{RED}{BOLD}впало: {names}{OFF}  {DIM}({total:.2f} s){OFF}")
        return 1

    print(f"{GREEN}{BOLD}усе зелене{OFF} {DIM}({len(modules)} модул(ів), {total:.2f} s){OFF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
