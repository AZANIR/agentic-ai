# Playbook — how a stage gets made

A working document. It records **exactly how** a stage of the course is built: the sequence,
the gates, the criteria, and the lessons that have already cost us mistakes. The goal is
simple — so that stage 2 does not have to be reinvented, and stage 7 does not repeat stage 1's
mistakes.

[CONVENTIONS.md](CONVENTIONS.md) says **how to write the code**. This file says **how to drive
a stage to done**.

> Where the numbers come from: stage 1, taken all the way through, independent review included.
> The record: [`_review/review-2026-08-23.md`](docs/features/s01-agent-loop/_review/review-2026-08-23.md).

---

## 1. The stage pipeline

Nine steps. Only the ones explicitly marked skippable may be skipped.

| # | Step | Command | Artefact |
|---|---|---|---|
| 1 | Specification | `/sdd:specify sNN-slug` | `spec.md`, `.size`, `.route` |
| 2 | Clarification | `/sdd:clarify sNN-slug` | an updated `spec.md` |
| 3 | Architecture | `/sdd:design sNN-slug --depth=easy` | `sad.md`, `adr/*.md` |
| 4 | Test plan | `/sdd:plan-tests sNN-slug` | `## Test plan` inline in `spec.md` |
| 5 | Tasks | `/sdd:tasks sNN-slug` | `tasks.json`, `tasks/`, `tracker.md` |
| 6 | Implementation | `/sdd:implement sNN-slug` | code + checks + commits |
| 7 | **Review** | `/sdd:review sNN-slug` | `_review/review-YYYY-MM-DD.md` |
| 8 | Fixes | — | MAJORs closed, MINORs deferred into §8 |
| 9 | Tag + article | `git tag stage-NN` | the tag, `sources/artstroy/{slug}/index.mdx` |

**Auto-skips on the `quick` route** (size XS/S), each with its reason stated:
`sequences` — when SAD §6 already carries the critical flows · `data-model` — when the schema
does not change · `api` — when there is no contract · `screens` — when `target_surfaces` names
no UI.

**What may never be skipped:** step 7. The reason is in §4.

## 2. A realistic budget

Measured on stage 1 (size S).

| Phase | Share |
|---|---|
| Documents (steps 1–5) | ~35% |
| Code and checks (step 6) | ~30% |
| **Review and fixes (7–8)** | **~25%** |
| Article (step 9) | ~10% |

Plan on the basis that **code and tests are about half the work**. The other half is proving
they do what you think they do. On stage 1 the review found seven MAJORs **after** everything
was green and declared finished.

## 3. Definition of Done

A stage is finished when **every** item holds. Not "the code works".

1. `README.md`: what you will be able to do after the stage → the canonical idea → the bridge
   to NovaShop → what to break.
2. `README.md` opens with an orientation block that fits one screen.
3. `python -m stages.sNN_slug.run` works **with no API key**.
4. `python -m stages.sNN_slug.check` is green offline; at least one check covers a **failure
   mode**.
5. `exercises.md` (3–5 tasks with expected results) + `solutions/` + `CHECKLIST.md`.
6. New terms added to [GLOSSARY.md](GLOSSARY.md).
7. Status updated in [CURRICULUM.md](CURRICULUM.md) and in the root README.
8. **Review passed, every MAJOR closed**, MINORs deferred with an owner and a due date.
9. Tag `stage-NN` created and pushed; the article written and linking to the tag.

Stages 6 and 10 additionally: `deploy/smoke.sh` passes against a real HTTPS URL.

## 4. The review gate is mandatory

**Two independent reviewers in clean context, in parallel.** Not one, and not whoever wrote the
code.

| Stage | What it looks for |
|---|---|
| 1 | Tracing US → AC → `file:line` of code → the check function. Separately: ACs **not claimed** by the `SDD-AC` trailers. Recomputing every numeric NFR by hand |
| 2 | Conventions taken literally, edge cases, security, whether the tests have teeth, whether the teaching text contradicts the code |

### Why two, and why not the author

An author checks the code against **their own model of what the code should do**. If the idea
itself is wrong, that is invisible from the inside: the tests were written by the same head and
they agree with the code. Both are wrong together.

On stage 1 the confirmation gate worked exactly as designed — per generation. That a
per-generation gate turns confirmation into blanket permission was seen only by a clean context.

The split into two stages is not a formality either. Stage 1 runs **from spec to code** and
finds what is **missing** — a requirement nobody implemented; it cannot be seen by looking at
the code, because it is not there. Stage 2 runs **from code to consequences** and finds what is
there but breaks at the edge. A single reviewer almost always slides into the second pass: code
is concrete, and a missing requirement is silent.

### Resolving findings

Each one is **Fix** / **Defer** (owner plus due date in §8 of the spec) / **Not an issue**
(with the reason). No open stage-1 finding ships.

## 5. Lessons already paid for in mistakes

Each one comes from a real event on stages 1–3. Re-read them before every stage.

### A file that has been read is not proof that it runs

Two independent reviewers in clean context read `ws.py`, traced the criterion to its line, and
described what happens there. Live mode had meanwhile not worked **once since the day it was
written**: `from __future__ import annotations` turned the socket annotation into a string, the
type was imported inside a factory, and FastAPI, unable to resolve the name, treated the socket
as a query parameter. Every connection closed before `accept()`.

The first run found it, a minute after both reviews finished.

Why nobody found it earlier: **every check for that module read it as text.** That was done
deliberately and correctly, so the suite would not drag a web framework into the base install.
And precisely because of it, the module executed nowhere, CI included.

**Rule:** if a module's checks only **read** it, at least one has to **run** it. No optional
package — `NOT EVALUATED`, and the extras job then applies the "nothing is left unverified"
rule. Reading proves intent; running proves fact.

### An invariant with two terms where there are three participants stays green and lies

"The sum of the steps equals the total time" is true while the pipeline owns the clock alone.
The moment a consumer takes fragments at its own pace, its pause lands silently on the **next**
step. Measured: a model that slept 750 ms reported 2750, and the sum still added up perfectly.

The most expensive step became whichever one the browser happened to think after — and that is
exactly the one a reader would go and optimise.

**Rule:** a sum invariant has to name **every** owner of time, and the remainder "attributed to
nobody" has to be checked separately against zero. Plus the mirror half: not only "the sum adds
up" but "this share equals how long that participant actually worked". Without the second half,
conservation is satisfied even when someone else's time was booked to a named step.

**Aside:** `total` must not be computed as the sum of its parts — that turns the law into an
identity and it stops catching a step nobody measured.

### Boundary arithmetic is checked across several input sizes, not one

p95 was taken as `round(0.95·n)` instead of `ceil(0.95·n)`. At a hundred runs the two formulas
agree — and the check stood at exactly a hundred. At thirty, p95 landed on the fastest run with
6.7 % worse than it, and `tail_ratio` dropped below one: "there is no tail". They disagree on 95
of the first 200 sample sizes.

**Rule:** a check on a formula using `round`, `ceil`, `//` or a slice runs a **list** of sizes,
not one. A single size is one happy point, and it is almost always happy, because it was chosen
while looking at the code.

### An instruction that punishes obedience is worse than no instruction

`pip install -e ".[voice]"`, and on the next line `uvicorn ...`. The `voice` extra held model
weights and no web package at all. A reader who installed **nothing** got a polite "install
this" message; a reader who installed it got `command not found`, and before that a
`ModuleNotFoundError` from a file that did not exist in the repository.

Same class: the documented `uvicorn ...:create_app --factory` brought up the **fake** mode,
because `--factory` cannot pass arguments.

**Rule:** commands quoted in a lesson are checked against the manifest — the named extra exists
and brings what the next line calls; the named factory enables the mode the prose claims.

### "The fake cannot produce X by construction" is a virtue, not an excuse

