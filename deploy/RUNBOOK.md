# RUNBOOK — stage 6

What to do when it breaks. Written **after** four real failures during the first deployment,
not from imagination.

## Bring it up

```bash
cp deploy/.env.prod.example deploy/.env.prod   # and fill it in
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d --build
API_KEY=<key> ./deploy/smoke.sh https://localhost
```

The order is not arbitrary: `migrate` runs **before** `api` (`service_completed_successfully`),
because a service without its table does not merely fail — it stays dead after the table appears.

## Read the state

```bash
curl -k https://localhost/healthz | python -m json.tool
```

| Field | What it means |
|---|---|
| `status` | `up` only when **every** dependency is alive |
| `dependencies.<name>.status` | each one separately; `reason` is the error **type**, not its text |
| `provider` | `real` or `fake`. `fake` in production means ALLOW_FAKE_LLM=1 (ADR-0009) |

**`provider: fake` on a real domain means users are being given invented answers.**
It is visible without a key on purpose.

## What actually broke

### `502` from the proxy, `PermissionError: /data/traces/...` in the logs

The volume belongs to root, the process to an unprivileged user. The directory has to be created
**in the image** with the right owner: Docker copies the image's permissions into a fresh named
volume only on the first mount.

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod down -v
```

The `-v` is mandatory: a volume with the wrong permissions survives an image rebuild.

### `503`, with `store: InFailedSqlTransaction` in the state

A failed query left the transaction in an aborted state. Every subsequent one fails **even after
the cause is gone**. The cause is usually one thing: the migrations did not apply.

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod logs migrate
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod restart api
```

The code rolls the transaction back itself — but a connection taken before the fix stays poisoned
until the restart.

### The service will not start: "the prod profile is configured unsafely"

The guard is doing its job. Read the list — it names each problem separately. If only the provider
is missing and you are bringing the build up **to check something**, set `ALLOW_FAKE_LLM=1` and
remember that the state shows it.

### The scheduler keeps restarting

It fails for the same reasons as `api`, but nothing pokes it from outside, so it can only be
noticed through `ps` or the log.

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod ps
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod logs scheduler
```

**A dead scheduler is invisible in the service's metrics** — named in ADR-0003 as the price of
moving it into its own process.

### The rate limit lets more through than it says

Check `APP_PROFILE`. In `local` the counters are process-local **deliberately**, so with two
workers the limit doubles — that is the stage's exercise, not a defect. In `prod` the counters are
shared:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod exec redis \
	redis-cli --scan --pattern 's06:*'
```

An empty list in `prod` under load means the service is actually in `local`.

## Revoke a key

Keys are read at startup. Remove it from `API_KEYS` and restart `api` and `scheduler`. Revoking
without a restart does not work — the named price of ADR-0006.

## The second deploy — stage 10's assembled service

The capstone **has no HTTP layer of its own**: it substitutes the assembled service into stage
6's application. So it comes up with the same command and a different module:

```bash
uvicorn stages.s10_capstone.serve:app --host 0.0.0.0 --port 8000
```

The variables are stage 6's, plus two of its own:

| Variable | What it does | Default |
|---|---|---|
| `TRACE_DIR` | Where traces are written | `traces/` |
| `MEMORY_PATH` | The memory facts file | `capstone-memory.jsonl` |

**Startup takes longer than stage 6, and that is not a fault.** The knowledge base is indexed
once, at startup; until the index is ready `/healthz` reports `knowledge: false`. An orchestrator
needs slack before its first probe here, or it will restart a service that is merely reading
documents.

The list for a live service is the same one:

```bash
API_KEY=... ./deploy/smoke.sh https://agentic.example
```

**`NOT EVALUATED`:** the run against a real HTTPS domain. It needs a live machine, so it cannot
be reproduced offline, and the stage check says so as a third state rather than green. Locally
(`https://localhost`) the list passes, but trust in the certificate stays unverified — exactly as
at stage 6.

## Tear it all down

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod down -v
```

The `-v` erases **both the facts and the traces**. The volume backup is in the section above.
