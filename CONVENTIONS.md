# Конвенції репозиторію

Правила, яких дотримується кожен етап — **як писати код**.
Як довести етап до готовності (конвеєр, гейт рев'ю, теги, стаття) — [PLAYBOOK.md](PLAYBOOK.md). Джерело — [`docs/architecture-map.md`](docs/architecture-map.md)
§Conventions; тут вони розписані з поясненням «чому», бо правило без причини порушують першим.

---

## Структура

**Етап — це Python-пакет `stages/sNN_slug/`.** Запуск: `python -m stages.sNN_slug.run`.

Префікс `s` обов'язковий: ім'я Python-пакета не може починатися з цифри, а дефіс у ньому
заборонений. `stages/01-agent-loop` виглядає охайніше, але `python -m stages.01-agent-loop.run`
не запуститься ніколи.

**Склад етапу:**

```
stages/sNN_slug/
├── README.md       UA — урок: канон зі статті + міст на наш домен
├── README.en.md    EN — один екран
├── exercises.md    UA — завдання без спойлерів
├── solutions/      еталонні розв'язки
├── CHECKLIST.md    «я зрозумів / я запустив / я пояснив»
├── run.py          демо, працює без API-ключа
├── check.py        перевірки, офлайн
└── data/           фікстури
```

**Етапи 1–9 самодостатні** й навмисне дублюють трохи коду між собою — читач має могти
почати з етапу 5. **Етап 10 імпортує**, а не копіює: у цьому й полягає різниця між
навчальним і продакшн-кодом.

## Профілі й адаптери

**`if profile == ...` у коді етапу заборонено.** Розгалуження живе у фабриках `shared/`.

Порушення цього правила — найдешевший спосіб зруйнувати репозиторій: щойно код уроку
починає знати про профіль, урок перестає бути про агентів і стає про конфігурацію.
[ADR-0002](docs/adr/0002-profile-switched-adapters.md)

## LLM

**Лише `shared.llm.get_client()`.** Жодного `openai.OpenAI()` у коді етапів.

Демо завжди передає `demo_script=[...]`, щоб працювати без ключа, і друкує
`shared.llm.banner(client)` першим рядком — читач має бачити, підробка перед ним чи
справжня модель. [ADR-0003](docs/adr/0003-openai-compatible-llm-shim.md)

## Трасування

Кожен крок агента пише в `shared.trace`. Присутнє **з етапу 1**.

```python
with trace_run("демо етапу 1", stage="s01") as tr:
    tr.step("llm_call", model=settings.llm_model)
    tr.step("tool_call", name="get_weather", args=args)
```

[ADR-0005](docs/adr/0005-tracing-from-stage-one.md)

## Перевірки

Голі `assert` у `check.py`, без тест-фреймворка. Кожна перевірка — функція з docstring у
один рядок; цей рядок читач бачить у виводі.

**Серед перевірок етапу обов'язково є щонайменше одна на режим відмови.** Позначай її
префіксом `FAILURE ·` у docstring.

```python
def check_step_limit_stops_runaway() -> None:
    """FAILURE · агент зупиняється лімітом, а не крутиться вічно"""
    client = FakeLLM.always_calling("search_web")
    ...
```

Зелений щасливий шлях не доводить нічого. [ADR-0006](docs/adr/0006-assert-checks-over-test-framework.md)

## Помилки

Сервіс відповідає єдиним конвертом:

```json
{"error": {"code": "budget_exceeded", "message": "…"}}
```

Ліміти й бюджет — це `429` і `402`, а не `500`. `500` означає «ми зламались»; вичерпаний
бюджет — це штатна робота запобіжника, і плутати їх у моніторингу дорого.

## Ідентифікатори

Зовнішні ID — префіксовані рядки, що генеруються застосунком: `ord_`, `ses_`, `trc_`.

Префікс одразу каже, на що дивишся, у логах, трейсах і повідомленнях про помилки. ID
генерує застосунок, а не БД: інакше його не можна залогувати до вставки.

## Дані

Postgres 16 + `pgvector` — єдине сховище. Redis — лише лічильники й TTL-кеш.
[ADR-0004](docs/adr/0004-postgres-pgvector-single-store.md)

**Міграції:** пари `migrations/NNNN_name.up.sql` і `.down.sql`. Міграція без відкату не
приймається — раннер відмовиться її бачити. Кожна виконується в одній транзакції.

**Таблиці створює той етап, якому вони потрібні.** Схема «наперед, про всяк випадок»
застаріває швидше, ніж її встигають використати.

## Language

**Everything published to this repository is written in English.** Documentation, lesson text,
docstrings, comments, reader-facing messages, commit messages — all of it. A repository read by
people who do not share one language is read in English or not at all.

| What | Language |
|---|---|
| Lessons, READMEs, glossary, specs, ADRs, review records | English |
| Identifiers: variables, functions, files, packages | English |
| Docstrings and explanatory comments | English |
| Reader-facing messages, including check failures | English |
| Commit messages, PR titles and descriptions | English |

This replaces the earlier rule, which kept prose in Ukrainian. The change is repository-wide
and applies to files that already exist: a half-translated repository is worse than either
whole, because a reader cannot tell which half is current.

**Ukrainian is not forbidden — it is simply not what gets committed.** Drafts, working notes
and anything under `sources/` stay in whatever language suits their author; `sources/` is
gitignored precisely so that choice costs nothing.

## Стиль коду

`ruff` — лінтер і форматер: `ruff check .` і `ruff format .`. Рядок ≤ 100 символів.
Правила: `E`, `F`, `I`, `UP`, `B`.

**Код уроку читають більше, ніж запускають.** Тому: явне краще за коротке, коментар
пояснює «чому», а не «що», і жодної магії, яку не пояснює сусідній абзац README.

## Комміти

Одна логічна зміна — один комміт. Імператив, англійською: `Add stage 1 agent loop`.

Без згадок AI-асистента в будь-якому вигляді: ні співавторства, ні згенеровано-з, ні
згадок інструментів — ні в коммітах, ні в PR, ні в коментарях, ні в документації.

## Секрети

Лише `.env`, який ніколи не потрапляє в git. Жодних ключів у коді, фікстурах,
прикладах чи README. Деталі — [SECURITY.md](SECURITY.md).
