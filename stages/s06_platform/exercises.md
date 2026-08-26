# Stage 6 exercises — break it and see what goes red

Before every exercise, run the suite and make sure it is green:

```bash
python -m stages.s06_platform.check
```

The numbers were measured **with the database up**. Without it six checks become `NOT VERIFIED`
rather than red, and the count of reds drops — a third state does not equal a green:

```bash
docker compose -f deploy/docker-compose.yml up -d --wait
python scripts/migrate.py up
python scripts/mutate.py s06 --expect
```

**Read the names, not the count.** A mutation caught by an incidental check is worse than one
caught by the check that claims to be about it.

---


## Exercise 1 · The counter in the shared store becomes process-local

`shared/counters.py`:

```python
# before
    if client is not None:
        return Shared(client)

# after
    if client is not None:
        return InMemory()
```

**Reds: 2.**

The most important of the sixteen. The counter becomes process-local — and **everything keeps
working**: requests go through, refusals arrive, metrics get counted. The boundary simply means
something else.

What goes red is exactly the check that claims sharedness: two independent instances see one
number. No rate-limit check replaces it — on a single instance the limit is correct.

---

## Exercise 2 · The set member is made of time and amount again

`shared/counters.py`:

```python
# before
        member = f"{now:.6f}:{uuid4().hex[:8]}:{amount}"

# after
        member = f"{now:.6f}:0:{amount}"
```

**Reds: 3.**

The set member is made of time and amount again. Two events at the same instant with the same
cost become one member, because a set does not hold duplicates.

The defect is one-sided: the counter **under**counts. Six requests in one instant pass with a
limit of three. It was found not through a red but through a mirrored check — the contract fixture
advanced time every step and therefore never produced the case that tells the two implementations
apart.

---

## Exercise 3 · Reading the counter cleans the store again

`shared/counters.py`:

```python
# before
        return sum(value for at, value in self._events.get(key, []) if now - at < window)

# after
        return sum(value for _, value in self._prune(key, now=now, window=window))
```

**Reds: 2.**

Reading the counter cleans the store again. A question about a window that has already passed
erases the event for good — the next request inside the window sees zero.

A method called "how much" has no right to delete.

---

## Exercise 4 · The key comparison becomes a plain equality

`stages/s06_platform/guards.py`:

```python
# before
    known = any(hmac.compare_digest(given, candidate.encode()) for candidate in settings.api_keys)

# after
    known = any(key == candidate for candidate in settings.api_keys)
```

**Reds: 2.**

The constant-time comparison becomes a plain `==`. Functionally **nothing changes**: keys are
compared, foreign ones are rejected, ours pass.

The only thing that changes is that the response time starts telling you the length of the shared
prefix.

> **This exercise gave zero reds at first.** The property was correct and held by nothing — that
> is, it lived exactly until the next refactoring. A check had to be written: a structural claim
> about the presence of `compare_digest`, not a timing measurement.

---

## Exercise 5 · The limit is counted per service rather than per owner

`stages/s06_platform/guards.py`:

```python
# before
    seen = counters.add(f"rate:{owner}", 1, now=now, window=MINUTE)

# after
    seen = counters.add("rate:everyone", 1, now=now, window=MINUTE)
```

**Reds: 4.**

The limit is counted per service rather than per owner. One client exhausts the quota for
everybody.

The most reds of the sixteen — and that does **not** make the exercise the most important one: the
limit sits next to everything, so it touches many checks. Exercise 1 gives one red and is worse.

---

## Exercise 6 · The budget is checked before the rate limit

`stages/s06_platform/guards.py`:

```python
# before
    for gate in (within_rate, within_budget):

# after
    for gate in (within_budget, within_rate):
```

**Reds: 2.**

The budget is checked before the rate limit. The service starts counting the spend of those it is
going to reject anyway, and the order of the gates stops being a decision.

---

## Exercise 7 · The key goes into the trace instead of the derived owner

`stages/s06_platform/guards.py`:

```python
# before
    return hashlib.sha256(f"{salt}:{key}".encode()).hexdigest()[:16]

# after
    return key
```

**Reds: 5.**

The key itself goes into the trace instead of the derived identifier. A key in a trace is a key in
a file read by whoever is debugging; and in the database, and in the metrics, and in the build
logs.

---

## Exercise 8 · The spend is not recorded

`stages/s06_platform/guards.py`:

```python
# before
    return counters.add(f"spend:{owner}", amount, now=now, window=DAY)

# after
    return counters.total(f"spend:{owner}", now=now, window=DAY)
```

**Reds: 4.**

The spend is not recorded. The breaker stays in place and **never fires**: every time it asks
about zero.

The mirrored half: the check "the budget rejects" is green under this mutation too, because its
fixture accrues the spend itself.

