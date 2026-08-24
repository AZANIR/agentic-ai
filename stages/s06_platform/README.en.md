# Stage 6 — Platform: five capabilities become a system

The lesson itself is in Ukrainian ([`README.md`](README.md)). This page is the map: what the
stage claims, which file holds what, and where to break it.

## What it is

Five stages exist and work. There is no system. This stage stitches them into one service and
shows that going to production is not "the same thing, on a server".

> **A prototype answers "does this work?". Production answers "what happens when it breaks at
> three in the morning, and who finds out".**

## Run it

```bash
python -m stages.s06_platform.run           # seven scenes, no key, no containers
python -m stages.s06_platform.run --trace   # plus one request's trace
python -m stages.s06_platform.check         # 59 checks, 45 of them on failure modes
python scripts/mutate.py s06 --expect       # break it on purpose, sixteen exercises

docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d --build
API_KEY=<key> ./deploy/smoke.sh https://localhost
```

## The modules, in reading order

| File | What it holds | Lines |
|---|---|---|
| `guards.py` | three gates — who, how often, at whose expense | 40 / 100 |
| `intent.py` | one branch per model call; the limit is a measured number | 18 |
| `observe.py` | health per dependency, metrics per failure kind | 29 |
| `app.py` | the stitching, and one trace per request | 56 / 120 |
| `jobs.py` | the two-worker trap, behind a flag | 34 |
| `api.py` | three routes and no decisions | 26 |
| `shared/counters.py` | in-memory or shared, one contract | 53 |
| `shared/factstore.py` | file or database, one method set | 73 |

## One sentence

> **State in process memory stops being true the moment there is a second process. And it
> stops silently.**

One cause, three faces: the scheduler runs the job twice (visible in logs), the counter lets
a limit of 30 pass 60 (visible nowhere), and metrics serve one worker's slice (visible once
the numbers stop quite reconciling). The second one matters most — a doubled job gets noticed;
a doubled limit just means the boundary quietly became something else.

## Four defects only deploying found

- **The traces volume belonged to root** while the process runs unprivileged. First write:
  PermissionError, proxy: 502. Locally the directory belongs to whoever ran the command.
- **Nothing applied the migrations.** The first failed query left the connection in an aborted
  transaction, so the service stayed dead *after the cause was gone* — a defect no test sees,
  because every test takes a fresh connection.
- **Config refused to start prod without a paid provider** — correctly, and it blocked
  verification of the real adapters. ADR-0009 records the explicit flag and why health reports
  it.
- **The scheduler restarted silently.** Nothing polls it from outside, which is the price
  ADR-0003 named for moving it out.

## What this stage does not prove

- **One key, one owner.** No roles, no per-team quotas; revoking a key needs a restart.
- **The budget counts an estimate**, not the provider's invoice. A guard should fire before
  the catastrophe, not balance the books.
- **Metrics are process-local.** With N workers the endpoint serves one worker's slice.
- **The trace does not explain retrieval.** Stages 2 and 5 write no steps, so it answers
  "which branch" and not "why these documents" (ADR-0005).
- **Certificate trust was not verified.** Locally it is self-signed by construction, and the
  smoke script marks that as a third state rather than a pass.
- **No backups.** `down -v` erases both facts and traces; copies arrive in stage 10.

## Where to break it

Sixteen mutations in `mutations.json`, each pinned to the checks it must turn red. The three
worth your time leave the code **working and wrong**: the counter becomes process-local, the
owner filter leaves the query, and the budget is checked before the rate limit.

Walkthrough in [`exercises.md`](exercises.md), written in Ukrainian.
