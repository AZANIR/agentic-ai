# Playbook — how a stage gets made

A working document. It records **exactly how** a stage of the course is built: the sequence,
the gates, the criteria, and the lessons that have already cost us mistakes. The goal is
simple — so that stage 2 does not have to be reinvented, and stage 7 does not repeat stage 1's
mistakes.

[CONVENTIONS.md](CONVENTIONS.md) says **how to write the code**. This file says **how to drive
a stage to done**.

> Where the numbers come from: stage 1, taken all the way through, independent review included.
> The record: [`_review/review-2026-08-23.md`](docs/features/s01-agent-loop/_review/review-2026-08-23.md).

---

## 1. The stage pipeline

Nine steps. Only the ones explicitly marked skippable may be skipped.

| # | Step | Command | Artefact |
|---|---|---|---|
| 1 | Specification | `/sdd:specify sNN-slug` | `spec.md`, `.size`, `.route` |
| 2 | Clarification | `/sdd:clarify sNN-slug` | an updated `spec.md` |
| 3 | Architecture | `/sdd:design sNN-slug --depth=easy` | `sad.md`, `adr/*.md` |
| 4 | Test plan | `/sdd:plan-tests sNN-slug` | `## Test plan` inline in `spec.md` |
| 5 | Tasks | `/sdd:tasks sNN-slug` | `tasks.json`, `tasks/`, `tracker.md` |
| 6 | Implementation | `/sdd:implement sNN-slug` | code + checks + commits |
| 7 | **Review** | `/sdd:review sNN-slug` | `_review/review-YYYY-MM-DD.md` |
| 8 | Fixes | — | MAJORs closed, MINORs deferred into §8 |
| 9 | Tag + article | `git tag stage-NN` | the tag, `sources/artstroy/{slug}/index.mdx` |

**Auto-skips on the `quick` route** (size XS/S), each with its reason stated:
`sequences` — when SAD §6 already carries the critical flows · `data-model` — when the schema
does not change · `api` — when there is no contract · `screens` — when `target_surfaces` names
no UI.

**What may never be skipped:** step 7. The reason is in §4.

## 2. A realistic budget

Measured on stage 1 (size S).

| Phase | Share |
|---|---|
| Documents (steps 1–5) | ~35% |
| Code and checks (step 6) | ~30% |
| **Review and fixes (7–8)** | **~25%** |
| Article (step 9) | ~10% |

Plan on the basis that **code and tests are about half the work**. The other half is proving
they do what you think they do. On stage 1 the review found seven MAJORs **after** everything
was green and declared finished.

## 3. Definition of Done

A stage is finished when **every** item holds. Not "the code works".

1. `README.md`: what you will be able to do after the stage → the canonical idea → the bridge
   to NovaShop → what to break.
2. `README.md` opens with an orientation block that fits one screen.
3. `python -m stages.sNN_slug.run` works **with no API key**.
4. `python -m stages.sNN_slug.check` is green offline; at least one check covers a **failure
   mode**.
5. `exercises.md` (3–5 tasks with expected results) + `solutions/` + `CHECKLIST.md`.
6. New terms added to [GLOSSARY.md](GLOSSARY.md).
7. Status updated in [CURRICULUM.md](CURRICULUM.md) and in the root README.
8. **Review passed, every MAJOR closed**, MINORs deferred with an owner and a due date.
9. Tag `stage-NN` created and pushed; the article written and linking to the tag.

Stages 6 and 10 additionally: `deploy/smoke.sh` passes against a real HTTPS URL.

## 4. The review gate is mandatory

**Two independent reviewers in clean context, in parallel.** Not one, and not whoever wrote the
code.

| Stage | What it looks for |
|---|---|
| 1 | Tracing US → AC → `file:line` of code → the check function. Separately: ACs **not claimed** by the `SDD-AC` trailers. Recomputing every numeric NFR by hand |
| 2 | Conventions taken literally, edge cases, security, whether the tests have teeth, whether the teaching text contradicts the code |

### Why two, and why not the author

An author checks the code against **their own model of what the code should do**. If the idea
itself is wrong, that is invisible from the inside: the tests were written by the same head and
they agree with the code. Both are wrong together.

On stage 1 the confirmation gate worked exactly as designed — per generation. That a
per-generation gate turns confirmation into blanket permission was seen only by a clean context.

The split into two stages is not a formality either. Stage 1 runs **from spec to code** and
finds what is **missing** — a requirement nobody implemented; it cannot be seen by looking at
the code, because it is not there. Stage 2 runs **from code to consequences** and finds what is
there but breaks at the edge. A single reviewer almost always slides into the second pass: code
is concrete, and a missing requirement is silent.

### Resolving findings

Each one is **Fix** / **Defer** (owner plus due date in §8 of the spec) / **Not an issue**
(with the reason). No open stage-1 finding ships.

## 5. Lessons already paid for in mistakes

Each one comes from a real event on stages 1–3. Re-read them before every stage.

### A file that has been read is not proof that it runs

Two independent reviewers in clean context read `ws.py`, traced the criterion to its line, and
described what happens there. Live mode had meanwhile not worked **once since the day it was
written**: `from __future__ import annotations` turned the socket annotation into a string, the
type was imported inside a factory, and FastAPI, unable to resolve the name, treated the socket
as a query parameter. Every connection closed before `accept()`.

The first run found it, a minute after both reviews finished.

Why nobody found it earlier: **every check for that module read it as text.** That was done
deliberately and correctly, so the suite would not drag a web framework into the base install.
And precisely because of it, the module executed nowhere, CI included.

**Rule:** if a module's checks only **read** it, at least one has to **run** it. No optional
package — `NOT EVALUATED`, and the extras job then applies the "nothing is left unverified"
rule. Reading proves intent; running proves fact.

### An invariant with two terms where there are three participants stays green and lies

"The sum of the steps equals the total time" is true while the pipeline owns the clock alone.
The moment a consumer takes fragments at its own pace, its pause lands silently on the **next**
step. Measured: a model that slept 750 ms reported 2750, and the sum still added up perfectly.

The most expensive step became whichever one the browser happened to think after — and that is
exactly the one a reader would go and optimise.

**Rule:** a sum invariant has to name **every** owner of time, and the remainder "attributed to
nobody" has to be checked separately against zero. Plus the mirror half: not only "the sum adds
up" but "this share equals how long that participant actually worked". Without the second half,
conservation is satisfied even when someone else's time was booked to a named step.

**Aside:** `total` must not be computed as the sum of its parts — that turns the law into an
identity and it stops catching a step nobody measured.

### Boundary arithmetic is checked across several input sizes, not one

