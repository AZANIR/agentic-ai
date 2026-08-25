---
status: current
mode: brownfield
updated_at: "2026-08-25"
reflects_commit: "faa95f6"
language: "python >=3.11"
build_cmd: 'pip install -e ".[dev]"'
test_cmd: "python scripts/check_all.py"
lint_cmd: "ruff check ."
migration_tool: "custom: scripts/migrate.py + numbered .sql in migrations/"
frontend: "vanilla JS (сторінка живого режиму етапу 7)"  # єдиний UI курсу; етапи 6 і 10 — backend-service + cli
---

# Architecture map — Agentic AI (навчально-продакшн курс)

> **Скан наявного коду** (`mode: brownfield`). До етапу 6 ця карта описувала цільовий фундамент —
> рішення, ухвалені до першого рядка коду. Тепер вона описує систему, яка працює й розгортається
> за HTTPS. Розділ «Стан системи після етапу 6» називає, що з ухваленого наперед виявилось
> правдою, а що — ні.
>
> **Стан:** скелет матеріалізовано 2026-08-22, **етап 1 завершено 2026-08-23**. Машинні ключі
> нижче — команди, які реально спрацювали, а не заплановані.
>
> Конвенції нижче тепер цитують реальний код етапу 1. Повний brownfield-перескан варто
> запустити після етапу 2, коли з'явиться другий етап і стане видно, що з конвенцій справді
> повторюється, а що було одноразовим.
>

>
> Джерело всіх рішень: [`planning/2026-08-22-agentic-ai-course-design.md`](../planning/2026-08-22-agentic-ai-course-design.md).
> Фундаментальна сесія (G2–G4) **не проводилась**: користувач прямо вказав, що рішення вже
> прийняті у спеці й перепитувати їх не треба.

## Stack

- **Language / runtime:** Python 3.11+ — спека §7
- **Packaging:** один інсталюваний пакет, `pyproject.toml` з extras на етап
  (`[s03]`, `[s04]`, `[s09]`, `[voice]`, `[prod]`, `[dev]`) — спека §7.
  Це те, що дозволяє етапу 10 **імпортувати** зрілі модулі етапів 1–9, а не копіювати їх.
- **Frameworks:** FastAPI + uvicorn (сервіс), mcp 2.0 (MCP-сервери), LangGraph / CrewAI /
  Google ADK (лише етап 9, за extras), APScheduler (фонові задачі)
- **LLM-доступ:** SDK `openai` як єдиний клієнт — через `base_url` покриває OpenAI, Groq,
  OpenRouter, Ollama, LM Studio
- **Build / test / lint:**
  - build — `pip install -e .[dev]`
  - test — `python scripts/check_all.py` (офлайн, без API-ключа, детермінований)
  - lint — `ruff check .` (лінт + формат одним інструментом)

## C4 — цільова система

```mermaid
C4Container
    title Target containers - Agentic AI course repo
    Person(learner, "Learner", "Reads lessons / runs stages / deploys")
    Person(enduser, "End user", "Talks to the deployed NovaShop agent")

    Container(stages, "stages", "Python packages s01..s10", "Ten self-contained lessons; s06 and s10 are deployable services")
    Container(shared, "shared", "Python package", "Profile-switched adapters: llm / embeddings / trace / stores")
    Container(api, "agent service", "FastAPI + uvicorn", "HTTP and WebSocket entry; auth, rate limit, budget guard, metrics")
    Container(mcp, "MCP servers", "mcp 2.0 over stdio", "NovaShop tools: orders / returns / catalog")
    Container(web, "test pages", "static html + js", "Chat page and microphone page for manual checks")
    Container(caddy, "Caddy", "reverse proxy", "Automatic HTTPS termination")

    ContainerDb(pg, "Postgres + pgvector", "PostgreSQL 16", "Orders / memory facts / document vectors")
    ContainerDb(redis, "Redis", "Redis 7", "Rate limits / budgets / short term cache")
    Container(obs, "Prometheus + Grafana", "metrics stack", "Is the system healthy")
    Container(lf, "Langfuse", "self hosted tracing", "Why the agent decided that")
    System_Ext(llm, "LLM provider", "Groq or OpenRouter or local Ollama")

    Rel(learner, stages, "runs locally and offline")
    Rel(enduser, caddy, "HTTPS and WSS")
    Rel(caddy, api, "reverse proxy")
    Rel(web, api, "fetch and websocket")
    Rel(api, shared, "imports adapters")
    Rel(stages, shared, "imports adapters")
    Rel(api, mcp, "list_tools and call_tool")
    Rel(shared, pg, "SQL and vector search")
    Rel(shared, redis, "counters")
    Rel(shared, llm, "chat completions")
    Rel(shared, lf, "spans")
    Rel(api, obs, "exposes /metrics")
```