The criterion demanded "a hundred runs **with a spread of latencies**". A fake clock produces no
spread — that is its whole value. So the distribution was typed in as literals, and the demo
printed "runs: 100" for a hand-written list, on a stage whose thesis is that only what is
measured can be optimised.

The way out is neither to make the clock non-deterministic nor to rewrite the criterion. The
spread belongs in **another layer**: the model's delay became a pure function of the run number.
A hundred real runs, a real tail, and a repeat run gives the same hundred numbers.

**Rule:** when the "Given" cannot occur because of a property of the fake, look for the layer
where that property can be introduced deterministically. Literals in a test satisfy the "Then"
and not the "Given" — and it is usually the "Then" that gets checked.

**Aside:** a tail made of one tier makes p95 equal to the worst case. Two tiers, and the
difference between "almost worst" and "worst" is visible again.

### A mutation test proves the test reacts — not that it reacts **to that**

I disabled the gate, saw red, and declared it proven. In fact the check was failing with
`FakeLLMError: script exhausted` — it never reached the assertion. A test with the right verdict
and the wrong cause **passes mutation testing**, which means it looks reliable by exactly the
criterion used to judge it.

**Rule:** after a mutation, read the **cause** of the failure, not only the fact of it. If it is
not an `AssertionError` with meaningful text, the test does not prove what you think.

**Aside:** the fake's script has to contain a step **after** the one being checked. Otherwise a
disabled guard leads to an exhausted script instead of a fired assertion.

### Defaults at a trust boundary are fail-closed only

The unknown-field check worked only when the schema's author remembered
`additionalProperties: false`. All three of our tools had it, so nothing went red — and the
exercise asks the reader to add a fourth.

**Rule:** a guard that works only when switched on is an understanding, not a trust boundary.

### A backup lives outside the system you are rewriting

Before `git filter-branch` I made `git tag backup-before-rewrite`. `filter-branch` dutifully
rewrote **the tag itself**, and the local copies of the articles were gone for good.

**Rule:** `cp -r` into a directory outside the repository **before** the first destructive
command. A backup inside the thing you are rewriting is not a backup.

**Aside:** `filter-branch` leaves the originals in `refs/original/`, and `git rev-list --all`
still sees them. Without `update-ref -d` plus `gc --prune=now` they would have gone out in the
push.

### `ruff format` rewrites code inside markdown

It turns the fragment `description="x",` into `description = ("x",)` — in isolation that really
is valid Python (a tuple assignment). A lesson full of fragments is prose, not code for the
compiler.

**Rule:** `extend-exclude = ["*.md"]` in `[tool.ruff]`. Already done.

### `localhost` resolves to IPv6 first

Docker publishes the port on IPv4 only. Measured: IPv4 connects in 26 ms, IPv6 refuses after
2041 ms.

**Rule:** `127.0.0.1` in every connection string, plus a `connect_timeout` in the connector.

### Heuristics in tests break on inflected languages

Twice in a row: `"Kyiv" in weather` (the language inflects — "in Kyiv" becomes a different word
form) and `"'" not in reason` as an indicator of a dumped structure (the word for "required"
contains an apostrophe).

**Rule:** check what actually matters — the content, the structural brackets, the specific
fields — rather than an indirect sign that happened to correlate.

### Numbers in prose are derived from code, not typed

In an article draft I showed the trace call shorter than it is. The defect lived four minutes,
until the first automatic check of the snippet against the file.

**Rule:** every number and every fragment in an article is verified by script against the
repository. The verification is in §8.

### When the line budget is reached, extract a module rather than raise the budget

`loop.py` stood at 116/120, and the review fixes added about 13 lines. The mitigation was
written into `sad.md` §11 **in advance** — the gate moved out into `gate.py` and the budget
stayed intact.

**Rule:** a risk with a mitigation written down beforehand is not an emergency; it is the plan
working.

### A test that "the bad thing did not happen" never replaces a test that "the good thing did"

Stage 2. The access filter has to sit **before** the top-k selection. Put it after, and an
internal document takes a slot, gets removed afterwards, and the asker receives "nothing found"
instead of the correct answer that was ranked third.

**Nothing leaked. The leak check stays green.** What disappears is the permitted answer — and
there was no check for that until I wrote one separately.

The same failure recurred within the same stage by a different mechanism: dropping
`partial(search_knowledge_base, access=access)` causes no leak (the `PUBLIC` default is
fail-safe), but the operator stops seeing what they are allowed to see. Again no leak check
fired.

**Rule:** for every "the forbidden thing did not get through" check, write its mirror — "the
permitted thing arrived". These are different claims, and covering one gives a false sense that
both are covered.

### Видимість дефекту може залежати від параметра, який до дефекту стосунку не має

Та сама вада з фільтром **не проявляється взагалі** при `top_k=3`: правильна відповідь ще
влазить у трійку разом із двома внутрішніми фрагментами, і обидва порядки дають однакову
видачу. При `top_k=2` видача стає порожньою. Код зламаний однаково; змінюється лише те, чи це
видно — і вирішує це параметр, який до контролю доступу не належить.

Перевірка, написана «як у продакшні» (з `top_k=3`), була б зеленою на зламаному коді.

**Правило:** параметр у перевірці, підібраний так, щоб властивість стала спостережною, — не
штучність, а частина доказу. Записувати **чому саме це значення** там, де стоїть перевірка,
інакше наступний рефакторинг «підправить під продакшн» і мовчки знеструмить її.

### Ассерт із правильним вердиктом і слабким твердженням

Перша версія перевірки форми інструмента писала `"query" in params["properties"]`. Мутація,
що додає `access` у схему — тобто рівно те, від чого ця перевірка мала захищати, — проходила
її наскрізь. Зелена перевірка, зламана властивість.

**Правило:** для властивості «рівно оце й нічого більше» ассерт має бути `list(...) == [...]`,
а не `x in ...`. «Серед іншого є» і «тільки» — різні твердження.

### Мутаційний прогін може отруїти байткод-кеш

Заміна `0.2` на `0.0` і повернення назад **за ту саму секунду** лишає чинним старий `.pyc`:
Python звіряє час зміни з точністю до секунди й розмір файлу, а вони збіглися. Перевірка
падала на вже поверненому коді, і хвилина пішла на пошук неіснуючого баґа.

**Правило:** мутаційний харнес чистить `__pycache__` після відкату. Те саме попередження —
у `exercises.md` кожного етапу, бо читач робить рівно ці мутації.

### Ruff ловить несумісність із підлогою версій, якої локальний прогін не бачить

`f"...{list(params["properties"])}"` — вкладені однакові лапки в f-string дозволені з Python
3.12. Локально стоїть 3.14, тому все працювало; підлога репозиторію `>=3.11`, і матриця CI
містить 3.11. Впало б у CI, не в мене.

**Правило:** `ruff check` — не косметика й не про стиль. Ганяти його перед кожним комітом, а не
перед пушем.

### Мутаційний харнес мусить доводити, що набір узагалі запустився

Етап 2. Мутація зламала синтаксис файлу — і харнес відрапортував **«0 червоних»** для всіх
шести мутацій підряд. Він шукав рядки `FAIL` у виводі; коли модуль не імпортується, таких
рядків немає жодного, і «нічого не впало» невідрізненне від «усе гаразд».

Тобто інструмент, яким перевіряють, чи не бреше перевірка, збрехав рівно тим самим способом.

**Правило:** харнес рахує, **скільки перевірок виконалось**, і кричить, якщо їх менше, ніж
має бути. Без цього «мутація не спіймана» і «мутація зламала збірку» — той самий вивід.

### Правка через `sed` із `\n` у заміні вставляє справжній перенос рядка

Те саме тричі за етап: `\n` усередині Python-рядка, написаного всередині bash-рядка,
обробляється двічі й доїжджає до файлу переносом. Найдорожчий випадок зламав f-string
і запустив попередній урок.