p95 was taken as `round(0.95·n)` instead of `ceil(0.95·n)`. At a hundred runs the two formulas
agree — and the check stood at exactly a hundred. At thirty, p95 landed on the fastest run with
6.7 % worse than it, and `tail_ratio` dropped below one: "there is no tail". They disagree on 95
of the first 200 sample sizes.

**Rule:** a check on a formula using `round`, `ceil`, `//` or a slice runs a **list** of sizes,
not one. A single size is one happy point, and it is almost always happy, because it was chosen
while looking at the code.

### An instruction that punishes obedience is worse than no instruction

`pip install -e ".[voice]"`, and on the next line `uvicorn ...`. The `voice` extra held model
weights and no web package at all. A reader who installed **nothing** got a polite "install
this" message; a reader who installed it got `command not found`, and before that a
`ModuleNotFoundError` from a file that did not exist in the repository.

Same class: the documented `uvicorn ...:create_app --factory` brought up the **fake** mode,
because `--factory` cannot pass arguments.

**Rule:** commands quoted in a lesson are checked against the manifest — the named extra exists
and brings what the next line calls; the named factory enables the mode the prose claims.

### "The fake cannot produce X by construction" is a virtue, not an excuse

The criterion demanded "a hundred runs **with a spread of latencies**". A fake clock produces no
spread — that is its whole value. So the distribution was typed in as literals, and the demo
printed "runs: 100" for a hand-written list, on a stage whose thesis is that only what is
measured can be optimised.

The way out is neither to make the clock non-deterministic nor to rewrite the criterion. The
spread belongs in **another layer**: the model's delay became a pure function of the run number.
A hundred real runs, a real tail, and a repeat run gives the same hundred numbers.

**Rule:** when the "Given" cannot occur because of a property of the fake, look for the layer
where that property can be introduced deterministically. Literals in a test satisfy the "Then"
and not the "Given" — and it is usually the "Then" that gets checked.

**Aside:** a tail made of one tier makes p95 equal to the worst case. Two tiers, and the
difference between "almost worst" and "worst" is visible again.

### A mutation test proves the test reacts — not that it reacts **to that**

I disabled the gate, saw red, and declared it proven. In fact the check was failing with
`FakeLLMError: script exhausted` — it never reached the assertion. A test with the right verdict
and the wrong cause **passes mutation testing**, which means it looks reliable by exactly the
criterion used to judge it.

**Rule:** after a mutation, read the **cause** of the failure, not only the fact of it. If it is
not an `AssertionError` with meaningful text, the test does not prove what you think.

**Aside:** the fake's script has to contain a step **after** the one being checked. Otherwise a
disabled guard leads to an exhausted script instead of a fired assertion.

### Defaults at a trust boundary are fail-closed only

The unknown-field check worked only when the schema's author remembered
`additionalProperties: false`. All three of our tools had it, so nothing went red — and the
exercise asks the reader to add a fourth.

**Rule:** a guard that works only when switched on is an understanding, not a trust boundary.

### A backup lives outside the system you are rewriting

Before `git filter-branch` I made `git tag backup-before-rewrite`. `filter-branch` dutifully
rewrote **the tag itself**, and the local copies of the articles were gone for good.

**Rule:** `cp -r` into a directory outside the repository **before** the first destructive
command. A backup inside the thing you are rewriting is not a backup.

**Aside:** `filter-branch` leaves the originals in `refs/original/`, and `git rev-list --all`
still sees them. Without `update-ref -d` plus `gc --prune=now` they would have gone out in the
push.

### `ruff format` rewrites code inside markdown

It turns the fragment `description="x",` into `description = ("x",)` — in isolation that really
is valid Python (a tuple assignment). A lesson full of fragments is prose, not code for the
compiler.

**Rule:** `extend-exclude = ["*.md"]` in `[tool.ruff]`. Already done.

### `localhost` resolves to IPv6 first

Docker publishes the port on IPv4 only. Measured: IPv4 connects in 26 ms, IPv6 refuses after
2041 ms.

**Rule:** `127.0.0.1` in every connection string, plus a `connect_timeout` in the connector.

### Heuristics in tests break on inflected languages

Twice in a row: `"Kyiv" in weather` (the language inflects — "in Kyiv" becomes a different word
form) and `"'" not in reason` as an indicator of a dumped structure (the word for "required"
contains an apostrophe).

**Rule:** check what actually matters — the content, the structural brackets, the specific
fields — rather than an indirect sign that happened to correlate.

### Numbers in prose are derived from code, not typed

In an article draft I showed the trace call shorter than it is. The defect lived four minutes,
until the first automatic check of the snippet against the file.

**Rule:** every number and every fragment in an article is verified by script against the
repository. The verification is in §8.

### When the line budget is reached, extract a module rather than raise the budget

`loop.py` stood at 116/120, and the review fixes added about 13 lines. The mitigation was
written into `sad.md` §11 **in advance** — the gate moved out into `gate.py` and the budget
stayed intact.

**Rule:** a risk with a mitigation written down beforehand is not an emergency; it is the plan
working.

### A test that "the bad thing did not happen" never replaces a test that "the good thing did"

Stage 2. The access filter has to sit **before** the top-k selection. Put it after, and an
internal document takes a slot, gets removed afterwards, and the asker receives "nothing found"
instead of the correct answer that was ranked third.

**Nothing leaked. The leak check stays green.** What disappears is the permitted answer — and
there was no check for that until I wrote one separately.

The same failure recurred within the same stage by a different mechanism: dropping
`partial(search_knowledge_base, access=access)` causes no leak (the `PUBLIC` default is
fail-safe), but the operator stops seeing what they are allowed to see. Again no leak check
fired.

**Rule:** for every "the forbidden thing did not get through" check, write its mirror — "the
permitted thing arrived". These are different claims, and covering one gives a false sense that
both are covered.

### Whether a defect is visible can depend on a parameter unrelated to it

That same filter defect **does not show at all** at `top_k=3`: the right answer still fits into
the three alongside two internal fragments, and both orderings give the same result. At
`top_k=2` the result becomes empty. The code is equally broken either way; only its visibility
changes, and that is decided by a parameter that has nothing to do with access control.

A check written "like production" (with `top_k=3`) would be green on broken code.

**Rule:** a parameter chosen in a check so that the property becomes observable is not
artificial — it is part of the proof. Write down **why that value** next to the check, or the
next refactor will "align it with production" and silently switch it off.

### An assertion with the right verdict and a weak claim

The first version of the tool-shape check said `"query" in params["properties"]`. A mutation
adding `access` to the schema — precisely what the check was meant to guard against — passed
straight through it. A green check over a broken property.

**Rule:** for a property of the form "exactly this and nothing else", the assertion is
`list(...) == [...]`, not `x in ...`. "Is among them" and "is only" are different claims.

### A mutation run can poison the bytecode cache