## Module inventory

| Module | Path | Layers | Wired at | Responsibility |
|---|---|---|---|---|
| `shared` | `shared/` | адаптери (ports+infra) | імпорт із `stages/*` | Профіле-залежні реалізації: `llm`, `embeddings`, `trace`, `config`, `counters` (памʼять/Redis), `factstore` (файл/Postgres), `check_runner` |
| `stages.s01_agent_loop` | `stages/s01_agent_loop/` | lesson | `run.py`, `check.py` | **Готово.** Цикл, валідація аргументів, гейт підтвердження; 30 перевірок |
| `stages.s02_rag` | `stages/s02_rag/` | lesson | `run.py`, `check.py` | **Готово.** embed → cosine → top-k, фільтр доступу ДО відбору; 49 перевірок |
| `stages.s03_router` | `stages/s03_router/` | lesson | `run.py`, `check.py` | **Готово.** Supervisor, схема стану як контракт, цикл ревізій; 38 перевірок |
| `stages.s04_mcp` | `stages/s04_mcp/` | lesson + server | `server.py`, `run.py` | **Готово.** MCP-сервер, stdio-клієнт, три фази відмови; 36 перевірок |
| `stages.s05_memory` | `stages/s05_memory/` | lesson | `run.py`, `check.py` | **Готово.** Вікно + підсумок, факти, чотири умови вибірки; 42 перевірки |
| `stages.s06_platform` | `stages/s06_platform/` | **service** | `serve.py` (ASGI) | **Готово.** Три воротарі, класифікатор, стан і метрики, пастка двох воркерів; 69 перевірок. Розгорнуто локально за HTTPS; довіра до сертифіката від публічного центру — НЕ ПЕРЕВІРЕНО |
| `stages.s07_voice` | `stages/s07_voice/` | lesson + service | `pipeline.py`, `ws.py` | **Готово.** Батч проти стріму, barge-in, WebSocket-голос; 44 перевірки; 1574 -> 450 мс |
| `stages.s08_eval` | `stages/s08_eval/` | lesson | `run.py`, `check.py` | **Готово.** Три рівні оцінки поверх трейсів, «не оцінено» як третій стан; 31 перевірка |
| `stages.s09_frameworks` | `stages/s09_frameworks/` | lesson ×4 | `via_langgraph.py`, `via_crewai.py`, `via_adk.py`, `baseline.py` | **Готово.** Один контракт задачі, чотири реалізації; міряється ціна риштувань, не якість відповіді; 28 перевірок |
| `stages.s10_capstone` | `stages/s10_capstone/` | **service** | `service.py`, `run.py` | **Готово.** Девʼять етапів зібрано в один сервіс; міряється саме складання — 166 виконаних рядків проти 19 перехідників; 24 перевірки. Розгортання — НЕ ПЕРЕВІРЕНО |
| `scripts` | `scripts/` | tooling | CLI | `check_all.py`, `migrate.py`, `mutate.py`, `clean_install.py`, `docs_check.py` і три валідатори документів |
| `deploy` | `deploy/` | infra | — | **Готово.** `docker-compose.yml` (розробка) і `docker-compose.prod.yml` (пʼять контейнерів), `Dockerfile`, `Caddyfile`, `smoke.sh`, `RUNBOOK.md` |

## Стан системи після етапу 10

До етапу 6 карта описувала **рішення**, ухвалені до першого рядка коду (`mode:
greenfield-bootstrap`). Тепер вона описує те, що працює, — і етап 10 дав числа замість
вражень: усі десять етапів закриті, сім із них виконуються всередині зібраного сервісу.

```
HTTPS → Caddy → uvicorn (N воркерів) → guards → intent → memory → s01/s03 → відповідь
                                         │        │        │
                                       Redis   FakeLLM  Postgres
                                                        (том)
         planner (окремий процес) ──────────────────────┘
```

Етап 10 бере той самий скелет і вимірює його зсередини: 166 виконаних рядків етапів на запит
проти 19 рядків перехідників (11 %). Етапи 4 і 7 у складання не ввімкнені — обидва названі з
причиною, і нуль для них є рішенням, а не помилкою.