**Правило:** для правок коду, що містять `\n`, — редагування за індексом рядка або окремий
файл у скретчпаді, ніколи не текстова заміна через дві оболонки.

### Перевірка на витік мусить спершу ствердити, що прогін відбувся

Етап 3, третій випадок тієї самої форми за три етапи. Перевірка «текст запиту не підвищує
рівень доступу» була зеленою на мутації, яка **ламала спеціаліста**: він падав, `safely()`
це ловив, прогін завершувався збоєм — і нічого не витекло, бо не сталося нічого взагалі.

Форма загальна: **«погане не сталося» істинне й тоді, коли не сталося нічого.** Збій, порожня
видача, виняток, обірваний маршрут — усе це проходить перевірку на витік.

**Правило:** перевірка на заборонене починається з твердження, що дозволене відбулося —
`finish_reason == "answered"`, видача непорожня, крок виконано. Лише після цього має сенс
питати, чи не витекло. Інакше найнадійніший спосіб пройти перевірку безпеки — зламати код.

### Перевірка, що охороняє константу, не має ітерувати цю ж константу

Етап 3. Перевірка незмінності `access` була написана так:

```python
for name in sorted(FROZEN):
    ...assert setattr впав...
```

Спорожни `FROZEN` — і тіло циклу не виконається жодного разу. Набір лишається **повністю
зеленим**, доки двері стоять відчинені. Гірше: урок наказував читачеві саме цю мутацію
(«прибери `FROZEN`»), а `exercises.md` — іншу (`if name in FROZEN:` → `if False:`), і та
давала червоне. **Дві інструкції на ту саму вправу з протилежним результатом.**

**Правило:** перевірка стверджує склад константи явно (`assert FROZEN == {...}`), а поведінку
— за іменем поля, не через ітерацію того, що перевіряє. Інакше мутація «список порожній»
проходить крізь перевірку, яка існує саме проти неї.

### «НЕ ПЕРЕВІРЕНО» мусить бути окремим станом, інакше зелений набір бреше

Перевірка порівняння двох реалізацій робила `return`, коли необовʼязкова бібліотека не
встановлена, — і мала вердикт `ok`. Тобто «збіглося» і «не перевіряли» друкувалися однаково.
У CI бібліотека не ставилась ніколи, тож єдиний запобіжник проти розходження двох реалізацій
не виконувався ніде, а пайплайн був зелений.

**Правило:** третій стан у раннері (`NotVerified`), окремий лічильник у підсумку — і окрема
робота в CI, яка ставить extras і **падає**, якщо хоч щось лишилось невиконаним. Без другої
половини перший стан просто задокументує, що нічого не перевіряється.

### Мутація, що не компілюється, дає найпереконливіші хибні числа

Замір «вправа 3 → дев'ять червоних перевірок» був неправильний: мутація писала `access=PUBLIC`
у модуль, де `PUBLIC` не імпортований. `NameError` ловився `safely()`, кожен запит ставав
`specialist_failed`, і червоніло дев'ять перевірок замість трьох. Число виглядало солідно,
розбір під ним пояснював зовсім інший механізм — і суперечив сам собі за два абзаци.

**Правило:** мутаційний харнес перевіряє, що змінений файл **імпортується**, перш ніж рахувати
червоне. Заміри для вправ робляться рівно тим текстом, який написано у вправі, і копіюються
з прогону, а не переказуються.

### Мутаційний харнес — інструмент репозиторію, а не три рядки на місці

Ті три рядки писалися шість разів і підвели тричі, щоразу мовчки: старий `.pyc` після
відкату за ту саму секунду; убитий прогін, що лишив файл зламаним; замір на мутації, яка
не компілювалась. Тепер це `scripts/mutate.py` із відкотом у `finally`, маркером на диску
й лічильником виконаних перевірок.

Головне в ньому — не зручність, а `--expect`: числа, обіцяні у вправах, лежать у
`stages/<етап>/mutations.json`, і прогін **падає**, коли проза розійшлася з фактом.

**Правило:** жодне число «стільки-то перевірок почервоніє» не пишеться в урок руками.
Воно копіюється з прогону й закріплюється в `mutations.json`.

### Лінтер може зробити інструкцію у вправі невиконуваною

Вправа 3 наказувала написати `access=PUBLIC` — а `ruff --fix` прибрав цей імпорт як
невикористаний, бо ним ніщо не користувалось. Читач, який виконав інструкцію дослівно,
отримував `NameError`, який ловився `safely()`, і бачив десять червоних перевірок замість
трьох — усі з неправильної причини.

**Правило:** мутація у вправі не має потребувати нічого, чого немає у файлі. Літерал
(`access="public"`) замість константи; і `--expect` це ловить, бо міряє рівно той текст,
який написано у вправі.

### Локальний venv — не CI, і різниця не видна доти, доки не запушиш

`numpy` лежав у extras етапу 2, хоча `shared/embeddings.py` імпортує його **безумовно**, а
`shared/check.py` — перевірки ядра — його виконують. CI ставить `[dev]`. Обидві роботи матриці
впали на `ModuleNotFoundError` **до першої перевірки**, обидві версії Python однаково.

Локально нічого не було видно: numpy стояв у venv, бо його притягнув етап 2. До моменту, коли
причину назвали, етап 3 уже тягнув numpy транзитивно — наступний пуш дав би три упалі модулі
замість двох.

**Правило:** пакет, який спільний шар імпортує на рівні модуля, є залежністю **ядра**, хоч би
що казала таблиця extras. Перед пушем — `python scripts/clean_install.py`: блокатор імпортів
у `sys.meta_path` через `sitecustomize.py`, щоб він пережив підпроцеси. Двадцять рядків, і
цей клас закритий цілком.

### «Не перевіряли» не має ховати «зламано»

Спокуса після попереднього уроку — навчити прогін рахувати будь-яку смерть на імпорті як
`НЕ ПЕРЕВІРЕНО`. Це зробило б CI зеленим на тому самому баґу, який його червонив: зламана
збірка читалась би як «етап просто не запускали».

**Правило:** опційність визначається за `pyproject.toml`, а не за фактом відсутності. Немає
`langgraph` (є в extras) — «НЕ ПЕРЕВІРЕНО». Немає `numpy` (у ядрі) — `FAIL`, код виходу 1.
У трейсбеку вони виглядають однаково, і розрізняє їх лише таблиця залежностей.

### Крок CI, що шукає слово у виводі, мусить мати це слово у виводі

`check_all.py` друкував вивід модуля лише в гілці «впало». Модуль, що завершився успішно,
свої рядки `НЕ ПЕРЕВІРЕНО` втрачав — тож `grep -q` у CI промахувався **завжди**, і робота
лишалась зеленою незалежно ні від чого. Правило формально було; воно було сліпе.

**Правило:** написавши крок, який щось шукає, перевір руками, що шукане взагалі з'являється
у виводі. Найдешевше — прогнати той самий `grep` локально й побачити ненульовий результат
хоча б раз.

### Перевірка, що читає історію git, у CI читає іншу історію

`actions/checkout` робить **неглибокий клон без теґів**. Перевірки «нижній етап не змінено»
звіряються з теґом попереднього етапу — і в CI падали з `fatal: bad revision 'stage-02'`,
хоча локально працювали бездоганно.

Це той самий клас, що й невстановлений пакет: перевірка не має вхідного матеріалу. І ліки
ті самі, обидві половини:

    fetch-depth: 0    щоб у CI вона справді виконувалась
    NotVerified       щоб у свіжому клоні без теґів вона не червоніла

Друга половина сама по собі недостатня — без першої перевірка не виконається ніколи й ніде.

**Правило:** усе, що перевірка бере ззовні файлової системи етапу — теґи, змінні оточення,
мережу, час — у CI виглядає інакше. Перевір явно, а не припускай.