Replacing `0.2` with `0.0` and putting it back **within the same second** leaves the old `.pyc`
valid: Python compares the modification time to one-second precision along with the file size,
and both matched. The check failed on already-restored code, and a minute went into hunting a
bug that did not exist.

**Rule:** the mutation harness clears `__pycache__` after a rollback. The same warning goes into
every stage's `exercises.md`, because the reader performs exactly these mutations.

### Ruff catches incompatibility with the version floor that a local run cannot see

`f"...{list(params["properties"])}"` — nested identical quotes inside an f-string are allowed
from Python 3.12. Locally 3.14 is installed, so everything worked; the repository floor is
`>=3.11` and the CI matrix includes 3.11. It would have failed in CI, not here.

**Rule:** `ruff check` is neither cosmetic nor about style. Run it before every commit, not
before the push.

### A mutation harness has to prove the suite ran at all

Stage 2. A mutation broke the file's syntax — and the harness reported **"0 red"** for six
mutations in a row. It was looking for `FAIL` lines in the output; when a module does not
import there are none, and "nothing failed" is indistinguishable from "all is well".

Which means the tool used to check whether a test lies had lied in exactly the same way.

**Rule:** the harness counts **how many checks executed** and shouts when there are fewer than
there should be. Without that, "the mutation was not caught" and "the mutation broke the build"
produce the same output.

### An edit through `sed` with `\n` in the replacement inserts a real newline

The same thing three times in one stage: `\n` inside a Python string written inside a bash
string is processed twice and arrives in the file as a line break. The most expensive instance
broke an f-string and took down the previous lesson.

**Rule:** for code edits containing `\n`, edit by line index or write a separate file in the
scratchpad — never a text substitution passing through two shells.

### A leak check has to first assert that the run happened

Stage 3, the third instance of the same shape in three stages. The check "request text does not
raise the access level" was green against a mutation that **broke the specialist**: it crashed,
`safely()` caught it, the run finished as a failure — and nothing leaked, because nothing
happened at all.

The shape is general: **"the bad thing did not happen" is true when nothing happened.** A crash,
an empty result, an exception, an abandoned route — all of them pass a leak check.

**Rule:** a check for something forbidden starts by asserting that the permitted thing occurred
— `finish_reason == "answered"`, a non-empty result, the step executed. Only then does asking
whether anything leaked mean something. Otherwise the most reliable way to pass a security check
is to break the code.

### A check guarding a constant must not iterate that same constant

Stage 3. The immutability check for `access` was written like this:

```python
for name in sorted(FROZEN):
    ...assert setattr raised...
```

Empty `FROZEN` and the loop body never runs. The suite stays **entirely green** while the door
stands open. Worse: the lesson told the reader to make exactly that mutation ("remove `FROZEN`")
while `exercises.md` named a different one (`if name in FROZEN:` → `if False:`), and that one
did go red. **Two instructions for the same exercise with opposite outcomes.**

**Rule:** the check asserts the constant's contents explicitly (`assert FROZEN == {...}`) and
the behaviour by field name, not by iterating the very thing under test. Otherwise the mutation
"the list is empty" passes through the check that exists against it.

### "NOT EVALUATED" has to be its own state, or a green suite lies

The check comparing two implementations did a `return` when an optional library was missing —
and reported `ok`. So "they matched" and "we did not look" printed identically. In CI the
library was never installed, so the only guard against the two implementations diverging ran
nowhere, and the pipeline was green.

**Rule:** a third state in the runner (`NotVerified`), its own counter in the summary — and a
separate CI job that installs the extras and **fails** if anything is still unexecuted. Without
the second half, the first state merely documents that nothing is being checked.

### A mutation that does not compile produces the most convincing false numbers

The measurement "exercise 3 → nine red checks" was wrong: the mutation wrote `access=PUBLIC`
into a module where `PUBLIC` was not imported. The `NameError` was caught by `safely()`, every
request became `specialist_failed`, and nine checks went red instead of three. The number looked
solid, and the explanation beneath it described an entirely different mechanism — contradicting
itself two paragraphs later.

**Rule:** the mutation harness checks that the modified file **imports** before counting red.
Measurements for exercises are taken with exactly the text written in the exercise, and copied
from the run rather than paraphrased.

### The mutation harness is a repository tool, not three lines written on the spot

Those three lines were written six times and failed three, silently each time: a stale `.pyc`
after a rollback within the same second; a killed run that left the file broken; a measurement
on a mutation that did not compile. It is now `scripts/mutate.py`, with the rollback in a
`finally`, a marker on disk and a counter of executed checks.

Its point is not convenience but `--expect`: the numbers promised in the exercises live in
`stages/<stage>/mutations.json`, and the run **fails** when the prose and the fact have parted
company.

**Rule:** no number of the form "this many checks will go red" is typed into a lesson by hand.
It is copied from a run and pinned in `mutations.json`.

### A linter can make an exercise's instruction impossible to follow

Exercise 3 told the reader to write `access=PUBLIC` — and `ruff --fix` removed that import as
unused, because nothing was using it. A reader who followed the instruction literally got a
`NameError`, which `safely()` caught, and saw ten red checks instead of three — all for the
wrong reason.

**Rule:** a mutation in an exercise must not need anything the file does not already have. A
literal (`access="public"`) instead of a constant; and `--expect` catches this, because it
measures exactly the text written in the exercise.

### A local venv is not CI, and the difference is invisible until you push

`numpy` sat in stage 2's extras, even though `shared/embeddings.py` imports it
**unconditionally** and `shared/check.py` — the core checks — execute it. CI installs `[dev]`.
Both matrix jobs died on `ModuleNotFoundError` **before the first check**, on both Python
versions alike.

Locally nothing showed: numpy was in the venv because stage 2 had pulled it in. By the time the
cause was named, stage 3 was already pulling numpy transitively — the next push would have given
three broken modules instead of two.

**Rule:** a package that a shared layer imports at module level is a **core** dependency,
whatever the extras table says. Before a push — `python scripts/clean_install.py`: an import
blocker in `sys.meta_path` via `sitecustomize.py`, so that it survives subprocesses. Twenty
lines, and the class is closed entirely.

### "Not evaluated" must not hide "broken"

The temptation after the previous lesson is to teach the run to count any death on import as
`NOT EVALUATED`. That would turn CI green on the very bug that had turned it red: a broken
build would read as "the stage simply was not run".

**Rule:** optionality is decided by `pyproject.toml`, not by the fact of absence. No `langgraph`
(it is in extras) — `NOT EVALUATED`. No `numpy` (it is core) — `FAIL`, exit code 1. In a
traceback they look identical, and only the dependency table tells them apart.

### A CI step that searches the output for a word must have that word in the output

