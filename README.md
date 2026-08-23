# Agentic AI: від нуля до продакшену

Практикум із 10 етапів за [однойменною серією статей](docs/readme.md) Sai Bhargav Rallapalli.
Не переказ — репозиторій, у якому кожну ідею серії треба **побудувати, зламати й виміряти**.

[English](README.en.md) · [Програма](CURRICULUM.md) · [Встановлення](SETUP.md) · [Глосарій](GLOSSARY.md)

---

## Що це

Дві речі одночасно, одним кодом:

- **Навчальний курс.** Десять самодостатніх етапів. Усе працює локально, офлайн,
  безкоштовно й детерміновано — платіжна картка не потрібна ніде.
- **Розгортуваний сервіс.** Той самий код на етапах 6 і 10 виходить на справжню VM
  за HTTPS, з Postgres, Redis, метриками, трасуванням і бюджетним запобіжником.

Різницю тримає `APP_PROFILE`: він перемикає адаптери, а не гілки коду
([ADR-0002](docs/adr/0002-profile-switched-adapters.md)). Тому те, що ти вивчив, — це
буквально те, що потім працює під навантаженням.

## Для кого

Ти вмієш написати функцію на Python і запустити скрипт. Ти не знаєш, що таке embedding,
tool-call, state graph, MCP, barge-in чи LLM-as-judge — і саме тому цей курс існує.

**Обіцянка:** після кожного етапу ти маєш щось робоче, що запустив сам, і можеш **словами**
пояснити, чому воно так влаштоване.

## Як влаштований курс

```
Акт I   · етапи 1–5  · БУДУЄМО      кожен етап додає агенту нову здатність
Акт II  · етап  6    · ЗШИВАЄМО     блоки 1–5 стають одним задеплоєним сервісом
Акт III · етапи 7–9  · ПЕРЕВІРЯЄМО  латентність, вимірювання, вибір інструмента
Фінал   · етап  10   · ПЕРЕПИСУЄМО  чисто, з обґрунтуванням кожного рішення
```

Етапи 7–9 не додають функціоналу. Вони існують, щоб ти перестав собі брехати.

| # | Етап | Що будуєш | Стаття |
|---|------|-----------|--------|
| 1 ✅ | [Agent loop](stages/s01_agent_loop/README.md) | ReAct-цикл з нуля, без фреймворку | [#1](https://blog.gopenai.com/what-is-an-ai-agent-the-simplest-explanation-youll-find-e7b176a31c44) |
| 2 | RAG | embed → cosine → top-k → відповідь із цитатою | [#2](https://blog.gopenai.com/rag-vs-fine-tuning-which-one-actually-solves-your-problem-06df08b5dc40) |
| 3 | Router | Свій міні-граф, потім LangGraph | [#3](https://blog.gopenai.com/build-a-multi-agent-router-with-langgraph-in-30-minutes-8ee979116b53) |
| 4 | MCP | FastMCP-сервер і клієнт | [#4](https://blog.gopenai.com/mcp-protocol-explained-the-new-standard-every-ai-developer-needs-to-know-0e3e56aee2aa) |
| 5 | Memory | extract → store → retrieve, семантичний пошук | [#5](https://blog.gopenai.com/memory-in-ai-agents-why-your-agent-forgets-everything-and-how-to-fix-it-250150317ff1) |
| 6 | Platform | **Перший деплой:** FastAPI + HTTPS + метрики | [#6](https://blog.gopenai.com/i-built-a-multi-connector-ai-platform-on-a-single-vm-heres-the-real-architecture-656c9c3f3044) |
| 7 | Voice | Батч проти стріму, barge-in, вимірювання | [#7](https://blog.gopenai.com/voice-agents-at-scale-what-breaks-when-millions-of-people-talk-to-your-ai-87750cc78054) |
| 8 | Evaluation | Оцінка на 3 рівнях поверх трейсів | [#8](https://blog.gopenai.com/agent-evaluation-how-do-you-know-your-agent-actually-works-1c6b7cef5461) |
| 9 | Frameworks | Один таск трьома фреймворками | [#9](https://blog.gopenai.com/langgraph-vs-crewai-vs-google-adk-i-built-the-same-agent-three-times-87c2f2ce3b59) |
| 10 | Capstone | **Другий деплой:** усе разом, під навантаженням | [#10](https://blog.gopenai.com/the-capstone-building-one-real-agent-with-everything-from-this-series-23742b41fcc7) |

Детальніше — у [CURRICULUM.md](CURRICULUM.md).

## Швидкий старт

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # лапки обов'язкові — без них shell з'їсть дужки
cp .env.example .env             # міняти нічого не треба
python scripts/check_all.py      # має бути зелено, офлайн, без ключів
```

Якщо останній рядок зелений — усе готове. Повністю: [SETUP.md](SETUP.md).

## Статус

Скелет матеріалізовано; етап 1 завершено.

| Компонент | Стан |
|---|---|
| `shared/` — конфіг, LLM-шим, FakeLLM, трасування | готово, 13 перевірок |
| `scripts/check_all.py`, `scripts/migrate.py` | готово |
| `deploy/docker-compose.yml` — Postgres+pgvector, Redis | готово |
| CI (ruff + перевірки, без секретів) | готово |
| Етап 1 — цикл агента | **готово**, 21 перевірка |
| Етапи 2–10 | не почато |

## Куди дивитись

| Документ | Про що |
|---|---|
| [CURRICULUM.md](CURRICULUM.md) | Програма: мета етапу, час, залежності, статус |
| [SETUP.md](SETUP.md) | Встановлення, вибір LLM-провайдера, типові граблі |
| [GLOSSARY.md](GLOSSARY.md) | Терміни українською й англійською |
| [CONVENTIONS.md](CONVENTIONS.md) | Правила коду репозиторію |
| [SECURITY.md](SECURITY.md) | Модель загроз публічного ендпоінта |
| [docs/architecture-map.md](docs/architecture-map.md) | Архітектура: C4, модулі, сховища |
| [docs/adr/](docs/adr/) | Шість рішень, які визначили решту |
| [planning/](planning/) | Дизайн-спека курсу |

## Джерела

Оригінальні статті лежать у [`docs/`](docs/readme.md), URL кожної — у її frontmatter.
Етапи **не копіюють** текст статей: вони переказують ідеї і будують за ними працюючий код.

> Перед публікацією цього репозиторію повні тексти статей у `docs/` треба замінити на
> посилання й власні конспекти — див. §14 [дизайн-спеки](planning/2026-08-22-agentic-ai-course-design.md).