### Перевірка «нижній етап не змінено» мусить називати, що саме не має мінятись

Та сама правка `require_tag`, спільна для всього репозиторію, проходить крізь `check.py`
**кожного** етапу — і перевірка «етапи 1 і 2 не змінено» на неї червоніла. Формально
правильно; по суті ні: теза уроку — що не змінився **цикл**, а не що нижні етапи більше
ніколи не отримають рядка.

**Правило:** такий страж обмежується файлами реалізації (`:(exclude)…/check.py`), і причина
пишеться поруч. Інакше перший же інфраструктурний рефакторинг поставить вибір: зламати
перевірку або не робити рефакторинг.

### Self-check специфікації мусить перевіряти обидва напрямки

Перша версія скрипта звіряла «кожен критерій має рядок у плані тестів». Зворотний напрямок —
«кожен рядок плану має критерій» — не перевірявся, і в специфікації етапу 3 виявилось три
рядки, що посилались на критерії, яких у §5 не існувало.

Коли скрипт нарешті став двонапрямним, він одразу знайшов **ту саму діру в етапі 2**, де вона
прожила два тижні й пережила незалежне рецензування.

**Правило:** будь-яка звірка двох переліків робиться в обидва боки. Односторонньої досить
рівно доти, доки помилка не в тому боці, який ти не перевіряєш. Скрипт —
`scripts/spec_check.py`, прогонити на кожній специфікації перед комітом.

### Апостроф в українському слові закриває bash-рядок

Третій раз за сесію: `рев'ю`, `з'явилось`, `об'єм` містять ASCII-апостроф, і всередині
`python -c '...'` він закриває рядок оболонки. Далі bash намагається виконати українську
прозу як команди.

**Правило:** будь-яка правка з українським текстом — через файл у скретчпаді, а не через
`-c` з однією парою лапок. Це не питання охайності: помилка щоразу виглядає як синтаксична
помилка Python, і хвилина йде на пошук не там.

### Ризик у реєстрі може вгадати подію й помилитись у ліках

Етап 4, ще до першого рядка коду. У SAD §11 стояв ризик «API бібліотеки MCP зміниться» з
мітигацією «extra з підлогою, не пін». Установка за підлогою `mcp>=1.2` дала **2.0.0**, у якій
зник модуль із точки входу статті-джерела й перейменувалися всі поля відповіді.

Тобто мітигація була не просто слабка — вона **називала причиною те, що й спричинило подію**.

Це третій етап поспіль, де ризик збувається, і третій раз мітигація вгадала подію й
промахнулась у ліках: на етапі 2 вона передбачила, що ліміт рядків упреться, і назвала не той
модуль для виносу; на етапі 3 те саме.

**Правило:** мітигація в реєстрі формулюється як **дія, яку можна виконати сьогодні**, і
перевіряється питанням «якщо ризик спрацює завтра, це справді допоможе?». «Підлога, не пін»
проти зміни мажорної версії відповіді не дає — вона її дозволяє.

### Число в NFR, вигадане до заміру, — це не вимога, а побажання

Етап 4. У NFR стояло «перевірки ≤ 8 с». Заміряно після реалізації: **11.96 с**, і вісім було
недосяжне **за побудовою** — одне підняття підпроцесу коштує 0.85–1.7 с, а сценаріїв шість.

Спокуса в такий момент одна: підігнати реалізацію під число. Тут це означало б підняти один
сервер на весь набір — і купити секунди за властивість, заради якої перевірки й пишуть
(падіння одного сценарію не має пояснюватись станом іншого).

**Правило:** NFR із числом, якого ще ніхто не міряв, позначається як оцінка й **виправляється
за першим заміром**, а не захищається. Виправлення записується з причиною: наступний читач
має бачити, що число заміряне, а не що воно завжди було таким.

**Що при цьому оптимізувати можна.** Ізоляція потрібна між **сценаріями**, не між твердженнями:
два ассерти про одну й ту саму відповідь — це один сценарій, і другий процес купує там нічого.
Різниця тонка, і саме вона відрізняє чесну оптимізацію від здачі властивості.

### Профіль дешевший за здогад про те, що повільне

Етап 4. Набір перевірок виріс до 21.6 с. Дві «очевидні» оптимізації — прибрати зайве
підняття процесу в демо й скоротити тайм-аут — дали разом **0.3 с**.

Профіль показав справжнє: перевірка «жодна причина відмови не порожня» піднімала **ті самі
два сервери**, що й перевірка фаз відмови. Три секунди за нуль нової інформації. Об'єднання
дало **5.7 с**, тобто вдвадцятеро більше за обидва здогади.

**Правило:** перед скороченням часу — профіль, навіть якщо здається, що й так видно, де
дорого. Один рядок `sort -rn` по мілісекундах із виводу набору коштує хвилину.

**І та сама межа, що й раніше:** об'єднувати можна те, що є **одним сценарієм**. Дві
перевірки про ту саму пару відмов — один сценарій. Дві перевірки про різні сервери —
не один, скільки б секунд це не коштувало.

### Скорочення часу може мовчки послабити перевірку, яка цей час охороняє

Етап 4. Перевірка тайм-ауту писала `assert took < 10`, і при тайм-ауті 1.5 с мутація
«удесятеро довший» давала 15 с і чесно червоніла. Потім тайм-аут зменшили до 0.6 с заради
швидкості набору — і та сама мутація стала давати 6 с, тобто **проходити**.

Ніхто нічого не ламав. Константна межа просто перестала відповідати параметру, який
зменшили в іншому місці й з іншої причини.

**Правило:** межа в перевірці, що стосується величини, робиться **похідною** від цієї
величини (`1.5 + asked * 3`), а не константою. Константа правильна рівно доти, доки ніхто
не змінить те, з чим її колись звіряли.

### Одна група винятків може спричинити три різні дефекти в одному модулі

Етап 4. `anyio` загортає виняток із задачі у `BaseExceptionGroup`, і це дало **три** окремі
вади в тому самому клієнті:

    порожня причина       str(TimeoutError()) — порожній рядок
    безглузда причина     str(ExceptionGroup) — «unhandled errors in a TaskGroup»
    неправильна фаза      except ServerRefused не бачив загорнутого винятку

Третя найгірша: живий, справний сервер, який відповів «немає такого інструмента»,
діагностувався як «процес не піднявся» — тобто саме та підміна, проти якої написаний увесь
модуль. І виправляти її треба було не в тому місці, де вона виглядала: не в `except`, а в
розгортанні причини.

**Правило:** у коді з асинхронними бібліотеками і **тип**, і **текст** причини беруться з
розгорнутого винятку, ніколи з того, що прилетіло назовні. Один хелпер, один виклик.

### Два Accepted ADR одного етапу можуть суперечити один одному

ADR-0003 писав «MCP рівня доступу не бачить узагалі». ADR-0004 того самого етапу ухвалював,
що рівень доступу їде **в payload**, сервер його читає й фільтрує видачу — і перевірка
доводила саме це. Формулювання розійшлося по чотирьох файлах, і жодна перевірка його не
тримала.

Правильне твердження було вужчим: його не бачить **модель**, бо клієнт прибирає поле зі схеми.

**Правило:** формулювання, яке звучить як гасло («X його не бачить узагалі»), перевіряється
питанням «хто саме не бачить і на якому кроці». Якщо відповідь довша за гасло — у документ
іде відповідь.

### Чужа структура даних приходить неваlidованою, хоч би що казала типізація

`mcp.types.Tool.input_schema` оголошений як `dict[str, Any]` — і це все, що бібліотека
обіцяє. Перевірено по дроту проти саморобного сервера: `"properties": null` давало
`AttributeError`, `"required": null` — `TypeError`, `"properties": ["query"]` — знову
`AttributeError`. Тобто чужий сервер валив складання реєстру цілком.