---

## Exercise 9 · The owner filter is removed from the database store

`shared/factstore.py`:

```python
# before
            " WHERE owner = %s ORDER BY stored_at",
            (owner,),

# after
            " ORDER BY stored_at",
            (),
```

**Reds: 2.**

The owner filter disappears from the query to the database. Somebody else's rows come back from
the store — and that is exactly why isolation is checked against **both** implementations, not
only the file one.

---

## Exercise 10 · A failed query no longer rolls the transaction back

`shared/factstore.py`:

```python
# before
            self._connection.rollback()
            raise

    def _execute

# after
            raise

    def _execute
```

**Reds: 2.**

A failed query no longer rolls the transaction back. The next ones fail **even once the cause is
gone** — the service stays dead after the fix.

Found by a real deploy: the table was not there, and after it appeared nothing got better.

---

## Exercise 11 · Health reports "alive" regardless of its dependencies

`stages/s06_platform/observe.py`:

```python
# before
            "status": UP if all(d["status"] == UP for d in seen.values()) else DOWN,

# after
            "status": UP,
```

**Reds: 2.**

Health reports "alive" regardless of its dependencies. The monitor stays quiet until a user
complains.

---

## Exercise 12 · The reason in health becomes the error's text rather than its type

`stages/s06_platform/observe.py`:

```python
# before
            return DOWN, type(error).__name__

# after
            return DOWN, str(error)
```

**Reds: 3.**

The reason in health becomes the error's text instead of its type. The database driver's text
carries the address, the user and the port — and health is read by somebody who has no key.

---

## Exercise 13 · Metrics stop telling failure kinds apart

`stages/s06_platform/observe.py`:

```python
# before
        self.requests[kind] += 1

# after
        self.requests["all"] += 1
```

**Reds: 2.**

Metrics stop telling failure kinds apart. "3 % rejected" describes broken authentication, abuse
and an exhausted budget equally well — three different operator actions.

---

## Exercise 14 · The scheduler moves back inside the application

`stages/s06_platform/jobs.py`:

```python
# before
        if self.mode != INSIDE or now < due_at:

# after
        if now < due_at:
```

**Reds: 3.**

The scheduler moves back inside the application. The job runs twice per interval.

This is the half that **is** visible in the logs. The other one is exercise 1.

---

## Exercise 15 · The service dies together with an unreachable dependency

`stages/s06_platform/app.py`:

```python
# before
        except Exception as error:  # noqa: BLE001 — межа сервісу: далі летіти нікуди

# after
        except KeyboardInterrupt as error:
```

**Reds: 2.**

The service stops catching dependency errors. An unreachable store takes the process with it: one
request is worse than all requests.

---

## Exercise 16 · The prod profile starts with a fake and no permission at all

`shared/config.py`:

```python
# before
        if not self.has_real_llm and not self.allow_fake_llm:

# after
        if False:
```

**Reds: 2.**

The `prod` profile starts with a fake and no permission at all. The service serves real users
inventions, and nothing says a word about it.

---

## Exercise 17 · The service checks one rule of the checklist instead of six

`stages/s06_platform/app.py`:

```python
# before
        decision = decide(_looks_like(question))

# after
        decision = decide(Situation(text=question, asked=True))
```

**Reds: 2.**

The service checks **one** rule of the checklist instead of six — the one the first draft started
from. The password is stored in memory and lands in the trace together with the reason for
discarding it.

Stage 5 deliberately put the secret **before** the request, because "remember my password"
satisfies both rules. Skipping the first three means teaching the reader a checklist and not using
it yourself.

---

## Exercise 18 · The derived owner is unsalted again

`stages/s06_platform/guards.py`:

```python
# before
    return hashlib.sha256(f"{salt}:{key}".encode()).hexdigest()[:16]

# after
    return hashlib.sha256(key.encode()).hexdigest()[:16]
```

**Reds: 2.**

The derived owner identifier is unsalted again. The promise "the key cannot be recovered from it"
stops being true: keys are short, `sha256` is deterministic across every deployment, and a
dictionary recovers `change-me-too` in a few attempts.

Whoever got hold of a trace — and the lesson insists that traces are read while debugging — got
the key as well.

---

## What to do next

Try **your own** mutation: break something and see whether anybody notices. If the suite stayed
green — you have found a hole in the checks, and that is worth more than any of the eighteen
above.

That is how exercises 4, 17 and 18 were found: the first gave zero reds, and the last two appeared
after an independent review asked about every check — **what exactly has to break for it to go
red?**

And separately — break the **deployment**:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod stop postgres
curl -k https://localhost/healthz | python -m json.tool
```

Health has to say `down` and name `store` by name. If it says `up` — you have found exercise 11 in
a live service.