**Що з ухваленого наперед виявилось правдою:**

- Два профілі на одну кодову базу — витримали **всі десять** етапів без жодного
  `if profile ==` у коді етапів.
- `shared/` як єдине місце розгалуження — витримало; на етапі 6 туди додались два
  адаптери (`counters`, `factstore`), і жоден етап 1–5 не змінився.
- Підробка провайдера за замовчуванням — витримала аж до розгортання, де довелось
  додати `auto_reply` (сервіс не має сценарію) і `ALLOW_FAKE_LLM` (ADR-0009 етапу 6).
- Самодостатність етапів — витримала складання: капстоун не змінив **жодної** частини,
  кожна невідповідність пішла в перехідник (ADR-0004 етапу 10).

**Що виявилось неточним:**

- «Інтерфейс етапу 5 вузький, сховище підміниться» — правда лише наполовину: набір
  методів справді вузький, але `Memory` приймає шлях, а не сховище. Фабрика стоїть
  зовні (ADR-0004 етапу 6) — і на етапі 10 вона там само.
- `frontend` у цій карті обіцяв vanilla-сторінку на етапах 6–7. Етап 6 виявився
  `backend-service` без UI; сторінка зʼявилась на етапі 7 і лишилась єдиним UI курсу.
- Стік трейсів у Langfuse обіцявся «на етапі 6». Переїхав на етап 8 із причиною
  (ADR-0008 етапу 6): вимогу до сховища трейсів формулює той, хто їх читає.
- «Капстоун імпортує зріле з етапів 1–9» — теза, яку етап 10 спростував власним виміром.
  Етап 6 **уже** імпортував чотири етапи, а з етапу 2 він імпортує одну константу й виконує
  нуль його рядків. «Імпортує» — не те саме, що «використовує».

## Conventions (правила, яких дотримується кожен новий етап)

Після завершення етапу 1 конвенції мають **реальні приклади в коді** — на них і посилаємось.
Решта (сховища, ліміти, бюджет) досі описана рішенням у спеці, бо приходить із етапом 6.

- **Іменування модулів:** `stages/sNN_slug/`, запуск `python -m stages.sNN_slug.run` —
  приклад: `stages/s01_agent_loop/run.py`. Префікс `s` обов'язковий: ім'я Python-пакета не може починатись із цифри.
- **Перемикання оточення:** усе через `APP_PROFILE=local|prod` + адаптери в `shared/`,
  ніколи через розгалуження коду — спека §5.1, ADR-0002.
- **Доступ до LLM:** лише `shared/llm.get_client()`; жодного прямого `openai.OpenAI()`
  у коді етапів — приклад: `stages/s01_agent_loop/run.py:85`, ADR-0003.
- **Трасування:** кожен крок агента пише в `shared/trace`; трасування присутнє з етапу 1,
  а не додається на етапі 8 — приклад: `stages/s01_agent_loop/loop.py:87`, ADR-0005.
- **Перевірки:** кожен етап має `check.py` з голими `assert`, що виконується офлайн на
  `shared/fake_llm`; **обов'язково хоча б одна перевірка на режим відмови** —
  приклад: `stages/s01_agent_loop/check.py` (21 перевірка, 8 на режими відмови), ADR-0006.
- **Помилки:** єдиний конверт відповіді сервісу `{"error": {"code", "message"}}`;
  ліміти й бюджет повертають `429` / `402`, не `500` — спека §8.2.
- **ID:** зовнішні ідентифікатори — префіксовані ULID-подібні рядки (`ord_`, `ses_`, `trc_`),
  генеруються застосунком, не БД.
- **Persistence:** Postgres 16 + `pgvector` як єдине сховище (без окремого векторного сервісу);
  Redis лише для лічильників і TTL-кешу — ADR-0004.
- **Міграції:** пронумеровані `migrations/NNNN_name.up.sql` / `.down.sql`, застосовує
  `scripts/migrate.py`; Alembic — коли схема почне часто змінюватись — спека §7.
- **Секрети:** лише `.env` поза git; `.env.example` / `.env.prod.example` як шаблони — спека §8.2.
- **Мова:** проза й уроки — українською, код/ідентифікатори/docstrings/комміти — англійською — спека §10.
- **Комміти:** без згадок AI-асистента в будь-якому вигляді (правило репозиторію).

## Datastores