**Правило:** усе, що перетнуло межу процесу, розбирається з припущенням «тут може бути будь-що
потрібного типу-контейнера». `schema.get("properties") or {}` недостатньо — потрібен
`isinstance`. І окрема перевірка з дослівно тими формами, які вже ламали.

### Виправив ваду — напиши перевірку, інакше вада повернеться мовчки

Етап 4. Рев'ю знайшло, що чужа схема валить складання реєстру, а дубльоване імʼя тихо
затінює дозволений інструмент. Я виправив обидва, перевірив руками в консолі — і **не
написав жодної перевірки**.

Мутаційний прогін показав це негайно: обидві мутації, що повертають старе поводження, дали
**0 червоних**. Тобто код був полагоджений рівно до наступного рефакторингу.

Перевірка руками доводить, що зараз працює. Перевірка в наборі доводить, що працюватиме далі.

**Правило:** кожна знахідка рев'ю закривається **парою** — правка коду й мутація в
`mutations.json`, яка цю правку відкочує. Прогін мутацій після виправлень обов'язковий: він
показує не «чи я полагодив», а «чи я захистив».

### Спостереження стає твердженням лише тоді, коли має перевірку

Етап 4 писав у NFR: «час перевірок ≤ 25 с (заміряно 15.9)». Чесне число, заміряне своїми
руками. Через дві задачі етап отримав другу e2e-перевірку — ту, що проганяє ті самі шість
сцен через межу процесу, — і набір став коштувати 32 с. Число в прозі лишилось старим.
Помітили випадково, місяцем пізніше, коли час кинувся в очі в чужому прогоні.

**Це третій випадок того самого класу на одному етапі.** Кількість перевірок розійшлася
з прозою — закрили лічильником. Кількість рядків розійшлася — закрили підрахунком через
AST. Час розійшовся — і не закрили нічим, бо він **виглядав як спостереження, а не як
вимога**. Різниці між ними немає жодної, окрім наявності перевірки.

**Правило:** число, що потрапило в документ, уже є твердженням. Або поруч стоїть те, що
його тримає, або в документі пишеться не число, а «заміряно одноразово, не тримається».

**Де ставити сторожа — там, куди сходяться всі.** Спокуса була написати перевірку часу
всередині етапу 4. Але етапів шість, і кожен наступний повторив би її своїми руками.
Стеля оголошується в модулі одним рядком (`BUDGET_SECONDS`), а тримає її раннер —
один механізм на всіх, і новий етап отримує його безкоштовно.

**Стеля — не ціль.** 90 при заміряних 32: сторож має ловити подорожчання вдесятеро, а не
на відсоток. Тісна межа на повільнішому раннері CI дає мигтіння, а межу, що мигтить,
піднімають не думаючи — і вона перестає означати будь-що. Механізм перевірено навмисним
псуванням: стеля 0.01 с робить модуль червоним.

### Питання, яке знаходить найбільше: «що має зламатись, щоб ця перевірка почервоніла?»

Етап 5, гейт рев'ю. Двадцять сім знахідок, і найдорожча не коштувала жодного рядка коду —
рев'юер просто спитав про кожну перевірку, **що саме** має зламатись, щоб вона впала.
Чотири рази відповідь була «нічого».

Найгірша з чотирьох стверджувала, що чужий факт не потрапляє у контекст. Фікстура клала
текст «Доставляти на Банков**у** 11», а обидва твердження шукали підрядок «Банков**а**».
Називного відмінка в тексті немає ніколи, тож `not any(...)` було істинним **завжди** —
включно з пам'яттю зовсім без фільтра власника.

**Це третій випадок тієї самої пастки з відмінюванням** («Київ»/«Києві» на етапі 1,
«Володимирська»/«Володимирську» на етапі 5). Перші два зробили перевірку **червоною** й
знайшлись за хвилини. Цей зробив її **зеленою назавжди** — і саме тому прожив до рев'ю.

**Правило:** перевірка, яка стверджує заперечення (`not in`, `assert not any`), спершу
має довести, що фікстура взагалі здатна дати збіг. Один рядок:

```python
assert any("Банков" in f.text for f in stored), "фікстура не містить чужого факту"
assert not any("Банков" in t for t in texts), texts
```

Без першого рядка друге твердження доводить лише те, що автор двічі написав те саме слово
по-різному.

**Практично:** прогрепай набір за `assert not`, `not in`, `assertNotIn` і для кожного
спитай, що функція має повернути, щоб твердження пройшло на зламаному коді. Найчастіша
відповідь — «порожньо», і «порожньо» майже завжди досяжне.

### Демонстрація вади буває чутливішою за перевірку вади

Той самий етап. Дзеркальна перевірка ізоляції проходила й ловила свою мутацію — але з
неправильної причини: чужі й власний факт мали **однакову оцінку**, і власний виживав лише
тому, що `sorted()` стабільний, а додали його останнім. Перестав два рядки у фікстурі — і
перевірка зеленіє на зламаному коді, не змінивши жодного ассерту.

Знайшлось це не з червоного. Я писав розв'язок для читача — три реалізації пам'яті поруч
на однакових даних, — і середня надрукувала «1 факт» там, де мала надрукувати «порожньо».

Причина проста: **демонстрація, яка нічого не показує, видимо марна, а перевірка, яка
нічого не доводить, виглядає точно як перевірка, що доводить.** У демонстрації немає
запасу, у перевірки він є.

**Правило:** якщо етап має розв'язок або демо, що показує ваду поруч із виправленням, —
пиши його **до** того, як вважати перевірку готовою. Він коштує двадцять рядків і ловить
те, на що перевірка сліпа.

### Реєстр ризиків варто перечитувати, коли ризик спрацював

SAD етапу 5 містив рядок: «ліміт рядків `long_term` затісний… виносити треба буде **не**
вибірку (вона вже окремо), а витяг фактів — він єдиний потребує моделі».

Виправлення знахідок рев'ю довело модуль до **90 із 90**. Спокуса була підняти бюджет.
Замість цього я відкрив реєстр і побачив, що місце винесення вже названо — і названо
правильно. Витяг став `extraction.py`, модуль повернувся до 79.

Мітигація, написана наперед, зазвичай вгадує **факт** («буде затісно») і не вгадує **місце**
(«що саме виносити»). Цього разу вгадала обидва — і це видно лише тому, що реєстр
перечитали в момент спрацювання, а не перед етапом.

### Курс може вчити правилу й порушувати його у власному коді

Етап 5 дав чекліст «що запам'ятовувати»: шість питань, перше — «це секрет?», четверте —
«прямо просив запам'ятати?». Порядок навмисний, і про це є абзац: «запам'ятай мій пароль»
задовольняє обидва, тож відповідь залежить винятково від того, яке питання раніше.

Через тиждень етап 6 зшивав сервіс, і в ньому з'явився рядок:

```python
if question.lower().startswith(("запамʼятай", "запам'ятай")):
    self.store.remember(...)
```

Одне правило з шести. Четверте. Сервіс зберігав паролі **й клав їх у трейс** разом із
причиною відкидання — на етапі, чия теза дослівно: «ключ у трейсі це ключ у файлі, який
читає той, хто налагоджує».

**Механізм помилки варто назвати точно.** Я не забув про чекліст — я його написав. Я не
проігнорував правило — я його сформулював. Просто в момент написання `_remember` думав
про зшивання, а не про памʼять, і `decision.py` не спав на думку жодного разу.

**Правило:** коли етап **використовує** механізм попереднього етапу, перевірка має
стверджувати, що використовує **цілком**, а не частково. Найдешевша форма — виклик
чужої функції замість власного `if`: `decide(...)` неможливо виконати наполовину.