`check_all.py` printed a module's output only in the "it failed" branch. A module that finished
successfully lost its `NOT EVALUATED` lines — so `grep -q` in CI missed **every time**, and the
job stayed green regardless of anything. The rule was formally there; it was blind.

**Rule:** having written a step that searches for something, check by hand that the thing
searched for appears in the output at all. The cheapest way is to run that same `grep` locally
and see a non-empty result at least once.

### A check that reads git history reads a different history in CI

`actions/checkout` makes a **shallow clone with no tags**. The "the stage below has not changed"
checks compare against the previous stage's tag — and in CI they failed with
`fatal: bad revision 'stage-02'`, while locally they worked flawlessly.

This is the same class as the uninstalled package: the check has no input material. And the cure
is the same, both halves:

    fetch-depth: 0    so that in CI it actually executes
    NotVerified       so that in a fresh clone without tags it does not go red

The second half alone is not enough — without the first the check never executes anywhere.

**Rule:** everything a check takes from outside the stage's own filesystem — tags, environment
variables, the network, the clock — looks different in CI. Check it explicitly, do not assume.

### A "the stage below has not changed" check must name what exactly must not change

That same `require_tag` edit, shared across the whole repository, passes through **every**
stage's `check.py` — and the "stages 1 and 2 have not changed" check went red on it. Formally
correct; in substance not: the lesson's claim is that **the loop** did not change, not that the
stages below will never receive another line.

**Rule:** such a guard is limited to the implementation files (`:(exclude)…/check.py`), and the
reason is written next to it. Otherwise the first infrastructure refactor poses a choice: break
the check or skip the refactor.

### A spec self-check has to check both directions

The first version of the script verified "every criterion has a row in the test plan". The
reverse direction — "every row of the plan has a criterion" — was not checked, and stage 3's
spec turned out to hold three rows referring to criteria that did not exist in §5.

When the script finally became bidirectional, it immediately found **the same hole in stage 2**,
where it had lived for two weeks and survived an independent review.

**Rule:** any reconciliation of two lists is done in both directions. A one-way one suffices
exactly until the mistake is on the side you are not checking. The script is
`scripts/spec_check.py`; run it on every spec before a commit.

### An apostrophe in a Ukrainian word closes the bash string

The third time in one session: words like *rev'yu*, *z'yavylos*, *ob'yem* carry an ASCII
apostrophe, and inside `python -c '...'` it closes the shell string. Bash then tries to execute
Ukrainian prose as commands.

**Rule:** any edit carrying Ukrainian text goes through a file in the scratchpad, never through
`-c` with a single pair of quotes. This is not a matter of tidiness: the error looks like a
Python syntax error every single time, and a minute goes into looking in the wrong place.

### A risk in the register can guess the event and miss on the cure

Stage 4, before the first line of code. SAD §11 carried the risk "the MCP library's API will
change" with the mitigation "an extra with a floor, not a pin". Installing by the floor
`mcp>=1.2` produced **2.0.0**, in which the module holding the source article's entry point was
gone and every response field had been renamed.

So the mitigation was not merely weak — **what it prescribed is what caused the event**.

This is the third stage running where a risk comes true, and the third time the mitigation
guessed the event and missed on the cure: on stage 2 it predicted that the line budget would be
hit and named the wrong module to extract; on stage 3, the same.

**Rule:** a mitigation in the register is phrased as **an action that can be taken today**, and
is tested by the question "if the risk fires tomorrow, will this actually help?". "A floor, not
a pin" is no answer to a major version changing the response — it is what permits it.

### A number in an NFR invented before the measurement is a wish, not a requirement

Stage 4. The NFR said "checks ≤ 8 s". Measured after implementation: **11.96 s**, and eight was
unreachable **by construction** — one subprocess start-up costs 0.85–1.7 s, and there are six
scenarios.

The temptation at such a moment is a single one: bend the implementation to fit the number. Here
that would have meant one server for the whole suite — buying seconds with the very property the
checks are written for (one scenario's failure must not be explained by another one's state).

**Rule:** an NFR with a number nobody has measured yet is marked as an estimate and **corrected
on the first measurement**, not defended. The correction is recorded with its reason: the next
reader has to see that the number was measured, not that it was always this.

**What can still be optimised.** Isolation is needed between **scenarios**, not between
assertions: two asserts about one and the same response are one scenario, and a second process
buys nothing there. The difference is thin, and it is exactly what separates honest optimisation
from surrendering the property.

### A profile is cheaper than a guess about what is slow

Stage 4. The check suite had grown to 21.6 s. Two "obvious" optimisations — removing a redundant
process start-up in the demo and shortening the timeout — gave **0.3 s** between them.

The profile showed the real thing: the check "no failure reason is empty" started **the same two
servers** as the failure-phase check. Three seconds for zero new information. Merging them gave
**5.7 s** — twenty times more than both guesses together.

**Rule:** before cutting time, profile — even when it seems obvious where the cost is. One
`sort -rn` line over the milliseconds in the suite's output costs a minute.

**And the same boundary as before:** what may be merged is what is **one scenario**. Two checks
about the same pair of failures — one scenario. Two checks about different servers — not one,
however many seconds it costs.

### Cutting time can silently weaken the check that guards that time

Stage 4. The timeout check said `assert took < 10`, and with a timeout of 1.5 s the mutation
"ten times longer" gave 15 s and honestly went red. Then the timeout was reduced to 0.6 s for
the sake of suite speed — and the same mutation started giving 6 s, that is, **passing**.

Nobody broke anything. The constant bound simply stopped matching a parameter that was reduced
elsewhere and for another reason.

**Rule:** a bound in a check that concerns a quantity is made **derived** from that quantity
(`1.5 + asked * 3`), not a constant. A constant is right exactly until somebody changes the
thing it was once matched against.

### One exception group can produce three different defects in one module

Stage 4. `anyio` wraps a task's exception in a `BaseExceptionGroup`, and that gave **three**
separate defects in the same client:

    empty reason        str(TimeoutError()) — an empty string
    nonsense reason     str(ExceptionGroup) — "unhandled errors in a TaskGroup"
    wrong phase         except ServerRefused did not see the wrapped exception

The third is the worst: a live, healthy server that answered "no such tool" was diagnosed as
"the process did not start" — precisely the substitution the whole module is written against.
And it had to be fixed somewhere other than where it showed: not in the `except`, but in the
unwrapping of the cause.

**Rule:** in code that uses async libraries, both the **type** and the **text** of the cause are
taken from the unwrapped exception, never from what arrived at the outside. One helper, one
call.

### Two Accepted ADRs of one stage can contradict each other

ADR-0003 said "MCP does not see the access level at all". ADR-0004 of the same stage decided
that the access level travels **in the payload**, that the server reads it and filters the
result — and a check proved exactly that. The wording had spread across four files, and no check
was holding it.