| Store | Engine | Accessed via | Notes |
|---|---|---|---|
| Основна БД | PostgreSQL 16 + `pgvector` | `shared/stores/` | Замовлення NovaShop, факти пам'яті, вектори документів. У профілі `local` замінюється на in-memory реалізацію того ж інтерфейсу |
| Лічильники | Redis 7 | `shared/stores/` | Token bucket rate-limit, бюджетні лічильники, TTL-кеш. У `local` — in-process dict |
| Трейси | JSONL у `traces/` (local) → Langfuse (prod) | `shared/trace.py` | Той самий запис, два стоки |

## Frontend / UI foundation

Мінімальний фронтенд, свідомо. Дві статичні сторінки без збірки й без фреймворка — вони існують,
щоб **вручну постукати** в сервіс, а не як продукт.

- **Component library / design system:** немає і не планується. Дві сторінки не виправдовують
  дизайн-систему — ставити React заради них було б саме тією надмірністю, проти якої аргументує стаття 6.
- **Design tokens:** кілька CSS-змінних у `<style>` кожної сторінки
- **Styling approach:** vanilla CSS у самому файлі, без збірки
- **Shared primitives:** немає
- **State / data-fetching:** `fetch` + `WebSocket` напряму
- **Closest UI precedent:** `deploy/web/chat.html` (текстовий чат) і `deploy/web/mic.html`
  (мікрофон, етап 7) — обидві створює `scaffold`/етап 6

**Правило на майбутнє:** якщо сторінок стане більше трьох або з'явиться реальний UI —
це окреме рішення з власним ADR, а не тихе додавання фреймворка.

## Where things live / closest precedents

- **Новий навчальний етап** → `stages/sNN_slug/`, за зразком `stages/s01_agent_loop/`
  (README.md + README.en.md + exercises.md + solutions/ + CHECKLIST.md + код + check.py).
- **Новий адаптер** (провайдер, сховище, стік трейсів) → `shared/`, з обома реалізаціями
  (`local` і `prod`) за одним інтерфейсом; ніколи не `if PROFILE == ...` у коді етапу.
- **Новий інструмент агента** → MCP-tool у `stages/s04_mcp/server.py` або
  `stages/s10_capstone/mcp/`; за правилом статті 6 — менше інструментів із чистими payload,
  а не мапа всіх ендпоінтів.
- **Нова інфраструктура** → `deploy/`, з оновленням `deploy/RUNBOOK.md`.

## Constraints & known tech-debt

- **Читач не має платити, щоб пройти курс.** `check_all.py` не ходить у мережу взагалі.
  Будь-яке рішення, що вимагає API-ключа для базової перевірки, — порушення фундаменту.
- **Одна VM, ≥4 ГБ RAM.** Повний стек (app+pg+redis+caddy+prometheus+grafana+langfuse) не
  влазить у 2 ГБ, тож `docker compose` має три профілі (`core` / `observability` / `full`).
- **Один uvicorn-воркер за замовчуванням** через APScheduler. Це не недогляд, а відтворення
  пастки зі статті 6; етап 6 показує проблему і виносить планувальник в окремий процес.
- **Локальний Whisper на CPU повільний.** Це зміст уроку 7, не баг — але в README мають бути
  чесні очікувані числа.
- **Статті-джерела в репозиторії не зберігаються.** Локальні копії прибрано, лишились
  посилання на оригінали (`.gitignore`: `sources/`). Звірка статей із кодом за PLAYBOOK §8
  описана, але **жодного разу не запускалась** — скрипта звірки немає.
- **Версії LangGraph / CrewAI / ADK ламаються між релізами.** Запінені в `pyproject.toml`;
  смоук у `check.py` ловить розрив рано.

## Reconciliation with the authored architecture doc

Авторського `docs/architecture.md` немає. Є два документи, з якими ця карта узгоджена:

1. [`planning/2026-08-22-agentic-ai-course-design.md`](../planning/2026-08-22-agentic-ai-course-design.md) —
   **джерело істини** для всіх рішень нижче. Карта не суперечить йому ніде; вона перекладає
   його рішення у форму, яку читають подальші SDD-скіли.
2. [`planning/00-prior-cursor-plan.md`](../planning/00-prior-cursor-plan.md) — попередній план.
   Частково скасований (спека §2): деплой, systemd і Prometheus перенесено з «поза scope» у scope,
   провайдер став pluggable, шлях запуску виправлено на `stages.sNN_slug`.
