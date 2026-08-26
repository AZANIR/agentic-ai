"""Звірка статті з кодом, який вона описує (PLAYBOOK §8).

    python scripts/article_check.py                     # усі статті
    python scripts/article_check.py three_guards        # одна, за частиною імені
    python scripts/article_check.py --facts s01         # що взагалі можна звірити для етапу

Навіщо окремий скрипт. Досі звірка писалася **наново для кожної статті** й лишалася в
скретчпаді сесії. Наслідок не в незручності: дві статті, звірені різними наборами тверджень,
не можна порівняти між собою, а звірка, яку не можна повторити, — це не звірка, а спогад про
неї.

Стаття посилається на **теґ**, не на `main`, і саме тому все тут читається з теґа через
`git show`. Число, обчислене на теперішньому коді, описувало б не ту статтю: код рухається
далі, стаття лишається на місці, і розбіжність між ними — не помилка статті.

## П'ять вимірів

    frontmatter   обов'язкові поля й межі zod-схеми artstroy
    attribution   жодних згадок асистента — правило репозиторію
    links         посилання ведуть на теґ, теґ існує, файл існує НА ТОМУ теґу
    snippets      фрагменти коду присутні у справжньому файлі на тому ж теґу
    claims        числа мають назване джерело, і джерело перераховується

**Числа — головний вимір, і він єдиний необов'язковий.** Поруч зі статтею може лежати
`claims.json`: перелік `{що, скільки, звідки}`. Кожен рядок каже, яким обчисленням число
береться, — і скрипт це обчислення виконує. Без файлу вимір чесно каже `НЕ ПЕРЕВІРЕНО`, а не
зелено: «числа не звірялись» і «числа збіглися» — різні стани.

Звіряються **три** сторони, не дві: число мусить стояти в тексті статті, збігатися з тим, що
дає обчислення на теґу, і мати назване джерело. Перша редакція цього файлу брала обидві
половини з теґа — і ловила рівно нуль, бо порівнювала дві копії одного джерела. Той самий
клас вади, що ловився на етапах 8, 9 і 10.

## Чого цей скрипт не робить

- Не читає мережу. Стаття береться з репозиторію блога, код — з теґа цього репозиторію.
- Не судить прозу. Він звіряє те, що має джерело: посилання, фрагменти, числа з `claims.json`.
- Не знає, чи фрагмент **спрощений навмисно**. Незнайдений фрагмент — це знахідка, яку автор
  або виправляє, або декларує в тексті поруч зі сніпетом.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Статті живуть у репозиторії блога — там їх публікують, і там же лежать їхні
# `claims.json`. Друга копія тут означала б, що звіряється те, що нікуди не йде.
BLOG = Path(os.environ.get("ARTSTROY_REPO", REPO_ROOT.parent / "artstroy"))
ARTICLES = BLOG / "src" / "content" / "articles"

RED, GREEN, YELLOW, DIM, OFF = (
    "\033[31m",
    "\033[32m",
    "\033[33m",
    "\033[2m",
    "\033[0m",
)

# Межі zod-схеми artstroy. Копія, і це названо: схема живе в іншому репозиторії, тож
# єдиний спосіб не розійтися — тримати числа в одному місці й правити їх разом.
BOUNDS = {"title": 80, "description": 180, "lede": 280}
REQUIRED = ("isDraft", "title", "description", "cover", "category", "authors", "publishedTime")

# Згадки асистента заборонені всюди, що йде назовні (правило репозиторію).
FORBIDDEN = (
    "claude",
    "copilot",
    "chatgpt",
    "gpt-4",
    "co-authored-by",
    "generated with",
    "згенеровано з",
    "ai-асистент",
)

# Маркер режиму відмови в docstring перевірки. Обидва, і це не хвіст сумісності:
# репозиторій переїхав на англійську (ADR-0008), а теґи переписати неможливо — на
# `stage-01`..`stage-10` назавжди лишається старий маркер. Лічильник, що знає лише новий,
# показав би нуль на кожному теґу й оголосив би розбіжність у семи статтях із десяти.
FAILURE_MARKERS = ("FAILURE", "ВІДМОВА")

FRONTMATTER = re.compile(r"^---\n(?P<body>.*?)\n---\n", re.DOTALL)
FIELD = re.compile(r"^(?P<key>[a-zA-Z_]+):\s*(?P<value>.*?)\s*$", re.MULTILINE)
REPO_LINK = re.compile(
    r"https://github\.com/[^/]+/[^/)\s]+/(?:tree|blob)/(?P<ref>[^/)\s]+)/(?P<path>[^)\s#]+)"
)
ANY_REPO_LINK = re.compile(r"https://github\.com/[^)\s]+")
FENCE = re.compile(r"```(?P<lang>[a-z]*)\n(?P<code>.*?)```", re.DOTALL)


@dataclass
class Report:
    """Що дала звірка однієї статті."""

    slug: str
    tag: str = ""
    problems: list[str] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        return not self.problems


def git(*args: str) -> tuple[int, str]:
    """Виклик git. Повертає код і вивід — падіння тут не є падінням звірки."""
    done = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return done.returncode, done.stdout


def at_tag(tag: str, path: str) -> str | None:
    """Вміст файлу НА ТЕҐУ, або `None`, якщо його там немає."""
    code, out = git("show", f"{tag}:{path}")
    return out if code == 0 else None


def tag_exists(tag: str) -> bool:
    return git("rev-parse", "--verify", f"refs/tags/{tag}")[0] == 0


def frontmatter(text: str) -> dict[str, str]:
    found = FRONTMATTER.match(text)
    if found is None:
        return {}
    return {m["key"]: m["value"].strip('"') for m in FIELD.finditer(found["body"])}


def check_frontmatter(text: str, report: Report) -> None:
    """Обов'язкові поля й межі схеми. Стаття без них не збереться в блозі."""
    meta = frontmatter(text)
    if not meta:
        report.problems.append("frontmatter не знайдено — стаття не збереться")
        return
    for key in REQUIRED:
        report.checked += 1
        if key not in meta:
            report.problems.append(f"frontmatter: немає обов'язкового поля {key!r}")
    for key, limit in BOUNDS.items():
        if key not in meta:
            continue
        report.checked += 1
        if len(meta[key]) > limit:
            report.problems.append(f"frontmatter: {key} — {len(meta[key])} символів, межа {limit}")