The correct claim was narrower: **the model** does not see it, because the client strips the
field from the schema.

**Rule:** a wording that sounds like a slogan ("X does not see it at all") is tested by the
question "who exactly does not see it, and at which step". If the answer is longer than the
slogan, the answer is what goes into the document.

### A foreign data structure arrives unvalidated, whatever the typing says

`mcp.types.Tool.input_schema` is declared as `dict[str, Any]` — and that is everything the
library promises. Checked over the wire against a hand-made server: `"properties": null` gave an
`AttributeError`, `"required": null` a `TypeError`, `"properties": ["query"]` an
`AttributeError` again. A foreign server brought down the registry build entirely.

**Rule:** everything that has crossed a process boundary is parsed on the assumption "whatever
should be a container here may be anything at all". `schema.get("properties") or {}` is not
enough — `isinstance` is required. Plus a separate check using verbatim the shapes that already
broke it.

### Fixed a defect — write the check, or the defect comes back silently

Stage 4. The review found that a foreign schema brings down the registry build, and that a
duplicated name silently shadows a permitted tool. I fixed both, verified by hand in the console
— and **wrote no check at all**.

The mutation run showed it immediately: both mutations restoring the old behaviour gave **0
red**. The code was repaired exactly until the next refactor.

Checking by hand proves that it works now. A check in the suite proves that it will keep
working.

**Rule:** every review finding is closed by a **pair** — the code fix and a mutation in
`mutations.json` that reverts that fix. A mutation run after the fixes is mandatory: it shows
not "did I repair it" but "did I protect it".

### An observation becomes a claim only once it has a check

Stage 4 wrote in its NFRs: "check time ≤ 25 s (measured 15.9)". An honest number, measured by
hand. Two tasks later the stage gained a second e2e check — the one that drives those same six
scenes across a process boundary — and the suite came to cost 32 s. The number in the prose
stayed old. It was noticed by accident, a month later, when the time caught the eye in somebody
else's run.

**This is the third case of the same class on one stage.** The number of checks drifted from the
prose — closed with a counter. The line count drifted — closed with a count through the AST. The
time drifted — and was closed with nothing, because it **looked like an observation, not like a
requirement**. There is no difference between the two beyond whether a check exists.

**Rule:** a number that has made it into a document is already a claim. Either the thing that
holds it stands next to it, or what goes into the document is not a number but "measured once,
not held".

**Where to put the guard — where everybody converges.** The temptation was to write the time
check inside stage 4. But there are six stages, and each next one would have rewritten it by
hand. The ceiling is declared in the module in one line (`BUDGET_SECONDS`), and the runner holds
it — one mechanism for all, and a new stage gets it for free.

**A ceiling is not a target.** 90 against a measured 32: the guard has to catch a tenfold
slowdown, not a one-percent one. A tight bound on a slower CI runner flickers, and a bound that
flickers gets raised without thinking — after which it stops meaning anything at all. The
mechanism was verified by deliberate breakage: a ceiling of 0.01 s turns the module red.

### The question that finds the most: "what has to break for this check to go red?"

Stage 5, the review gate. Twenty-seven findings, and the most expensive one cost not a single
line of code — the reviewer simply asked of every check **what exactly** has to break for it to
fail. Four times the answer was "nothing".

The worst of the four claimed that somebody else's fact does not reach the context. The fixture
stored the text "Deliver to *Bankovu* 11" — the street name inflected, as the sentence requires
— while both assertions searched for the substring *Bankova*, its dictionary form. The
nominative never appears in the text, so `not any(...)` was **always** true — including against
a memory with no owner filter at all.

**This is the third instance of the same inflection trap** (*Kyiv*/*Kyievi* on stage 1,
*Volodymyrska*/*Volodymyrsku* on stage 5). The first two turned a check **red** and were found
in minutes. This one turned it **green forever** — and that is exactly why it lived until the
review.

**Rule:** a check that asserts a negative (`not in`, `assert not any`) must first prove that the
fixture is capable of matching at all. One line:

```python
assert any("Bankov" in f.text for f in stored), "the fixture holds no foreign fact"
assert not any("Bankov" in t for t in texts), texts
```

Without the first line, the second assertion proves only that the author wrote the same word two
different ways.

**In practice:** grep the suite for `assert not`, `not in`, `assertNotIn` and for each one ask
what the function has to return for the assertion to pass on broken code. The most frequent
answer is "empty", and "empty" is almost always reachable.

### A demonstration of a defect can be more sensitive than a check for it

The same stage. The mirror isolation check passed and caught its own mutation — but for the
wrong reason: the foreign facts and one's own had **the same score**, and one's own survived
only because `sorted()` is stable and it had been added last. Swap two lines in the fixture and
the check goes green on broken code without a single assert changing.

It was not found from a red run. I was writing the solution for the reader — three memory
implementations side by side on the same data — and the middle one printed "1 fact" where it
should have printed "empty".

The reason is simple: **a demonstration that shows nothing is visibly useless, while a check
that proves nothing looks exactly like a check that proves something.** A demonstration has no
slack; a check has plenty.

**Rule:** if a stage has a solution or a demo that shows the defect beside its fix, write it
**before** considering the check finished. It costs twenty lines and catches what the check is
blind to.

### The risk register is worth re-reading at the moment a risk fires

Stage 5's SAD carried the line: "`long_term`'s line budget is too tight… what will have to be
extracted is **not** retrieval (that is already separate) but fact extraction — it is the only
part that needs a model".

Fixing the review findings brought the module to **90 out of 90**. The temptation was to raise
the budget. Instead I opened the register and saw that the place to extract had already been
named — and named correctly. Extraction became `extraction.py`, and the module went back to 79.

A mitigation written in advance usually guesses the **fact** ("it will get tight") and misses
the **place** ("what exactly to extract"). This time it guessed both — and that is visible only
because the register was re-read at the moment it fired, not before the stage.

### A course can teach a rule and break it in its own code

Stage 5 gave a "what to remember" checklist: six questions, the first being "is this a secret?",
the fourth "was it explicitly asked to be remembered?". The order is deliberate, and there is a
paragraph about it: "remember my password" satisfies both, so the answer depends entirely on
which question comes first.

A week later stage 6 was wiring the service together, and this line appeared in it:

```python
if question.lower().startswith(("remember", "note down")):
    self.store.remember(...)
```

One rule out of six. The fourth. The service stored passwords **and put them into the trace**
along with the rejection reason — on a stage whose claim reads literally: "a key in a trace is a
key in a file read by whoever is debugging".

**The mechanism of the mistake is worth naming precisely.** I did not forget the checklist — I
wrote it. I did not ignore the rule — I formulated it. At the moment of writing `_remember` I
was simply thinking about wiring, not about memory, and `decision.py` never once came to mind.

