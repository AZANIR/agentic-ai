# Setup

The point of this page is to get you to a green `check_all` in five minutes, **with no API key
and no internet**. Everything else — a real model, a database, a deployment — is optional and
comes later.

---

## 1. What you need

| Required | Version | For |
|---|---|---|
| Python | 3.11 or newer | stages 1–5, 8, 9 |
| git | any | cloning |

| Needed later | When |
|---|---|
| Docker + Docker Compose | stage 6 (database, Redis, deployment) |
| An Ubuntu VM, ~4 GB RAM | stages 6 and 10 (a real deployment, about €4–8/month) |

Check Python:

```bash
python --version     # must be 3.11+
```

If the command is not found, try `python3`, or `py` on Windows.

## 2. Virtual environment

```bash
git clone <url> Agentic-AI
cd Agentic-AI

python -m venv .venv
source .venv/bin/activate         # Linux / macOS
# .venv\Scripts\activate          # Windows PowerShell / cmd
# source .venv/Scripts/activate   # Windows Git Bash
```

You know it worked when your prompt gains a `(.venv)` prefix.

## 3. Installing the package

```bash
pip install -e ".[dev]"
```

> **The quotes are not optional.** Without them `bash` and `zsh` try to expand `[dev]` as a
> glob and you get `no matches found` — or, worse, a silent install with no dev dependencies.
> PowerShell does not need them and does not mind them; type them always.

`-e` means editable: the package is installed as a link to this directory, so your edits take
effect immediately with no reinstall.

**What each extra gives you:**

| Command | When to install |
|---|---|
| `pip install -e ".[dev]"` | always — linter plus the migration tool |
| `pip install -e ".[s03]"` | stage 3 (LangGraph) |
| `pip install -e ".[s04]"` | stage 4 (MCP) |
| `pip install -e ".[s06]"` | stage 6 (FastAPI, Postgres, Redis) |
| `pip install -e ".[s09]"` | stage 9 (LangGraph + CrewAI) |
| `pip install -e ".[embed]"` | real local embeddings |
| `pip install -e ".[voice]"` | stage 7 (Whisper + Piper) |
| `pip install -e ".[prod]"` | everything needed to deploy |

Extras compose: `pip install -e ".[dev,s02,s03]"`.

## 4. Configuration

```bash
cp .env.example .env
```

**Nothing in it needs changing.** The default `.env` is the `local` profile with an empty
`LLM_API_KEY`, which means the deterministic [FakeLLM](GLOSSARY.md#fakellm) and no network call
at all.

## 5. Verifying

```bash
python scripts/check_all.py
```

Expected output:

```
check_all · 1 module(s)
  PASS  shared.check (0.12 s)

all green (1 module(s), 0.12 s)
```

Green means the install is done, and you can go to [stage 1](CURRICULUM.md).

To run a single module:

```bash
python -m shared.check                 # the core, check by check
python scripts/check_all.py s01 s03    # only the named stages
```

---

## 6. Optional: a real model

The course runs end to end on FakeLLM. But to see how an agent behaves against a **real** model
you need a provider. The cheapest path is Groq: a free tier, a minute to register, no card.

Put this in `.env`:

```ini
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_your_key
LLM_MODEL=llama-3.3-70b-versatile
```

Alternatives are in the comments of `.env.example`: OpenRouter, Ollama (fully local), OpenAI.

**How to tell which one is running.** Every demo prints a banner as its first line:

```
[FakeLLM] Replies come from a script — there is no network.
[LLM] https://api.groq.com/openai/v1 · model=llama-3.3-70b-versatile
```

The checks (`check.py`) **always** run on FakeLLM, even when a key is configured — otherwise
they would stop being deterministic and would start costing money.

## 7. Optional: the database

Needed from stage 6 onwards.

```bash
docker compose -f deploy/docker-compose.yml up -d --wait
python scripts/migrate.py up
python scripts/migrate.py status
```

Stop it: `docker compose -f deploy/docker-compose.yml down`
Stop it and **erase the data**: `... down -v`

---

## The usual traps

**`no matches found: [dev]`**
You forgot the quotes. Write `pip install -e ".[dev]"`.

**`ModuleNotFoundError: No module named 'shared'`**
The venv is not active, or the package is not installed. Check for the `(.venv)` prefix and run
`pip install -e ".[dev]"` again.

**The database connection hangs, then times out**
`DATABASE_URL` says `localhost`. Change it to `127.0.0.1`.
Docker publishes the port on IPv4 only, while `localhost` resolves to `::1` (IPv6) **first** —
the client goes there, nothing is listening, and the connection hangs. An explicit IPv4 address
removes the ambiguity. `.env.example` already has it right.

**`port is already allocated` on `docker compose up`**
Something is already listening on 5432 or 6379 — usually a locally installed Postgres or Redis.
Either stop it, or change the port in `deploy/docker-compose.yml` **and** in `.env`.

**`ConfigError: the prod profile is configured unsafely`**
Not a bug but a guard: `APP_PROFILE=prod` requires `API_KEYS`, `DATABASE_URL`, `REDIS_URL` and a
real LLM. A public endpoint with no authentication that calls a paid model is an open wallet.
Details: [SECURITY.md](SECURITY.md).

**Checks fail after `git pull`**
Dependencies changed. Run `pip install -e ".[dev]"` again.
