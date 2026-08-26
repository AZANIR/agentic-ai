# Checklist — stage 6

Three levels. Passing means closing all three, not the first.

## I understood

- [ ] I can name the three boundary mechanisms and their three **different** failures.
- [ ] I understand why the gates are in that order, and what breaks if they are swapped.
- [ ] I can explain why a constant-time key comparison is not pedantry.
- [ ] I tell apart the questions health, metrics and the trace answer. Each has its own.
- [ ] I can name the **three faces** of one piece of state in process memory and say which of
      them is the most dangerous. Hint: not the one visible in the logs.
- [ ] I understand why migrations are a separate container rather than a step in the service's
      startup.
- [ ] I know what this stage does **not** promise: that metrics will reconcile across N workers.

## I ran it

- [ ] `python -m stages.s06_platform.run` — seven scenes; read the sixth carefully.
- [ ] `python -m stages.s06_platform.run --trace` — saw the order of the steps in the trace.
- [ ] `python -m stages.s06_platform.check` — all green; 69 checks, 57 of them on failure modes.
- [ ] `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env.prod up -d --build`
      — five containers, the scheduler among them.
- [ ] `API_KEY=<key> ./deploy/smoke.sh https://localhost` — 10 passed, 0 failures,
      1 **not verified**. Without `API_KEY=` it will be 8 passed and 3 not verified — and that is
      a correct answer too: the script does not pretend to have checked what it could not.
- [ ] `python scripts/mutate.py s06 --expect` — the numbers in the exercises match the run.
- [ ] Stopped `postgres` and looked at `/healthz`: `down`, and `store` named by name.
- [ ] Did exercise 1 and saw that the limit stayed "correct" on a single instance.

## I explained

Not to myself — out loud, to another person or in writing.

- [ ] **Why is a doubled limit more dangerous than a doubled job?**
      Hint: one is visible in the logs, the other nowhere.
- [ ] **Why must a refusal not say whether such a key exists?**
      Hint: keep trying until the text changes.
- [ ] **Why does health name the error's type rather than its text?**
      Hint: who reads health, and what is in the database driver's text.
- [ ] **Why is "the service is alive" with no list of dependencies a bad answer?**
      Hint: the process is alive, the database has been unreachable for an hour.
- [ ] **Why are migrations inside the service's startup the same trap as the scheduler?**
      Hint: as many workers, as many attempts to change the schema.

## I am ready for what comes next

- [ ] I can name the four defects that deploying itself found, and say why they are not visible
      from the code.
- [ ] I can explain why `ALLOW_FAKE_LLM` is named exactly that and why health reports it.
- [ ] I know the six limits of the stage named in the lesson — and none of them is a surprise.
