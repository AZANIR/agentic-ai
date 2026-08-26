# CONTEXT — the repository's domain vocabulary

The canonical **roles** and **domain objects** every specification here uses. One word, one
meaning, repository-wide.

> This is not the same thing as [GLOSSARY.md](GLOSSARY.md). That file holds the technical ideas
> the course teaches — embedding, tool call, barge-in. This one holds the roles and objects
> that describe **the product itself**. Confusing the two is expensive: the first explains the
> subject, the second describes the system.

Entry format: **Term** — definition. *Not to be confused with:* the nearest homonym.

---

## Glossary

### Roles

- **Learner** — the person taking the course: reads the lesson, runs the demo, does the
  exercises, deploys at stages 6 and 10. Everything in this repository is addressed to them.
  *Not to be confused with:* **Shopper** — that one lives inside the fictional story, while the
  Learner is outside it, at the keyboard.

- **Contributor** — whoever writes or changes a stage: the lesson, the code, the exercises, the
  checks. Bound by [CONVENTIONS.md](CONVENTIONS.md) and by the stage completion criteria.
  *Not to be confused with:* Learner — a Learner consumes a stage, a Contributor produces it.

- **Operator** — whoever deploys and runs the service at stages 6 and 10: keeps `.env` on the
  server, watches the metrics, reacts when the budget runs out. In practice the same person as
  the Learner, with different duties and a different set of risks.

- **Shopper** — a **fictional** character inside the running domain: asks about an order,
  files a return. Never a user of this repository.

### Domain objects

- **Stage** — a self-contained unit of the course: `stages/sNN_slug/`. Holds the lesson, the
  code, the exercises, the reference solutions, the checklist and the checks. A stage counts as
  finished only against all nine criteria in [CURRICULUM.md](CURRICULUM.md).
  *Not to be confused with:* a "step" — a step is one iteration of the agent loop, a stage is a
  chapter of the course.

- **Lesson** — a stage's text (`README.md`): what you will be able to do afterwards, the
  canonical idea, the bridge to our own domain, what to break.

- **Demo run** — running a stage's demonstration. Works **with no API key** and prints a banner
  as its first line: a fake in front of you, or a real model.

- **Stage check** — the set of `assert` checks that run offline. At least one of them always
  covers a **failure mode**.

- **Agent run** — one complete cycle: task → steps → a final answer or a stop at the limit.
  Produces exactly one trace.

- **Step** — one iteration of a run: the question to the model, its decision, the tool call, the
  observation of the result.

- **Tool** — a function the agent is allowed to call, together with the schema of its
  parameters.

- **Irreversible tool** — a tool whose consequences cannot be rolled back automatically: file a
  return, send an email, delete a record. Runs **only after an explicit human confirmation**.
  *Not to be confused with:* "a tool with a side effect" — writing a log line has an effect too,
  and needs no confirmation. Irreversibility opens the gate, not the presence of an effect.

- **Trace** — the ordered sequence of steps of one run. One line, one step. The data the
  evaluation at stage 8 reads.

- **Profile** — `local` or `prod`. Chooses adapter implementations and nothing else.

- **NovaShop** — the fictional online shop running through the whole course, the one domain all
  the canonical examples bridge into: orders, returns, policies, catalogue.
