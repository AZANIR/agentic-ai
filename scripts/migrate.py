"""Мінімальний раннер міграцій: пронумеровані .sql і таблиця обліку.

    python scripts/migrate.py status      # що застосовано, що чекає
    python scripts/migrate.py up          # застосувати всі непримінені
    python scripts/migrate.py down        # відкотити останню
    python scripts/migrate.py down --all  # відкотити все

Чому не Alembic. Alembic розв'язує задачу автогенерації діфів зі змін ORM-моделей.
Тут ORM немає і схема змінюється рідко — тож він додав би шар, який читачеві довелося б
вивчати, не отримавши натомість нічого. Момент переходу видно чітко: коли писати SQL
руками почне дратувати. До того — ці 130 рядків роблять усе, що треба.

Кожна міграція — пара файлів:
    migrations/0001_init.up.sql
    migrations/0001_init.down.sql
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "migrations"
FILENAME = re.compile(r"^(?P<version>\d{4})_(?P<name>[a-z0-9_]+)\.(?P<direction>up|down)\.sql$")

BOOTSTRAP = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    text        PRIMARY KEY,
    name       text        NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);
"""


@dataclass(frozen=True)
class Migration:
    version: str
    name: str
    up: Path
    down: Path

    def __str__(self) -> str:
        return f"{self.version}_{self.name}"


def discover() -> list[Migration]:
    """Зібрати пари up/down. Міграція без пари — помилка, а не попередження."""
    if not MIGRATIONS_DIR.exists():
        return []
    halves: dict[tuple[str, str], dict[str, Path]] = {}
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        match = FILENAME.match(path.name)
        if not match:
            raise SystemExit(
                f"неочікуване ім'я файлу: {path.name}\n"
                "очікується NNNN_name.up.sql або NNNN_name.down.sql"
            )
        key = (match["version"], match["name"])
        halves.setdefault(key, {})[match["direction"]] = path

    migrations = []
    for (version, name), pair in sorted(halves.items()):
        missing = {"up", "down"} - pair.keys()
        if missing:
            raise SystemExit(
                f"міграція {version}_{name} неповна: немає {', '.join(sorted(missing))}.sql\n"
                "міграція без відкату — це міграція, яку не можна безпечно застосувати"
            )
        migrations.append(Migration(version, name, pair["up"], pair["down"]))
    return migrations


def connect():
    """Підключитися до БД або впасти з поясненням, а не з трейсбеком."""
    from shared.config import settings

    if not settings.database_url:
        raise SystemExit(
            "DATABASE_URL не заданий.\n"
            "Підніми локальну БД:  docker compose -f deploy/docker-compose.yml up -d --wait\n"
            "і скопіюй .env.example у .env (там уже є робочий DATABASE_URL)."
        )
    try:
        import psycopg
    except ImportError:
        raise SystemExit('psycopg не встановлений. Постав його: pip install -e ".[dev]"') from None

    # connect_timeout обов'язковий, а не косметичний: без нього неправильний хост
    # висить безкінечно, і причина лишається невідомою. Краще впасти за 10 секунд
    # із поясненням.
    try:
        return psycopg.connect(settings.database_url, autocommit=False, connect_timeout=10)
    except Exception as exc:
        hint = ""
        if "localhost" in settings.database_url:
            hint = (
                "\n\nПідказка: у DATABASE_URL стоїть 'localhost'. Постав 127.0.0.1.\n"
                "Docker публікує порт лише на IPv4, а localhost резолвиться спершу\n"
                "в ::1 (IPv6) — клієнт іде туди, слухача немає, підключення висить."
            )
        raise SystemExit(
            f"не вдалося підключитися до {settings.database_url}:\n  {exc}{hint}"
        ) from None


def applied_versions(conn) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(BOOTSTRAP)
        cur.execute("SELECT version FROM schema_migrations")
        return {row[0] for row in cur.fetchall()}


def _run(conn, migration: Migration, direction: str) -> None:
    """Виконати одну міграцію в одній транзакції: або вся, або жодна."""
    sql_file = migration.up if direction == "up" else migration.down
    with conn.cursor() as cur:
        cur.execute(sql_file.read_text(encoding="utf-8"))
        if direction == "up":
            cur.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                (migration.version, migration.name),
            )
        else:
            cur.execute("DELETE FROM schema_migrations WHERE version = %s", (migration.version,))
    conn.commit()
    arrow = "->" if direction == "up" else "<-"
    print(f"  {arrow} {migration}")


def cmd_status() -> int:
    migrations = discover()
    with connect() as conn:
        done = applied_versions(conn)
    if not migrations:
        print("міграцій немає")
        return 0
    for migration in migrations:
        mark = "застосовано" if migration.version in done else "чекає"
        print(f"  [{mark:>11}] {migration}")
    pending = [m for m in migrations if m.version not in done]
    print(f"\nвсього {len(migrations)}, чекає {len(pending)}")
    return 0


def cmd_up() -> int:
    with connect() as conn:
        done = applied_versions(conn)
        pending = [m for m in discover() if m.version not in done]
        if not pending:
            print("нічого застосовувати — схема актуальна")
            return 0
        print(f"застосовую {len(pending)}:")
        for migration in pending:
            _run(conn, migration, "up")
    return 0


def cmd_down(all_of_them: bool) -> int:
    with connect() as conn:
        done = applied_versions(conn)
        applied = [m for m in discover() if m.version in done]
        if not applied:
            print("нічого відкочувати")
            return 0
        targets = list(reversed(applied)) if all_of_them else [applied[-1]]
        print(f"відкочую {len(targets)}:")
        for migration in targets:
            _run(conn, migration, "down")
    return 0


def main(argv: list[str]) -> int:
    command = argv[0] if argv else "status"
    if command == "status":
        return cmd_status()
    if command == "up":
        return cmd_up()
    if command == "down":
        return cmd_down(all_of_them="--all" in argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