def check_attribution(text: str, report: Report) -> None:
    """Жодних згадок асистента. Правило стосується всього, що йде назовні."""
    lowered = text.lower()
    for token in FORBIDDEN:
        report.checked += 1
        if token in lowered:
            line = next(
                (n for n, s in enumerate(text.split("\n"), 1) if token in s.lower()),
                0,
            )
            report.problems.append(f"атрибуція: рядок {line} містить {token!r}")


def check_links(text: str, report: Report) -> None:
    """Посилання ведуть на теґ, теґ існує, і файл існує САМЕ НА ТОМУ теґу.

    Читач за півроку має побачити код, який стаття описує. Посилання на `main` це не дає:
    воно показує те, що там опинилось потім.
    """
    all_links = set(ANY_REPO_LINK.findall(text))
    tagged = {(m["ref"], m["path"]) for m in REPO_LINK.finditer(text)}

    for link in sorted(all_links):
        if "/main/" in link or link.endswith("/main"):
            report.checked += 1
            report.problems.append(f"посилання на `main`, а не на теґ: {link}")

    tags = {ref for ref, _ in tagged}
    for tag in sorted(tags):
        report.checked += 1
        if not tag.startswith("stage-"):
            report.problems.append(f"посилання веде на {tag!r} — це не теґ етапу")
        elif not tag_exists(tag):
            report.problems.append(f"теґа {tag!r} не існує в репозиторії")
    if len(tags) == 1:
        report.tag = tags.pop()
    elif len(tags) > 1:
        report.problems.append(f"стаття посилається на кілька теґів: {sorted(tags)}")

    for ref, path in sorted(tagged):
        report.checked += 1
        if not tag_exists(ref):
            continue
        clean = path.rstrip("/")
        if at_tag(ref, clean) is None and git("cat-file", "-e", f"{ref}:{clean}")[0] != 0:
            report.problems.append(f"на теґу {ref} немає шляху {clean!r}")


def check_snippets(text: str, report: Report, claims: dict) -> None:
    """Фрагменти коду присутні у справжньому файлі на тому ж теґу.

    Порівняння за **нормалізованими пробілами**: стаття переносить рядки інакше, і різниця
    у відступах не є розбіжністю зі змістом.

    **Спрощення дозволені — але названі.** Фрагмент, що ілюструє форму, а не цитує файл,
    оголошується в `claims.json` разом із причиною. Це та сама вимога, що до рішень в
    `ARCHITECTURE.md`: або джерело, або названа причина, чому джерела немає. Мовчазний
    виняток перетворив би звірку на прикрасу — і саме тому виняток без причини є вадою.
    """
    declared = {item["starts"]: item.get("why", "") for item in claims.get("simplified", [])}
    if not report.tag:
        report.unverified.append("фрагменти: стаття не називає теґа — нема з чим звіряти")
        return

    code, listing = git("ls-tree", "-r", "--name-only", report.tag)
    if code != 0:
        report.unverified.append(f"фрагменти: дерево теґа {report.tag} недоступне")
        return
    sources = {
        name: at_tag(report.tag, name) or "" for name in listing.split("\n") if name.endswith(".py")
    }
    haystack = {name: " ".join(body.split()) for name, body in sources.items()}

    for block in FENCE.finditer(text):
        if block["lang"] != "python":
            continue
        needle = " ".join(block["code"].split())
        if len(needle) < 80:
            # Короткі фрагменти — це ілюстрація форми, а не цитата з файлу.
            continue
        report.checked += 1
        if any(needle in body for body in haystack.values()):
            continue
        head = block["code"].strip().splitlines()[0]
        excuse = next((why for starts, why in declared.items() if head.startswith(starts)), None)
        if excuse:
            continue
        if excuse == "":
            report.problems.append(f"спрощення {head[:50]!r} оголошено без причини")
            continue
        report.problems.append(
            f"фрагмент не знайдено на теґу {report.tag}: {head[:60]!r} — "
            "виправ або оголоси спрощення в `claims.json` разом із причиною"
        )