Знайшов це чистий контекст, і не міг знайти ніхто інший: усередині голови, що писала
обидва етапи, вони узгоджені за побудовою.

### Перевірка, що шукає підрядок у конфігурації, доводить наявність підрядка

Дві перевірки етапу 6 мали префікс `FAILURE ·`, правильне твердження й нуль зубів:

```python
assert "migrate:" in compose
assert "service_completed_successfully" in compose
```

Перенеси залежність із `api` у `caddy` — сервіс стартує до міграцій, тобто настає рівно
та поломка, яку перевірка називає. Обидва підрядки на місці; перевірка зелена.

Друга шукала `$BASE` у смоук-скрипті й рахувала входження. Гілка «локально перевіряємо
менше» проходила всі твердження — тобто робила саме те, що перевірка забороняє.

**Правило:** конфігурацію треба **розбирати**, а не грепати. YAML має парсер, і
твердження про структуру (`services["api"]["depends_on"]["migrate"]`) червоніє там,
де твердження про текст лишається зеленим. Ціна — одна залежність у `dev`.

Той самий принцип уже двічі застосовано до коду (розбір AST замість пошуку в тексті).
Конфігурація нічим не відрізняється: це теж структура, яку читає машина.

### Демо не має друкувати числа, якого не отримало

Сцена «дзеркальні половини» друкувала:

```
  смоук:  ./deploy/smoke.sh https://localhost -> 10 пройдено, 0 збоїв
```

Скрипт не запускався. Число взяте з памʼяті автора. І воно ще й **викидало третій стан**
(«1 не перевірено»), який сам скрипт викидати забороняє — тобто демо суперечило тому,
що показувало поруч.

**Правило:** демо друкує лише те, що щойно обчислило. Число, яке демо не може отримати
саме, замінюється командою, яку читач запустить. Проза, що переказує результат, — це
та сама вада, що число в NFR без заміру, лише гучніша: її бачить кожен читач.

### Розгортання знаходить клас вад, який недосяжний для юніт-тестів

Чотири вади з першого справжнього деплою, і три з них невидимі для тестів **за
побудовою**, а не через недбалість:

    том належав root          права існують між процесом і ОС; тести працюють від тебе
    міграції ніхто не застосував   порядок існує між контейнерами; у тестів їх немає
    невдалий запит отруїв зʼєднання   стан існує в ЧАСІ; у тестів немає минулого

Третя найповчальніша: `InFailedSqlTransaction` означає, що сервіс лишався зламаним
**після того, як причина зникла**. Таблиця зʼявилась, а зʼєднання далі падало.

**Клас ширший за бази даних:** закешована негативна відповідь DNS, запобіжник без
напіввідкритого стану, клієнт, що позначив вузол мертвим і не переперевіряє, прапорець,
виставлений на першій помилці й ніколи не знятий. Форма одна: **виправ причину —
симптом лишиться**.

**Правило:** перед тим, як вважати сервіс готовим, спитай про кожен довгоживучий обʼєкт:
**у який стан його може назавжди лишити одна відмова?** Це питання знаходить такі вади
за хвилину, без розгортання. Але ніщо не спонукає його поставити, доки не обпечешся.

### Перевірка, що порівнює одне джерело саме з собою, — це тотожність

Етап 8 писав оцінювач. Його рівень e2e судив `case.answer` — **опис** кейса, — тоді як
`trajectory.answer()` існував і не викликався жодним рівнем. Перевірка «та сама відповідь,
різні шляхи» порівнювала:

    straight.by_level(E2E).state == lucky.by_level(E2E).state

Обидва кейси несуть однаковий рядок і йдуть крізь одного детермінованого суддю. Ассерт
неможливо порушити — і він був зеленим, поки в трейсі відповіді не було взагалі.

**Питання, що знаходить цей клас:** *звідки взялися два боки рівності?* Якщо з одного
обʼєкта — це тотожність, і вона зійдеться навіть тоді, коли дані до неї не доїхали. Той
самий етап робить це правильно поруч: `report.parse()` читає **записаний файл**, а не
лічильники прогону.

### Проза, яку ніхто не запускає, старіє мовчки

Три вади етапу 8, знайдені рев'ю, — це один і той самий дефект у трьох місцях:

    ModelJudge          не було навіть у списку імпортів check.py
    восьма сцена демо   шукала traces/s01.jsonl — назви, якої трасувальник не створює
    повідомлення TRACE_SINK   посилалось на ADR, який рішення не ухвалював

У всіх трьох випадках код **читали** й нічого не помітили. Парсер бала, для якого «3 з 10»
означало десятку, прожив би до першого прогону з ключем; сцена, що не виконувалась, друкувала
відповідь на критерій приймання сталою прозою.

**Правило:** якщо гілку неможливо виконати в наборі — підміни її транспорт і виконай. Суддя,
що ходить у мережу, перевіряється підміною `_ask`; сцена, що читає диск, — тимчасовим
каталогом. «Без ключа не перевіряється» — це `НЕ ПЕРЕВІРЕНО` для **мережевої** частини, а не
для парсера, який до мережі не має стосунку.

### Число про брак вимірювання не сміє саме бути здогадом

Етап 8 мав закрити обіцянку етапу 6: сказати, чого оцінювачеві бракує у трейсах. Він сказав —
і **помилився двічі**: зарахував фазу відмови етапу 4 (`None` на щасливому шляху) за ключ
прогону й забув про етап 7. Цифра стояла у пʼяти місцях, включно з чеклістом, де читача
просили її переказати.

Найгірше, що ADR суперечив сам собі: його блок вимірів перелічував кроки етапу 7, а
підсумкова таблиця нижче цей етап пропускала.

**Правило:** ADR, який називає число, мусить назвати **спосіб його отримати**, а набір —
звірити прозу з цим способом. Тут перелік тепер розбирає виклики трасувальника в джерелах.
І розбирає **AST**, а не грепом: `whole(run=run)` етапу 7 — параметр функції, і греп читав
його як поле трейсу, тобто помилявся тим самим способом, що й людина.

### Ассерт-заперечення істинний за побудовою частіше, ніж здається

Перевірка приватності етапу 8 шукала текст користувача в обʼєкті `Watch`, який складається з
лічильників і сталих літералів. Жодна мутація коду не змогла б занести туди рядок — ассерт
був зеленим **за побудовою**. Справжній шлях витоку при цьому існував: компонентний рівень
копіював вільне поле `reason` просто в причину вердикта, а звіт її друкував.

**Питання:** *яку правдоподібну поломку цей ассерт спіймає?* Якщо жодної — він не перевірка,
а коментар із ключовим словом `assert`. Заперечення про **код** пишеться через
`code_mentions` (AST, не бачить docstring), тотожність обʼєкта — через `is`, а не через
підрядок з іменем імпорту.

### Мутаційний прогін — найдешевший рев'юер, і він іде до людей

На етапі 8 мутації знайшли три дефекти **в щойно написаних перевірках**, перш ніж їх побачив
хоч один рев'юер: дзеркальний випадок був вироджений (суддя мовчав повністю — обидві формули
давали нуль), перевірка частки мигтіла (випадкові ідентифікатори, 10 % на 21 траєкторії — нуль
приблизно раз на девʼять прогонів), а перевірка приватності була зчеплена з сусіднім модулем.

Четверту знайшла сама вправа: мутація `gap > 1` нічого не глушила, бо обидва розриви в наборі
дорівнюють двом. Вправа, що обіцяє червоне й дає зелене, вчить, що перевірки не мають зубів.

**Правило:** прогін мутацій — **перед** тим, як кликати рев'юерів, а не після. Він коштує
хвилини й знімає з них клас знахідок, на який вони витратять години.

### Фільтр, що відсіює саме порушників, робить ассерт про них тавтологією

