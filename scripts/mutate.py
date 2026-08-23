"""Мутаційний прогін: зламати код навмисно й подивитись, ЯКІ перевірки червоніють.

    python scripts/mutate.py s03            # усі мутації етапу
    python scripts/mutate.py s03 --expect   # ще й звірити з числами, обіцяними у вправах

Навіщо окремий інструмент, а не три рядки на місці. Ці три рядки писалися шість разів і
двічі підвели — обидва рази **мовчки**:

**Раз.** Заміна числа на число тієї ж довжини й відкат за ту саму секунду лишають чинним
старий `.pyc`: Python звіряє час зміни з точністю до секунди й розмір файлу. Перевірка
падала на вже поверненому коді.

**Два.** Прогін убили між записом мутації та відкотом — і файл лишився зламаним. Набір
почав зависати, а `git status` показував лише мої ж незакомічені правки, тож нічого
підозрілого в ньому не було видно.

Звідси три властивості цього скрипта, і кожна з них — наслідок конкретної втрати часу:

    відкат у `finally`     переживає Ctrl+C і kill між записом і відновленням
    маркер на диску        наступний запуск відмовиться стартувати на зламаному дереві
    лічильник виконаних    «мутація не спіймана» і «набір не запустився» — різні речі

Останнє важливіше, ніж здається. Харнес, який шукає рядки `FAIL`, на зламаному імпорті не
знаходить жодного — і рапортує «0 червоних» для мутації, яка насправді знесла весь модуль.
Інструмент, яким перевіряють, чи не бреше перевірка, збрехав тим самим способом.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKER = REPO_ROOT / ".mutation-in-progress"
PYTHON = sys.executable


def _clear_bytecode() -> None:
    """Почистити кеш байткоду. Лише наш код — `.venv` тут ні до чого й коштує хвилин."""
    for root in ("stages", "shared", "scripts"):
        for cache in (REPO_ROOT / root).rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def _run_checks(module: str) -> tuple[int, list[str]]:
    """Прогнати набір і повернути (скільки перевірок виконалось, які впали)."""
    result = subprocess.run(
        [PYTHON, "-m", module],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO_ROOT,
        timeout=180,
    )
    output = result.stdout + result.stderr
    executed = len(re.findall(r"^  (?:ok|FAIL|—) ", output, re.M))
    failed = [line.strip() for line in re.findall(r"^  FAIL\s+(.+)$", output, re.M)]
    return executed, failed


def apply_one(path: Path, old: str, new: str, module: str, floor: int) -> dict:
    """Накласти одну мутацію, прогнати набір, відкотити **завжди**."""
    original = path.read_text(encoding="utf-8")
    if old not in original:
        return {"error": f"текст мутації не знайдено у {path.name}"}
    if original.count(old) > 1:
        return {"error": f"текст мутації трапляється {original.count(old)} разів — неоднозначно"}

    MARKER.write_text(str(path), encoding="utf-8")
    try:
        _clear_bytecode()
        path.write_text(original.replace(old, new, 1), encoding="utf-8")
        executed, failed = _run_checks(module)
    finally:
        path.write_text(original, encoding="utf-8")
        _clear_bytecode()
        MARKER.unlink(missing_ok=True)

    if executed < floor:
        return {
            "error": (
                f"набір виконав лише {executed} перевірок із очікуваних {floor} — "
                "мутація зламала імпорт, і «жодної червоної» тут нічого не означає"
            )
        }
    return {"executed": executed, "failed": failed}


def load_plan(stage: str) -> dict:
    path = REPO_ROOT / "stages" / _package(stage) / "mutations.json"
    if not path.exists():
        raise SystemExit(f"немає {path.relative_to(REPO_ROOT)} — етап не описав своїх мутацій")
    return json.loads(path.read_text(encoding="utf-8"))


def _package(stage: str) -> str:
    matches = sorted((REPO_ROOT / "stages").glob(f"{stage}_*"))
    if not matches:
        raise SystemExit(f"немає етапу {stage}")
    return matches[0].name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", help="префікс етапу, напр. s03")
    parser.add_argument("--expect", action="store_true", help="звірити з обіцяними числами")
    args = parser.parse_args(argv)

    if MARKER.exists():
        raise SystemExit(
            f"попередній прогін не завершився: {MARKER.read_text(encoding='utf-8')} міг "
            f"лишитись зміненим.\nПеревір `git diff`, відкоти й прибери {MARKER.name}."
        )

    plan = load_plan(args.stage)
    module = f"stages.{_package(args.stage)}.check"
    floor = plan["executed_floor"]
    print(f"Мутаційний прогін · {module} · очікуваний мінімум виконаних: {floor}\n")

    mismatches = 0
    for mutation in plan["mutations"]:
        path = REPO_ROOT / mutation["file"]
        outcome = apply_one(path, mutation["old"], mutation["new"], module, floor)
        name = mutation["name"]

        if "error" in outcome:
            print(f"  ЗБІЙ  {name}\n        {outcome['error']}")
            mismatches += 1
            continue

        failed = outcome["failed"]
        expected = mutation.get("expect_failed")
        mark = " "
        if args.expect and expected is not None and len(failed) != expected:
            mark, mismatches = "!", mismatches + 1
        print(
            f"  {mark} {name}: червоних {len(failed)}"
            + (f" (у вправі обіцяно {expected})" if mark == "!" else "")
        )
        for label in failed:
            print(f"        -> {label}")

    if args.expect:
        print()
        if mismatches:
            print(f"РОЗБІЖНОСТЕЙ: {mismatches}. Числа у вправах не збігаються з прогоном.")
            return 1
        print("Усі числа у вправах збігаються з прогоном.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