**Rule:** when a stage **uses** a previous stage's mechanism, a check has to assert that it uses
it **whole**, not in part. The cheapest form is a call to the other module's function instead of
one's own `if`: `decide(...)` cannot be executed halfway.

A clean context found this, and nobody else could have: inside the head that wrote both stages,
they are consistent by construction.

### A check that searches a config for a substring proves that a substring exists

Two of stage 6's checks had the `FAILURE ·` prefix, the right claim, and no teeth:

```python
assert "migrate:" in compose
assert "service_completed_successfully" in compose
```

Move the dependency from `api` to `caddy` and the service starts before the migrations — that
is, exactly the breakage the check names sets in. Both substrings are in place; the check is
green.

The second searched for `$BASE` in the smoke script and counted occurrences. The "locally we
check less" branch passed every assertion — that is, did precisely what the check forbids.

**Rule:** a config has to be **parsed**, not grepped. YAML has a parser, and a claim about
structure (`services["api"]["depends_on"]["migrate"]`) goes red where a claim about text stays
green. The price is one dependency in `dev`.

The same principle has already been applied twice to code (AST parsing instead of a text
search). A config is no different: it too is a structure read by a machine.

### A demo must not print a number it did not obtain

The "mirror halves" scene printed:

```
  smoke:  ./deploy/smoke.sh https://localhost -> 10 passed, 0 failures
```

The script was never run. The number came from the author's memory. And it also **dropped the
third state** ("1 not evaluated"), which the script itself forbids dropping — so the demo
contradicted the very thing it was showing next to it.

**Rule:** a demo prints only what it has just computed. A number the demo cannot obtain by
itself is replaced by the command the reader will run. Prose that retells a result is the same
defect as an unmeasured number in an NFR, only louder: every reader sees it.

### Deployment finds a class of defects unreachable by unit tests

Four defects from the first real deployment, and three of them invisible to tests **by
construction**, not through negligence:

    volume belonged to root               permissions live between process and OS; tests run as you
    nobody applied the migrations         order lives between containers; tests have none
    failed query poisoned the connection  state lives in TIME; tests have no past

The third is the most instructive: `InFailedSqlTransaction` means the service stayed broken
**after the cause was gone**. The table appeared, and the connection kept failing.

**The class is wider than databases:** a cached negative DNS answer, a circuit breaker with no
half-open state, a client that marked a node dead and never re-checks, a flag set on the first
error and never cleared. The shape is one: **fix the cause — the symptom stays**.

**Rule:** before considering a service ready, ask of every long-lived object: **what state can
one failure leave it in forever?** That question finds such defects in a minute, with no
deployment at all. But nothing prompts you to ask it until you have been burned.

### A check that compares one source with itself is an identity

Stage 8 was writing the evaluator. Its e2e level judged `case.answer` — the case's
**description** — while `trajectory.answer()` existed and was called by no level at all. The
check "the same answer, different paths" compared:

    straight.by_level(E2E).state == lucky.by_level(E2E).state

Both cases carry the same string and go through one deterministic judge. The assert cannot be
violated — and it was green while the trace held no answer whatsoever.

**The question that finds this class:** *where did the two sides of the equality come from?* If
from one object, it is an identity, and it will hold even when the data never arrived. The same
stage does it right next door: `report.parse()` reads **the written file**, not the run's
counters.

### Prose that nobody runs goes stale silently

Three of stage 8's defects, found by the review, are one and the same defect in three places:

    ModelJudge                was not even in check.py's list of imports
    the demo's eighth scene   looked for traces/s01.jsonl — a name the tracer never creates
    the TRACE_SINK message    pointed at an ADR that decided no such thing

In all three cases the code was **read** and nothing was noticed. A score parser for which "3
out of 10" meant a ten would have lived until the first run with a key; a scene that never
executed printed its answer to an acceptance criterion as fixed prose.

**Rule:** if a branch cannot be executed in the suite, substitute its transport and execute it.
A judge that goes to the network is checked by substituting `_ask`; a scene that reads the disk,
by a temporary directory. "Not checkable without a key" is `NOT EVALUATED` for the **network**
part, not for a parser that has nothing to do with the network.

### A number about a missing measurement must not itself be a guess

Stage 8 was to close stage 6's promise: to say what the evaluator lacks in the traces. It said
so — and **got it wrong twice**: it counted stage 4's failure phase (`None` on the happy path)
as a run key and forgot stage 7. The figure stood in five places, including a checklist where
the reader was asked to repeat it.

Worst of all, the ADR contradicted itself: its measurement block listed stage 7's steps while
the summary table below skipped that stage.

**Rule:** an ADR that names a number must name **the way to obtain it**, and the suite must
reconcile the prose against that way. Here the inventory now parses the tracer calls in the
sources. And it parses the **AST**, not a grep: stage 7's `whole(run=run)` is a function
parameter, and the grep read it as a trace field — that is, it erred in exactly the same way a
human did.

### A negative assert is true by construction more often than it seems

Stage 8's privacy check looked for the user's text in a `Watch` object made of counters and
fixed literals. No code mutation could have got a string in there — the assert was green **by
construction**. A real leak path existed all the while: the component level copied the free-form
`reason` field straight into the verdict's reason, and the report printed it.

**The question:** *what plausible breakage will this assert catch?* If none, it is not a check
but a comment with the keyword `assert`. A negative about **code** is written through
`code_mentions` (AST, blind to docstrings); object identity through `is`, not through a
substring holding an import's name.

### The mutation run is the cheapest reviewer, and it goes before the humans

On stage 8 the mutations found three defects **in freshly written checks** before a single
reviewer had seen them: the mirror case was degenerate (the judge was silent altogether — both
formulas gave zero), the share check flickered (random identifiers, 10 % over 21 trajectories —
zero roughly once every nine runs), and the privacy check was coupled to a neighbouring module.

The exercise itself found the fourth: the mutation `gap > 1` silenced nothing, because both gaps
in the suite equal two. An exercise that promises red and delivers green teaches that checks
have no teeth.

**Rule:** the mutation run comes **before** calling the reviewers, not after. It costs minutes
and takes off their plate a class of findings they would spend hours on.

### A filter that removes exactly the violators makes an assert about them a tautology

Stage 9 asserted "every implementation performs the same task" like this:

    ran = _counted_rows(rows)      # keeps the ones where `not row.broken`
    for row in ran:
        assert not row.broken      # ...and asserts that there is no broken one

The same helper backed two more checks. Both reported `ok`, having proved the property on two
rows out of four — while the reader has every reason to think all four were proved.

**The question that finds this class:** *can the subject of the assert get into the thing it
iterates over at all?* If the collection was filtered on that same property — no. And
separately: **incomplete coverage is reported as the third state**, not as green. `NOT
EVALUATED` with a list of what was not proved is honest; `ok` on two out of four is not.

