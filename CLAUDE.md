# Notes for agents working in this repository

Full rules: [CONVENTIONS.md](CONVENTIONS.md). How a stage gets made: [PLAYBOOK.md](PLAYBOOK.md).
Architecture: [docs/architecture-map.md](docs/architecture-map.md).
Decisions and their reasons: [docs/adr/](docs/adr/). Do not overturn them silently — if you
disagree, write a new ADR.

## Commands

```bash
pip install -e ".[dev]"           # install (the quotes matter)
ruff check . && ruff format .     # lint and format
python scripts/check_all.py       # every check, offline, no keys
python scripts/clean_install.py   # the same, but as CI runs it: without optional packages
python scripts/migrate.py up      # migrations (needs docker compose up)
```

## What matters most

1. **`if profile == ...` inside stage code is forbidden.** Branching on the profile lives only
   in the factories under `shared/`.
2. **No `openai.OpenAI()` outside `shared/llm.py`.** Stages take a client through
   `get_client(demo_script=[...])`.
3. **Every `check.py` has at least one check on a failure mode** (docstring prefixed
   `FAILURE ·`). A happy path proves nothing.
4. **Everything must work offline and with no API key.** If a check needs the network, the
   check is broken, not the network.
5. **Everything committed here is in English.** Prose, docstrings, comments, check messages,
   commit messages. See the language table in CONVENTIONS.md. Drafts and anything under
   `sources/` may be in any language — they are gitignored.
6. **No mention of AI assistants in commits, PRs or documentation** — no co-authorship, no
   "generated with", no tool names.

## Where things go

| What | Where |
|---|---|
| A new stage | `stages/sNN_slug/`, following the template in CONVENTIONS.md |
| A new adapter (provider, store, trace sink) | `shared/`, always with both implementations |
| A new agent tool | An MCP tool; fewer tools with clean payloads beat a map of endpoints |
| Infrastructure | `deploy/`, updating `deploy/RUNBOOK.md` with it |
| A database table | A migration in the stage that needs it, not ahead of time |
