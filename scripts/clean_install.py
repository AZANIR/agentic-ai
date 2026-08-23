"""Прогнати перевірки так, ніби опційні пакети не встановлені — тобто як у CI.

    python scripts/clean_install.py              # без усіх опційних пакетів
    python scripts/clean_install.py langgraph    # без названих

Навіщо. Локальний venv накопичує пакети «десь по дорозі»: щось поставив, щоб подивитись,
щось притягнулось як залежність. Після цього `check_all.py` зелений, а чиста установка не
запускається взагалі — і дізнаєшся ти про це з CI, уже після пуша.

Саме так репозиторій отримав два червоні прогони поспіль: `numpy` лежав у extras етапу 2,
хоча `shared/embeddings.py` імпортує його безумовно. Локально numpy стояв, тож нічого не
було видно (ADR-0007).

Як це працює: у `sys.meta_path` ставиться фіндер, який кидає `ImportError` на названі пакети.
Він переживає підпроцеси, бо ставиться через `sitecustomize.py` на `PYTHONPATH` — інакше
`check_all.py`, який запускає кожен модуль окремим процесом, нічого б не помітив.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_DEP_NAME = re.compile(r"""['"]([A-Za-z][\w.-]*)(?:\[[^\]]*\])?\s*[><=!~]""")

_SITECUSTOMIZE = """
import os
import sys

_blocked = {p for p in os.environ.get("BLOCK_IMPORTS", "").split(",") if p}


class _Blocker:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in _blocked:
            raise ImportError(f"пакет {name!r} заблоковано: симуляція чистої установки")
        return None


if _blocked:
    sys.meta_path.insert(0, _Blocker())
"""


def optional_packages() -> set[str]:
    """Імена з `[project.optional-dependencies]` — усе, чого може не бути в чистій установці."""
    body = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    parts = body.split("[project.optional-dependencies]", 1)
    if len(parts) < 2:
        return set()
    tail = parts[1].split("\n[tool.", 1)[0]
    names = {name.lower().replace("-", "_") for name in _DEP_NAME.findall(tail)}
    # `dev` і `psycopg` ставляться в CI, тож блокувати їх означало б симулювати не CI.
    return names - {"ruff", "psycopg"}


def main(argv: list[str]) -> int:
    blocked = sorted(argv) if argv else sorted(optional_packages())
    print(f"Симуляція чистої установки. Заблоковано: {', '.join(blocked)}\n")

    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8")
        environment = {
            **os.environ,
            "PYTHONPATH": tmp + os.pathsep + os.environ.get("PYTHONPATH", ""),
            "BLOCK_IMPORTS": ",".join(blocked),
        }
        result = subprocess.run(
            [sys.executable, "scripts/check_all.py"], cwd=REPO_ROOT, env=environment
        )

    print()
    if result.returncode == 0:
        print("Чиста установка проходить. Те, що позначене НЕ ПЕРЕВІРЕНО, у CI покриває")
        print("окрема робота з extras — див. .github/workflows/ci.yml.")
    else:
        print("Чиста установка НЕ проходить. Пакет, якого бракує, або має бути в ядрі,")
        print("або імпортуватись усередині функції, а не на рівні модуля (ADR-0007).")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