# --- числа та їхні джерела -----------------------------------------------------------------


def _checks_in(source: str) -> list[ast.FunctionDef]:
    """Функції-перевірки з `check.py`, узяті з КОДУ, а не з переліку імен."""
    tree = ast.parse(source)
    listed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "CHECKS" for t in node.targets
        ):
            listed = {e.id for e in ast.walk(node.value) if isinstance(e, ast.Name)}
    return [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in listed]


def _executable_lines(source: str) -> int:
    """Виконувані рядки: без імпортів і рядків документації. Той самий спосіб, що в етапах."""
    tree = ast.parse(source)
    return len(
        {
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.stmt)
            and not isinstance(node, (ast.Import, ast.ImportFrom))
            and not (
                isinstance(node, ast.Expr) and isinstance(getattr(node.value, "value", None), str)
            )
        }
    )


def compute(how: str, *, tag: str, stage: str, file: str = "") -> int | None:
    """Обчислити число на теґу. `None` — джерело недоступне, а не нуль."""
    folder = _stage_folder(tag, stage)
    if folder is None:
        return None
    if how in ("checks", "failure_modes"):
        source = at_tag(tag, f"{folder}/check.py")
        if source is None:
            return None
        found = _checks_in(source)
        if how == "checks":
            return len(found)
        return sum(1 for f in found if (ast.get_docstring(f) or "").startswith(FAILURE_MARKERS))
    if how == "executable_lines":
        source = at_tag(tag, f"{folder}/{file}")
        return None if source is None else _executable_lines(source)
    if how in ("mutations", "mutation_red"):
        raw = at_tag(tag, f"{folder}/mutations.json")
        if raw is None:
            return None
        items = json.loads(raw)["mutations"]
        if how == "mutations":
            return len(items)
        return sum(int(m.get("expect_failed", 0)) for m in items)
    if how == "adrs":
        code, listing = git("ls-tree", "--name-only", f"{tag}:docs/features")
        if code != 0:
            return None
        feature = next((n for n in listing.split("\n") if n.startswith(f"{stage}-")), None)
        if feature is None:
            return None
        code, files = git("ls-tree", "--name-only", f"{tag}:docs/features/{feature}/adr")
        return None if code != 0 else sum(1 for n in files.split("\n") if n.endswith(".md"))
    if how == "exercises":
        # Ранні етапи не мали `mutations.json` узагалі: вправи жили лише в прозі. Рахувати
        # їх звідти — не милиця, а єдине джерело, яке на тому теґу існувало.
        source = at_tag(tag, f"{folder}/exercises.md")
        if source is None:
            return None
        return sum(1 for line in source.split("\n") if line.startswith("## Вправа"))
    return None


def _stage_folder(tag: str, stage: str) -> str | None:
    code, listing = git("ls-tree", "--name-only", f"{tag}:stages")
    if code != 0:
        return None
    for name in listing.split("\n"):
        if name.startswith(f"{stage}_"):
            return f"stages/{name}"
    return None


WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
}


def _spelled(value: int) -> set[str]:
    """Як число може бути записане в тексті: цифрами й словами, з дефісом і без."""
    forms = {str(value)}
    if value in WORDS:
        forms.add(WORDS[value])
    tens, ones = divmod(value, 10)
    if 20 <= value < 100 and ones and tens * 10 in WORDS:
        forms.add(f"{WORDS[tens * 10]}-{WORDS[ones]}")
        forms.add(f"{WORDS[tens * 10]} {WORDS[ones]}")
    return forms