### A lesson's claim is checked with the command the lesson recommends to the reader

Stage 9 opened on its headline finding: "no version of CrewAI supports Python 3.14". That same
stage's checklist told the reader to verify it themselves. One command — `pip download crewai` —
returns 0.11.2 and refutes the lesson.

The precise wording turned out **stronger** than the imprecise one: no version **from 0.14.0
on**, that is, none in which the required extension point exists. The choice between "it
installs and there is nothing to hook into" and "the API is there but it does not install" says
more than a plain "it does not install".

**Rule:** before writing "none", "always" or "never", run the command the reader will check it
with. A lesson whose first claim is refuted by its own first exercise loses not the claim but
the trust in everything else.

### A literal in a banner is a tautology the check will not see

Twice in a row, on stages 8 and 9: the demo prints the fixed string "the model is fake", and the
check asserts `output.startswith("[FakeLLM]")`. Both halves come from one literal, so the assert
is always true — including in the run of a reader who has a key configured.

**Rule:** the banner comes from the **factory**, not from a stage constant, and the check
compares it against what the factory returns right now. The same class as "an invariant with two
terms": an equality whose two sides come from one source is not a check.

### A hard-coded model name breaks the stage for exactly the reader who did everything right

`create(model="fake", …)` works right up until the reader configures a key. After that
`get_client()` returns the real client, the provider refuses a non-existent model, and the stage
fails on its very first scene — for the person who completed stage 1 and followed the
instruction.

The same kind of mistake as "an instruction that punishes obedience", only from inside the code.
A second instance turned up beside it: the flag `S09_ADK=1`, documented in the module's own
docstring, took down seventeen checks out of twenty-eight by demanding credentials the
implementation deliberately does not use.

**Rule:** before the tag, run the stage **both** ways — with a key and without. The "with a key"
branch usually has no check at all, because the checks are offline; so it is checked by hand, or
it is not checked at all.

### Warm-up, ceiling, threshold: everything that holds a number must have a check

Stage 9's invisible-lines column flickered from process to process, because the first run traces
the import as well. A warm-up fixed that — and **no check would have noticed the warm-up
disappearing**: all twenty runs of the determinism check happen in one process, where the import
has already occurred.

The number turned out worse than expected: a cold start gives 13992 executed lines against 1895
warm — sevenfold.

**Rule:** a determinism check that lives in one process sees only the flicker **inside** that
process. One fingerprint has to be taken in a subprocess — otherwise a whole class of
instability is invisible by construction. And more broadly: if some mechanism holds a number (a
warm-up, a sort, a cache), ask which check exactly goes red when it disappears. If there is
none, the mechanism effectively does not exist.

### A comparison in which one participant shares code with another is asymmetric

The framework implementation imported five lines from the baseline — and the "my lines" column
showed a difference of twelve instead of seventeen. The error leaned towards "the framework is
cheaper", that is, towards the conclusion one wants.

**Rule:** in a comparison every participant pays for everything it executes. Duplicating code
between the participants of a comparison is not negligence but a condition for the measurement
to be correct.

### "Imports" is not the same as "uses"

Stage 10's claim in its first draft read "the capstone imports what is mature from stages 1–9".
Reading `stages/s06_platform/app.py` killed it: stage 6 **already** imports four stages, and
writing that would have meant describing something that happened four stages ago.

But the real claim lay in that same line. From stage 2 **one name** is imported — the
access-level constant, which travels on as an argument. Search, embeddings, the access filter —
everything stage 2 exists for — is executed **never**.

A list of imports hides this. The proof of reuse has the form of **executed lines**, not
`import` lines. The question "how much of this part actually runs" has a number for an answer,
and the answer regularly turns out to be zero.

### A number that is computed, and a number that comes from nowhere

Two of stage 10's holes were found by the **mutation run**, not by the author and not by the
review. Both of one kind: the number was being computed, but nothing asserted **where it came
from**.

The adapters' cost did not depend on the `ADAPTERS` registry — you could count every function in
the module and the check "the cost is less than the whole module" stayed true. The warm-up
before the measurement had no witness at all: by that point in the check suite it changed
nothing any more, because the preceding checks had imported everything.

The patch for the first one is deliberately **behavioural**: remove one adapter from the
registry and the number must drop. Rewriting that same count inside the check would have meant
proving that two copies are identical. The same class that was caught on stages 8 and 9: **an
equality whose two halves come from one source**.

### The check suite hides the effect by its own run order

The mutation "remove the warm-up" turned nothing red. The check was honest; the conditions it
ran in were not: twenty other checks had already worked before it, and `sys.modules` handed back
ready-made modules.

A measurement in a **fresh process** gave 234 lines against 166 — forty-one percent of excess,
and all of it towards "assembly is expensive".

The lesson is wider than warm-ups: if an effect depends on process state, the check suite will
**not see it**, because the suite is what creates that state. Such things are measured in a
subprocess, and that is not excess.

### The same function does not yet mean the same conditions

The demo printed 166, the check measured 165. Both numbers already went through **one** call —
the shared measurement function. The difference sat in the **input**: in the demo the trace file
already held a scenario run, so the evaluator executed the parsing branch; in the check the file
was empty and that branch never ran.

A measurement of executed lines depends on the **data**, not only on the code. A shared function
removes one of the two causes of divergence; the second — identical conditions — has to be
arranged separately.

### A mismatch goes into the adapter, never into the part

During assembly there is inevitably a part that one edit would make more convenient. The edit is
cheaper than an adapter, cleaner to look at, and improves the stage itself.

And it is forbidden. A part that had to be changed refutes the claim "the parts were mature",
and the change also touches that stage's lesson, checks, tag and article. Every mismatch goes
into an adapter and into **the number**; the need for the edit goes into the report, with the
stage named.

For the same reason an adapter **decides nothing**. One that decides is a part, and a part
belongs in a stage — with a lesson and checks.

### An empty "what turned up" section is the most suspicious result

Nine modules designed independently do not fit together perfectly. A report that says otherwise
reports not on the assembly but on the author's wishes.

So the "what the assembly revealed" section is checked by a **number**, not by the presence of a
heading, and every item in it names a stage. Stage 10's seven items are not self-criticism but
the most honest summary available: a triumphant finale would have proved less.

### An instrument that measures itself reports that as work

Stage 9 stood among the assembly's parts and gave a non-zero number — exactly **one**. That
looked modest and plausible. Running `measure(lambda: None)` on **empty work** showed the same
one: stage 9's single executed line is the disabling of tracing in the `finally` of its own
counter.

"Measures" is not the same as "uses", and the difference between them is exactly the same as
between "imports" and "uses". The review found it, not the author, and the cheapest probe turned
out to be one line: **run the measurement on empty work and see what it reports**.

