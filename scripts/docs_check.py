"""Прогнати валідатори документів по всіх етапах одразу.

    python scripts/docs_check.py          # усі етапи
    python scripts/docs_check.py s05      # лише один

Три валідатори (`spec_check`, `tasks_check`, `mermaid_check`) беруть по одному етапу за
виклик — і це правильно для них самих, бо кожен друкує деталі саме про свій документ. Але
перед закриттям етапу треба прогнати всі три по всіх етапах, а це дев'ять команд, які легко
недорахувати.

Дев'ять команд, які пишуться руками, — це дев'ять нагод забути одну. Скрипт тут не заради
зручності, а заради того, щоб «прогнав валідатори» означало те саме щоразу.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURES = REPO_ROOT / "docs" / "features"

RED, GREEN, DIM, OFF = "\033[31m", "\033[32m", "\033[2m", "\033[0m"


def slugs(selector: str | None) -> list[str]:
    """Етапи з `docs/features/`, крім службового `_scaffold`."""
    found = sorted(p.name for p in FEATURES.iterdir() if p.is_dir() and not p.name.startswith("_"))
    return [s for s in found if selector is None or selector in s]


def run(script: str, *args: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / script), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0, (result.stdout or "") + (result.stderr or "")


def main(selector: str | None = None) -> int:
    failed: list[tuple[str, str]] = []
    for slug in slugs(selector):
        feature = FEATURES / slug
        # Етап у роботі має spec.md і ще не має tasks.json — це стан конвеєра, а не збій.
        # Валідатор, що падає трейсбеком на нормальному стані, привчає ігнорувати червоне.
        jobs: list[tuple[str, list[str]]] = [("spec_check.py", [slug])]
        if (feature / "tasks.json").exists():
            jobs.append(("tasks_check.py", [slug]))
        for document in ("sad.md", "spec.md"):
            if (feature / document).exists():
                jobs.append(("mermaid_check.py", [str(feature / document)]))

        for script, args in jobs:
            ok, output = run(script, *args)
            label = f"{slug} · {script.removesuffix('.py')}"
            if args and args[0].endswith(".md"):
                label += f" ({Path(args[0]).name})"
            mark = f"{GREEN}ok{OFF}" if ok else f"{RED}ЗБІЙ{OFF}"
            print(
                f"  {mark:<12} {label} {DIM}{output.strip().splitlines()[0] if output else ''}{OFF}"
            )
            if not ok:
                failed.append((label, output))

    print()
    for label, output in failed:
        print(f"{RED}{'=' * 70}{OFF}")
        print(f"{RED}{label}{OFF}")
        print(output.rstrip())
        print()

    if failed:
        print(f"{RED}збоїв: {len(failed)}{OFF}")
        return 1
    print(f"{GREEN}документи валідні в усіх етапах{OFF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