Етап 9 стверджував «усі реалізації виконують ту саму задачу» так:

    ran = _counted_rows(rows)      # лишає ті, у яких `not row.broken`
    for row in ran:
        assert not row.broken      # ...і стверджує, що broken немає

Той самий помічник тримав ще дві перевірки. Обидві звітували `ok`, довівши властивість двома
рядками з чотирьох — а читач має підстави думати, що доведено всі чотири.

**Питання, що знаходить цей клас:** *чи може предмет ассерта взагалі потрапити в те, по чому
він ітерує?* Якщо колекцію відфільтровано за тією самою ознакою — ні. І окремо: **неповне
покриття віддається третім станом**, а не зеленим. `НЕ ПЕРЕВІРЕНО` з переліком недоведених
чесне; `ok` на двох із чотирьох — ні.

### Твердження уроку перевіряється тією командою, яку урок радить читачеві

Етап 9 відкривався заголовною знахідкою: «жодна версія CrewAI не підтримує Python 3.14». Чекліст
того ж етапу наказував читачеві перевірити це власноруч. Одна команда — `pip download crewai` —
віддає 0.11.2 і спростовує урок.

Точне формулювання виявилось **сильнішим** за неточне: жодна версія **від 0.14.0**, тобто жодна,
у якій існує потрібна точка розширення. Вибір між «ставиться й нема чим підключити» та «є API,
але не ставиться» змістовніший за просте «не ставиться».

**Правило:** перед тим як написати «жодна», «завжди» чи «ніколи», виконай ту команду, якою це
перевірятиме читач. Урок, чия перша теза спростовується першою ж вправою, втрачає не тезу, а
довіру до решти.

### Літерал у банері — це тавтологія, яку перевірка не побачить

Двічі поспіль, на етапах 8 і 9: демо друкує сталий рядок «модель підроблена», а перевірка
стверджує `output.startswith("[FakeLLM]")`. Обидві половини походять з одного літерала, тож
ассерт істинний завжди — включно з прогоном читача, у якого налаштовано ключ.

**Правило:** банер приходить із **фабрики**, а не з константи етапу, і перевірка звіряє його з
тим, що фабрика поверне зараз. Той самий клас, що й «інваріант із двох доданків»: рівність,
обидва боки якої з одного джерела, не є перевіркою.

### Захардкоджене імʼя моделі ламає етап рівно для того, хто зробив усе правильно

`create(model="fake", …)` працює доти, доки читач не налаштував ключ. Після цього `get_client()`
віддає справжнього клієнта, провайдер відповідає відмовою на неіснуючу модель, і етап падає на
першій же сцені — у того, хто пройшов етап 1 і виконав інструкцію.

Той самий рід помилки, що й «інструкція, що карає за послух», лише зсередини коду. Поруч
знайшовся другий випадок: прапорець `S09_ADK=1`, задокументований у власному докстрінгу модуля,
валив сімнадцять перевірок із двадцяти восьми, вимагаючи креденшелів, яких реалізація навмисно
не використовує.

**Правило:** перед тегом прогони етап **обома** способами — з ключем і без. Гілка «з ключем»
зазвичай не має жодної перевірки, бо перевірки офлайнові; отже вона перевіряється руками, або
не перевіряється взагалі.

### Прогрів, стеля, поріг: усе, що тримає число, мусить мати перевірку

Колонка невидимих рядків етапу 9 мигтіла між процесами, бо перший прогін трасує ще й імпорт.
Прогрів це виправив — і **жодна перевірка не помітила б його зникнення**: усі двадцять прогонів
перевірки детермінізму йдуть в одному процесі, де імпорт уже стався.

Число виявилось гіршим за очікуване: холодний старт дає 13992 виконані рядки проти 1895 теплого,
всемеро.

**Правило:** перевірка детермінізму, яка живе в одному процесі, бачить лише мигтіння **всередині**
процесу. Один відбиток має братися в підпроцесі — інакше цілий клас нестабільності невидимий за
побудовою. І ширше: якщо число тримає якийсь механізм (прогрів, сортування, кеш), спитай, яка
саме перевірка почервоніє від його зникнення. Немає такої — механізму фактично немає.

### Порівняння, у якому один учасник ділиться кодом з іншим, несиметричне

Реалізація на фреймворку імпортувала пʼять рядків у базової лінії — і колонка «мої рядки»
показала різницю в дванадцять замість сімнадцяти. Помилка йшла в бік «фреймворк дешевший», тобто
в бік висновку, якого хочеться.

**Правило:** у порівнянні кожен учасник платить за все, що виконує. Дублювання коду між
учасниками порівняння — не недбалість, а умова коректності виміру.

### «Імпортує» — не те саме, що «використовує»

Теза етапу 10 у першій редакції звучала «капстоун імпортує зріле з етапів 1–9». Читання
`stages/s06_platform/app.py` її вбило: етап 6 **уже** імпортує чотири етапи, і написати це
означало б описати те, що сталося чотири етапи тому.

Але в тому самому рядку лежала справжня теза. З етапу 2 імпортується **одне ім'я** — константа
рівня доступу, яка їде далі як аргумент. Пошук, ембеддинги, фільтр доступу — усе, заради чого
етап 2 існує, — не виконується **ніколи**.

Перелік імпортів це ховає. Доказ повторного використання має форму **виконаних рядків**, а не
рядків `import`. Питання «скільки з цієї частини справді працює» має відповідь числом, і
відповідь регулярно виявляється нулем.

### Число, яке рахується, і число, яке нізвідки не береться

Дві діри етапу 10 знайшов **мутаційний прогін**, а не автор і не рев'ю. Обидві одного роду:
число рахувалось, але ніщо не стверджувало, **звідки** воно.

Ціна перехідників не залежала від реєстру `ADAPTERS` — можна було порахувати всі функції
модуля, і перевірка «ціна менша за весь модуль» лишалась істиною. Прогрів перед виміром не мав
жодного свідка: у наборі перевірок він на той момент уже нічого не міняв, бо попередні
перевірки все поімпортували.

Латка для першої навмисно **поведінкова**: прибери один перехідник із реєстру — число мусить
упасти. Переписати той самий підрахунок у перевірці означало б довести, що дві копії однакові.
Це той самий клас, що ловився на етапах 8 і 9: **рівність, обидві половини якої з одного
джерела**.

### Набір перевірок ховає ефект власним порядком прогону

Мутація «прибрати прогрів» червонила нуль. Перевірка була чесна; умови, у яких вона працювала, —
ні: до неї вже відпрацювало двадцять інших перевірок, і `sys.modules` віддавав готове.

Вимір у **свіжому процесі** дав 234 рядки проти 166 — сорок один відсоток зайвого, і весь у бік
«складання дороге».

Урок ширший за прогрів: якщо ефект залежить від стану процесу, набір перевірок його **не
побачить**, бо сам цей стан і створює. Такі речі міряються підпроцесом, і це не надмірність.

### Однакова функція ще не означає однакових умов

Демо друкувало 166, перевірка міряла 165. Обидва числа вже йшли через **один** виклик — спільну
функцію виміру. Різниця сиділа у **вході**: у демо файл трейсу вже містив прогін сценаріїв, тож
оцінювач виконував гілку розбору; у перевірці файл був порожній, і та гілка не виконувалась.

Вимір виконаних рядків залежить від **даних**, а не лише від коду. Спільна функція прибирає одну
причину розбіжності з двох; другу — однакові умови — доводиться забезпечувати окремо.

### Невідповідність іде в перехідник, ніколи в частину

Під час складання неминуче знаходиться частина, яку однією правкою можна зробити зручнішою.
Правка дешевша за перехідник, чистіша на вигляд і покращує сам етап.

І вона заборонена. Частина, яку довелося змінити, спростовує тезу «частини були зрілі», а зміна
зачіпає ще й урок, перевірки, тег і статтю того етапу. Кожна невідповідність іде в перехідник і
потрапляє в **число**; потреба в правці — у звіт, з назвою етапу.