### Four documents can promise what no criterion asks for

The spec's §1, `sad.md` twice, `CURRICULUM.md` — all of them said "a second deployment". No ASGI
surface existed, and §5 had **not one** acceptance criterion about it. The promise lived in prose
and never reached the place where somebody checks it.

A review that goes "spec → code" catches this with its first question: **which AC proves this?**
If there is no answer, the promise is not a requirement — it is decoration.

Incidentally, it turned out that the surface cost zero adapters: stage 6's `create_app` accepts
an assembled service, because the stages agree **by shape, not by name**.

### One half of a claim is satisfied by doing nothing at all

The check "one request is counted exactly once" was green and incomplete: code that counted
**nothing at all** satisfied it too. A mutation that removed the successful accounting sailed
straight past it.

The same with the cost: "the cost is less than the whole module" stayed true even after the cost
stopped depending on the adapter registry.

**Rule:** a claim about a number must have both halves — "no more" and "no less"; or else be
**behavioural**: remove an input and the number must change.

## 6. Tags and the reader's navigation

**Directories for navigation, tags for links.**

- `stages/sNN_slug/` — every stage visible at once, each self-contained.
- `git tag -a stage-NN` — **after** the review passes, on the commit the article describes.
- The article links **to the tag**: `github.com/AZANIR/agentic-ai/blob/stage-NN/...`
- A reader doing the exercises makes their own branch.

Why not a branch per stage: our stages are separate directories, not versions of one codebase.
Cumulative branches would mean forward-porting every fix into nine branches; stage 1 was fixed
twice in one day.

Why not links to `main`: ADR-0003 says outright that the validation from stage 1 moves into
`shared/` at stage 3. A reader arriving from article 1 six months later would see code the
article does not describe.

## 7. The article comes after the stage, never before

An article about an unwritten stage would describe code that does not exist — exactly the
defect this course is built against.

### Where an article lives

Articles are written straight into the blog repository, at
`src/content/articles/{slug}/index.mdx`, together with their `imgs/` and their `claims.json`.
This repository keeps no copy: a second copy is a second thing to keep in step, and the one
that is not published is the one that quietly goes stale.

### The artstroy format (checked against their zod schema)

```yaml
isDraft: true                          # false only after approval
title: "…"                             # ≤80 characters
description: "…"                       # ≤180 characters
cover: "./imgs/cover.webp"             # REQUIRED — without the file astro check fails
covert_alt: "…"                        # covert_alt indeed; the typo is real, and it is theirs
category: ai-coding                    # only: ai-coding devops documentation pentesting programming technology
authors: ["leonid-m"]
publishedTime: "YYYY-MM-DDT00:00:00.000Z"
```

Directory: `{slug_snake_case}/index.mdx` plus `imgs/` and `claims.json`.
Branch: `article/{slug-kebab}`. Commit: `content(article): add {description}`.

### The site's style rules

- **No `# H1` in the body** — the layout supplies the title.
- Open with a concrete scene, not a definition. Often followed by "the reflex says X, and the
  reflex is wrong".
- A closing table with a **wrong fix** column — their signature device.
- Numbers always carry their source; internal links are `/articles/{slug}`.
- **```` ```mermaid ```` renders as a CODE BLOCK, not a diagram** — mermaid is wired into one
  interactive component only. Use ASCII or tables for diagrams.
- The cover is produced by their stage 3 (`nano-banana-pro`) from the `covert_alt` text.

### The angle

What tutorials never have is **what broke and how it was found**. Article 1 is built around the
seven review findings rather than around "how to make an agent".

## 8. Checking an article against the code

```bash
python scripts/article_check.py                # every article
python scripts/article_check.py three_guards   # one
python scripts/article_check.py --facts s03    # what can be verified for a stage
```

A **template** used to stand here, and every article was verified by a script written from
scratch and left in a session scratchpad. The consequence is not inconvenience: two articles
verified by different sets of assertions cannot be compared, and a verification that cannot be
repeated is a memory of one.

Everything is read **from the tag** the article links to, not from the current code. A number
computed on `main` would describe a different article: the code moves on, the article stays
where it was published.

Five dimensions:

    frontmatter   required fields and the blog schema's bounds
    attribution   no mention of an assistant
    links         links point at a tag, the tag exists, the path exists AT that tag
    snippets      fragments appear in a real file of the same tag
    claims        numbers name their source, and the source is recomputed

**Numbers are the point, and the only optional dimension.** A `claims.json` sits beside the
article: a list of `{what, how much, from where}`, where "from where" is a computation
(`checks`, `failure_modes`, `executable_lines`, `mutations`, `mutation_red`, `exercises`).
Without the file the dimension reports `NOT EVALUATED` rather than green: "not verified" and
"matched" are different states.

The check has three sides, not two: the number must appear in the article's own prose, match
what the computation returns at the tag, and name the source. Taking both halves from the tag
would prove only that two copies agree — the tautology this repository has caught at stages 8,
9 and 10, and then made again in the tool built to catch it.

**Simplifications are allowed but named.** A fragment illustrating a shape rather than quoting a
file is declared in `claims.json` together with its reason — the same requirement stage 10 puts
on decisions with no source stage: either a source, or a stated reason why there is none. A
declaration with no reason is a defect; a silent exemption would turn the check into decoration.

The script is **not** part of `check_all.py`: it reads the blog repository, which it expects
beside this one (or at `ARTSTROY_REPO`). Without it the run reports `NOT EVALUATED` rather than
failing — for most clones the articles simply are not there.

It accepts **both** failure-mode markers, `FAILURE ·` and the older `ВІДМОВА ·`, and that is not
a compatibility tail. The repository moved to English (ADR-0008) while tags cannot be rewritten,
so `stage-01`…`stage-10` keep the old marker forever. A counter that knew only the new one
reported zero at every tag and declared a discrepancy in seven articles out of ten.

## 9. Checklist before starting a stage

- [ ] Re-read §5 — the lessons already paid for
- [ ] The previous stage has its tag and its article
- [ ] `python scripts/check_all.py` is green
- [ ] If this stage rewrites something from an earlier one (as `shared/` at stage 3), it is
      recorded in an ADR
- [ ] A backup exists, if anything destructive is planned

## 10. Checklist before closing a stage

- [ ] All nine items of §3
- [ ] Reviewed by two clean contexts, every MAJOR closed
- [ ] Mutating a key guard produces an `AssertionError` with meaningful text, **not** an
      infrastructure error
- [ ] NFR numbers re-measured, not copied from the previous stage
- [ ] Tag created and pushed
- [ ] Article checked by the script (§8), `isDraft: true` until approved
- [ ] CI green on both Python versions