def check_claims(text: str, report: Report, claims: dict) -> None:
    """Числа статті проти їхніх джерел — і проти самої статті.

    Трикутник, а не пара. `expect` мусить **цитуватися в тексті**, інакше твердження описує
    вже не ту статтю: досить поправити прозу й забути файл, і звірка знову доводитиме, що
    дві копії однакові. Перша редакція цього файлу брала обидві половини з теґа й ловила
    саме нуль — та сама тавтологія, що ловилась на етапах 8, 9 і 10.

    Без `claims.json` вимір каже `НЕ ПЕРЕВІРЕНО`, а не зелено.
    """
    if not claims:
        report.unverified.append(
            "числа: немає `claims.json` — жодне число статті не має названого джерела"
        )
        return

    tag = claims.get("tag") or report.tag
    if not tag:
        report.problems.append("claims: теґ не названо ні у файлі, ні в посиланнях статті")
        return

    lowered = text.lower()
    for item in claims.get("numbers", []):
        report.checked += 1
        if not any(form in lowered for form in _spelled(item["expect"])):
            report.problems.append(
                f"число {item['what']!r}: {item['expect']} у тексті статті не зустрічається — "
                "твердження описує вже не цю статтю"
            )
            continue
        got = compute(item["how"], tag=tag, stage=item["stage"], file=item.get("file", ""))
        if got is None:
            report.unverified.append(f"число {item['what']!r}: джерело недоступне на теґу {tag}")
            continue
        if got != item["expect"]:
            report.problems.append(
                f"число {item['what']!r}: у статті {item['expect']}, на теґу {tag} — {got}"
            )


def review(folder: Path) -> Report:
    report = Report(slug=folder.name)
    text = (folder / "index.mdx").read_text(encoding="utf-8")
    path = folder / "claims.json"
    claims = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    check_frontmatter(text, report)
    check_attribution(text, report)
    check_links(text, report)
    check_snippets(text, report, claims)
    check_claims(text, report, claims)
    return report


def facts(stage: str, tag: str) -> None:
    """Що взагалі можна звірити для етапу — щоб `claims.json` писався не навмання."""
    print(f"Що можна звірити для {stage} на теґу {tag}:")
    print()
    for how in ("checks", "failure_modes", "mutations", "mutation_red"):
        got = compute(how, tag=tag, stage=stage)
        print(f"   {how:<18} {got if got is not None else '—'}")
    folder = _stage_folder(tag, stage)
    if folder is None:
        return
    _, listing = git("ls-tree", "--name-only", f"{tag}:{folder}")
    print()
    print("   executable_lines:")
    for name in sorted(listing.split("\n")):
        if name.endswith(".py") and name not in ("__init__.py", "check.py", "run.py"):
            got = compute("executable_lines", tag=tag, stage=stage, file=name)
            print(f"      {name:<22} {got if got is not None else '—'}")


def main(selector: str | None = None) -> int:
    if selector == "--facts":
        stage = sys.argv[2] if len(sys.argv) > 2 else "s01"
        facts(stage, f"stage-{stage[1:]}")
        return 0

    if git("rev-parse", "--git-dir")[0] != 0:
        print(f"{YELLOW}НЕ ПЕРЕВІРЕНО{OFF} · git недоступний — статті звіряються з теґами")
        return 0
    if not ARTICLES.exists():
        print(f"{YELLOW}НЕ ПЕРЕВІРЕНО{OFF} · репозиторію блога немає за {BLOG}.")
        print(f"{DIM}   Постав його поруч або назви шлях у ARTSTROY_REPO.{OFF}")
        return 0

    folders = [
        p
        for p in sorted(ARTICLES.iterdir())
        if p.is_dir()
        and (p / "index.mdx").exists()
        and (p / "claims.json").exists()
        and (selector is None or selector in p.name)
    ]
    if not folders:
        print(f"{YELLOW}НЕ ПЕРЕВІРЕНО{OFF} · жодної статті не знайдено для {selector!r}")
        return 0

    print(f"Звірка статей із кодом · {len(folders)} шт.")
    print()
    broken = []
    for folder in folders:
        report = review(folder)
        mark = f"{GREEN}ok{OFF}  " if report.ok else f"{RED}ЗБІЙ{OFF}"
        tail = f"{DIM}теґ {report.tag or '—'} · тверджень {report.checked}{OFF}"
        print(f"  {mark} {report.slug:<46} {tail}")
        for line in report.unverified:
            print(f"      {YELLOW}—{OFF} {line}")
        if not report.ok:
            broken.append(report)

    print()
    for report in broken:
        print(f"{RED}{'=' * 70}{OFF}")
        print(f"{RED}{report.slug}{OFF}")
        for line in report.problems:
            print(f"  · {line}")
        print()

    if broken:
        print(f"{RED}статей із розбіжностями: {len(broken)} з {len(folders)}{OFF}")
        return 1
    print(f"{GREEN}усі статті збігаються з кодом на своїх теґах{OFF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else None))