Тому ж перехідник **не вирішує**. Той, що вирішує, є частиною, і їй місце в етапі — з уроком і
перевірками.

### Порожній розділ «що виявилось» — найпідозріліший результат

Дев'ять модулів, спроєктованих незалежно, не стикуються ідеально. Звіт, який каже інакше,
звітує не про складання, а про бажання автора.

Тому розділ «що складання виявило» перевіряється **числом**, а не наявністю заголовка, і кожен
його пункт називає етап. Сім пунктів етапу 10 — це не самокритика, а найчесніший підсумок:
парадний фінал довів би менше.

### Прилад, який міряє сам себе, рапортує це як роботу

Етап 9 стояв серед частин складання й давав ненульове число — рівно **одиницю**. Виглядало
скромно й правдоподібно. Прогін `measure(lambda: None)` на **порожній роботі** показав ту саму
одиницю: єдиний виконаний рядок етапу 9 — це вимикання трасування у `finally` його ж лічильника.

«Міряє» — не те саме, що «використовує», і різниця між ними точно така сама, як між «імпортує»
й «використовує». Знайшло це рев'ю, а не автор, і найдешевша проба виявилась однорядковою:
**прогнати вимір на порожній роботі й подивитись, що він покаже**.

### Чотири документи можуть обіцяти те, чого не питає жоден критерій

Специфікація §1, `sad.md` двічі, `CURRICULUM.md` — усі казали «другий деплой». ASGI-поверхні не
існувало, і §5 не мав про неї **жодного** критерію приймання. Обіцянка жила в прозі й не доїхала
до того місця, де її хтось перевіряє.

Рев'ю, що йде «специфікація → код», ловить це першим питанням: **який AC це доводить?** Якщо
відповіді немає, обіцянка не є вимогою — вона є прикрасою.

Виявилось, до речі, що поверхня коштувала нуль перехідників: `create_app` етапу 6 приймає
зібраний сервіс, бо етапи домовлені **формою, а не іменем**.

### Одна половина твердження задовольняється тим, щоб не робити нічого

Перевірка «один запит рахується рівно раз» була зелена й неповна: її задовольняв і код, що не
рахував **взагалі нічого**. Мутація, яка прибирала успішний облік, проходила повз неї.

Те саме з ціною: «ціна менша за весь модуль» лишалась істиною й після того, як ціна переставала
залежати від реєстру перехідників.

**Правило:** твердження про число мусить мати обидві половини — і «не більше», і «не менше»; або
бути **поведінковим**: прибери вхід — число мусить змінитись.

## 6. Tags and the reader's navigation

**Directories for navigation, tags for links.**

- `stages/sNN_slug/` — every stage visible at once, each self-contained.
- `git tag -a stage-NN` — **after** the review passes, on the commit the article describes.
- The article links **to the tag**: `github.com/AZANIR/agentic-ai/blob/stage-NN/...`
- A reader doing the exercises makes their own branch.

Why not a branch per stage: our stages are separate directories, not versions of one codebase.
Cumulative branches would mean forward-porting every fix into nine branches; stage 1 was fixed
twice in one day.

Why not links to `main`: ADR-0003 says outright that the validation from stage 1 moves into
`shared/` at stage 3. A reader arriving from article 1 six months later would see code the
article does not describe.

## 7. The article comes after the stage, never before

An article about an unwritten stage would describe code that does not exist — exactly the
defect this course is built against.

### Two directories

| Directory | What is in it | Published |
|---|---|---|
| `sources/docs/` | The author's working reference — never enters the repository | no |
| `sources/artstroy/{slug}/` | **Our** articles in Astro format | yes, in [artstroy](https://github.com/AZANIR/artstroy) |

All of `sources/` is gitignored.

### The artstroy format (checked against their zod schema)

```yaml
isDraft: true                          # false only after approval
title: "…"                             # ≤80 characters
description: "…"                       # ≤180 characters
cover: "./imgs/cover.webp"             # REQUIRED — without the file astro check fails
covert_alt: "…"                        # covert_alt indeed; the typo is real, and it is theirs
category: ai-coding                    # only: ai-coding devops documentation pentesting programming technology
authors: ["leonid-m"]
publishedTime: "YYYY-MM-DDT00:00:00.000Z"
```

Directory: `{slug_snake_case}/index.mdx` plus `imgs/`.
Branch: `article/{slug-kebab}`. Commit: `content(article): add {description}`.

### The site's style rules

- **No `# H1` in the body** — the layout supplies the title.
- Open with a concrete scene, not a definition. Often followed by "the reflex says X, and the
  reflex is wrong".
- A closing table with a **wrong fix** column — their signature device.
- Numbers always carry their source; internal links are `/articles/{slug}`.
- **```` ```mermaid ```` renders as a CODE BLOCK, not a diagram** — mermaid is wired into one
  interactive component only. Use ASCII or tables for diagrams.
- The cover is produced by their stage 3 (`nano-banana-pro`) from the `covert_alt` text.

### The angle

What tutorials never have is **what broke and how it was found**. Article 1 is built around the
seven review findings rather than around "how to make an agent".

## 8. Checking an article against the code

```bash
python scripts/article_check.py                # every article
python scripts/article_check.py three_guards   # one
python scripts/article_check.py --facts s03    # what can be verified for a stage
```

A **template** used to stand here, and every article was verified by a script written from
scratch and left in a session scratchpad. The consequence is not inconvenience: two articles
verified by different sets of assertions cannot be compared, and a verification that cannot be
repeated is a memory of one.

Everything is read **from the tag** the article links to, not from the current code. A number
computed on `main` would describe a different article: the code moves on, the article stays
where it was published.

Five dimensions:

    frontmatter   required fields and the blog schema's bounds
    attribution   no mention of an assistant
    links         links point at a tag, the tag exists, the path exists AT that tag
    snippets      fragments appear in a real file of the same tag
    claims        numbers name their source, and the source is recomputed

**Numbers are the point, and the only optional dimension.** A `claims.json` sits beside the
article: a list of `{what, how much, from where}`, where "from where" is a computation
(`checks`, `failure_modes`, `executable_lines`, `mutations`, `mutation_red`, `exercises`).
Without the file the dimension reports `NOT EVALUATED` rather than green: "not verified" and
"matched" are different states.

The check has three sides, not two: the number must appear in the article's own prose, match
what the computation returns at the tag, and name the source. Taking both halves from the tag
would prove only that two copies agree — the tautology this repository has caught at stages 8,
9 and 10, and then made again in the tool built to catch it.

**Simplifications are allowed but named.** A fragment illustrating a shape rather than quoting a
file is declared in `claims.json` together with its reason — the same requirement stage 10 puts
on decisions with no source stage: either a source, or a stated reason why there is none. A
declaration with no reason is a defect; a silent exemption would turn the check into decoration.

The script is **not** part of `check_all.py`: the articles live outside the repository
(`sources/` is gitignored), so for anyone else the run would always be `NOT EVALUATED`.

## 9. Checklist before starting a stage

- [ ] Re-read §5 — the lessons already paid for
- [ ] The previous stage has its tag and its article
- [ ] `python scripts/check_all.py` is green
- [ ] If this stage rewrites something from an earlier one (as `shared/` at stage 3), it is
      recorded in an ADR
- [ ] A backup exists, if anything destructive is planned

## 10. Checklist before closing a stage

- [ ] All nine items of §3
- [ ] Reviewed by two clean contexts, every MAJOR closed
- [ ] Mutating a key guard produces an `AssertionError` with meaningful text, **not** an
      infrastructure error
- [ ] NFR numbers re-measured, not copied from the previous stage
- [ ] Tag created and pushed
- [ ] Article checked by the script (§8), `isDraft: true` until approved
- [ ] CI green on both Python versions
