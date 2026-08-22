# Встановлення

Мета цієї сторінки — довести тебе до зеленого `check_all` за п'ять хвилин, **без API-ключа
і без інтернету**. Усе інше (справжня модель, база, деплой) — опційно й потім.

---

## 1. Що потрібно

| Обов'язково | Версія | Навіщо |
|---|---|---|
| Python | 3.11 або новіший | етапи 1–5, 8, 9 |
| git | будь-яка | клонувати |

| Знадобиться пізніше | Коли |
|---|---|
| Docker + Docker Compose | етап 6 (база, Redis, деплой) |
| VM з Ubuntu, ~4 ГБ RAM | етапи 6 і 10 (справжній деплой, ~€4–8/міс) |

Перевір Python:

```bash
python --version     # має бути 3.11+
```

Якщо команда не знайдена — спробуй `python3` або `py` (Windows).

## 2. Віртуальне оточення

```bash
git clone <url> Agentic-AI
cd Agentic-AI

python -m venv .venv
source .venv/bin/activate         # Linux / macOS
# .venv\Scripts\activate          # Windows PowerShell / cmd
# source .venv/Scripts/activate   # Windows Git Bash
```

Ознака успіху: в промпті з'явився префікс `(.venv)`.

## 3. Встановлення пакета

```bash
pip install -e ".[dev]"
```

> **Лапки обов'язкові.** Без них `bash` і `zsh` спробують розкрити `[dev]` як glob-шаблон
> і ти отримаєш `no matches found` або мовчазне встановлення без dev-залежностей.
> У PowerShell лапки не потрібні, але й не заважають — пиши їх завжди.

`-e` означає «editable»: пакет ставиться посиланням на цю папку, тож твої правки діють
одразу, без перевстановлення.

**Що дає який extra:**

| Команда | Коли ставити |
|---|---|
| `pip install -e ".[dev]"` | завжди — лінтер + інструмент міграцій |
| `pip install -e ".[s02]"` | етап 2 (NumPy) |
| `pip install -e ".[s03]"` | етап 3 (LangGraph) |
| `pip install -e ".[s04]"` | етап 4 (MCP) |
| `pip install -e ".[s06]"` | етап 6 (FastAPI, Postgres, Redis) |
| `pip install -e ".[s09]"` | етап 9 (LangGraph + CrewAI) |
| `pip install -e ".[embed]"` | справжні локальні ембеддинги |
| `pip install -e ".[voice]"` | етап 7 (Whisper + Piper) |
| `pip install -e ".[prod]"` | усе для розгортання |

Extras складаються: `pip install -e ".[dev,s02,s03]"`.

## 4. Налаштування

```bash
cp .env.example .env
```

**Міняти нічого не треба.** Дефолтний `.env` — це профіль `local` із порожнім
`LLM_API_KEY`, тобто детермінований [FakeLLM](GLOSSARY.md#fakellm) і жодного мережевого
виклику.

## 5. Перевірка

```bash
python scripts/check_all.py
```

Очікуваний вивід:

```
check_all · 1 модул(ів)
  PASS  shared.check (0.12 s)

усе зелене (1 модул(ів), 0.12 s)
```

Якщо зелено — встановлення завершено. Далі можна йти на [етап 1](CURRICULUM.md).

Окремий модуль запускається так:

```bash
python -m shared.check                 # ядро, з деталізацією по перевірках
python scripts/check_all.py s01 s03    # лише названі етапи
```

---

## 6. Опційно: справжня модель

Курс проходиться на FakeLLM повністю. Але щоб побачити, як агент поводиться зі
**справжньою** моделлю, потрібен провайдер. Найдешевший шлях — Groq: безкоштовний рівень,
реєстрація за хвилину, картка не потрібна.

Впиши в `.env`:

```ini
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_твій_ключ
LLM_MODEL=llama-3.3-70b-versatile
```

Альтернативи — у коментарях `.env.example`: OpenRouter, Ollama (повністю локально),
OpenAI (як у статтях-джерелах).

**Як зрозуміти, що саме працює.** Кожне демо друкує банер першим рядком:

```
[FakeLLM] Відповіді розігруються за сценарієм — мережі немає.
[LLM] https://api.groq.com/openai/v1 · model=llama-3.3-70b-versatile
```

Перевірки (`check.py`) **завжди** працюють на FakeLLM, навіть коли ключ заданий — інакше
вони перестали б бути детермінованими й почали б коштувати грошей.

## 7. Опційно: база даних

Потрібна з етапу 6.

```bash
docker compose -f deploy/docker-compose.yml up -d --wait
python scripts/migrate.py up
python scripts/migrate.py status
```

Зупинити: `docker compose -f deploy/docker-compose.yml down`
Зупинити й **стерти дані**: `... down -v`

---

## Типові граблі

**`no matches found: [dev]`**
Забув лапки. Пиши `pip install -e ".[dev]"`.

**`ModuleNotFoundError: No module named 'shared'`**
Не активоване venv, або пакет не встановлений. Перевір префікс `(.venv)` у промпті й
повтори `pip install -e ".[dev]"`.

**Підключення до бази висить, потім падає з таймаутом**
У `DATABASE_URL` стоїть `localhost`. Постав `127.0.0.1`.
Docker публікує порт лише на IPv4, а `localhost` резолвиться **спершу** в `::1` (IPv6) —
клієнт іде туди, слухача там немає, і підключення висить. Явна IPv4-адреса знімає
неоднозначність. У `.env.example` уже правильно.

**`port is already allocated` при `docker compose up`**
На 5432 або 6379 уже щось слухає — найчастіше локально встановлений Postgres або Redis.
Або зупини його, або зміни порт у `deploy/docker-compose.yml` **і** в `.env`.

**`ConfigError: профіль prod налаштований небезпечно`**
Це не баг, а запобіжник: `APP_PROFILE=prod` вимагає `API_KEYS`, `DATABASE_URL`, `REDIS_URL`
і справжнього LLM. Публічний ендпоінт без автентифікації, що ходить до платної моделі, —
відкритий гаманець. Деталі: [SECURITY.md](SECURITY.md).

**Перевірки падають після `git pull`**
Змінилися залежності. Повтори `pip install -e ".[dev]"`.
