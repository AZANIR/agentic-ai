# Checklist: what has to exist **before** the first deploy

Not "what would be nice to have". Every item here cost a specific breakage — either on this stage
or on the stages that led up to it.

## The order is deliberate

The items go in order of **the cost of the mistake**, not of difficulty. The first three break the
service quietly; the last ones break it loudly, and are therefore cheaper.

## 1. State has to live where every process can see it

**The question:** where does each counter, cache and schedule live — and what happens when there
is a second worker?

Not "will there be a second worker". There will be: a restart during an upgrade, autoscaling, an
accidental `--workers 2` in a command. State in process memory survives exactly until that moment
and breaks **silently**.

The one-line check: *do two independent instances see one number?*

## 2. Migrations are applied by exactly one thing

**The question:** who exactly runs the migrations, and how many times?

Inside the service's startup they run as many times as there are workers. This is the same trap as
with the scheduler, in a place where the price is higher: two processes changing the schema at
once is not a doubled job but a corrupted database.

## 3. A failed query must not poison the connection

**The question:** what does the code do when a query to the database fails?

Without a rollback the transaction stays in an aborted state, and **every subsequent query fails,
even once the cause is gone**. The service does not come back to life after the fix — it has to be
restarted, and the reason for that is not obvious.

## 4. The key must not end up in anything that gets written down

**The question:** walk the logs, the traces, the metrics and the responses. Where is the key in
there?

In the trace, in the database, in the metrics, in an error message. A derived owner identifier does
the same job and is not a key.

## 5. Three refusals have to be three

**The question:** does the client tell "you were not recognised", "wait" and "the money ran out"
apart?

And do the **metrics** tell them apart. "3 % rejected" is three different operator actions merged
into one number.

## 6. Health has to be able to say "broken"

**The question:** what will `/healthz` return if the database is unreachable?

If it is `up`, the endpoint is not needed: it always says the same thing. Health has to name
**every** dependency separately, and an unhealthy one has to make the whole service `down`.

The mirrored half of the same question: does a healthy service actually say `up`? A monitor that
always screams is the same defect as a gate that lets nobody through.

## 7. Data has to survive a restart

**The question:** what disappears after `docker compose up -d --build`?

Everything sitting in the container layer. A volume is not a deployment detail but a requirement.

And immediately the second one: **does the process have the right to write to that volume?** The
volume belongs to root if the directory was not created in the image with the right owner.

## 8. Secrets have to live on the machine

**The question:** what happens if the repository becomes public?

The environment file is in `.gitignore`, the example is in the repository, the real one is on the
server.

## 9. There has to be one way to check that it works

**The question:** how will you know the deploy succeeded?

"Seems to work" is not an answer. One script, the same list against any address, a non-zero exit
code on failure. What cannot be checked is marked as a **third state**, not as a green with an
asterisk.

## 10. What to do when it falls over has to be written down

**The question:** it is three in the morning. What do you read?

`RUNBOOK.md`, written **after** real breakages rather than out of imagination. Every section in it
here is something that genuinely broke during this stage's first deploy.

## What is deliberately not in this checklist

**Backups.** They are needed, and they arrive on stage 10 together with the dashboard and the load
test — that is, together with the rest of what is done **after** the first deploy, not instead of
it.

**Automated deployment.** A terminal and two files. CI that deploys by itself makes sense once
deploying is already boring.

**Multitenancy.** One key, one owner. Roles and per-team quotas are a different product.
