# Glossary

The terms this course introduces. One entry per idea the course actually uses — not a
dictionary of the field.

The stage a term appears under is where it first becomes necessary, not merely where it is
first mentioned.

---

## Repository foundations

These are introduced by the repository itself rather than by any stage. Without them no stage
makes sense.

| Term | What it is |
|---|---|
| <a id="profile"></a>**Profile** | `APP_PROFILE=local\|prod`. Switches WHICH implementations get built, and nothing else. `local` — everything in memory, offline, deterministic. `prod` — Postgres, Redis, a real model, metrics. The branching lives in exactly one place: the factories under `shared/`. See [ADR-0002](docs/adr/0002-profile-switched-adapters.md). |
| <a id="adapter"></a>**Adapter** | Two implementations of one interface — a teaching one and a production one. Stage code does not know which it was handed. That is what lets you learn on the same code that later carries load. |
| <a id="fakellm"></a>**FakeLLM** | A deterministic client that replays a pre-recorded script of responses. Not a mock for a test's sake but a teaching instrument: only with it can you check that "the step limit fired" — against a real model that check is impossible, because it is not deterministic. [ADR-0006](docs/adr/0006-assert-checks-over-test-framework.md). |
| <a id="trace"></a>**Trace** | The sequence of steps of one agent run: what the model was asked, which tool it chose, what came back. One JSON line, one step. Present **from stage 1** rather than bolted on at stage 8 — [ADR-0005](docs/adr/0005-tracing-from-stage-one.md). |
| <a id="check"></a>**Check** | A stage's `check.py`: bare `assert`, offline, no key. The rule: at least one check always covers a **failure mode**. |
| <a id="failure-mode"></a>**Failure mode** | A specific way of breaking: the endless loop, invented arguments, silent data loss. The course insists on checking these, because a broken system passes the happy path too. |
| <a id="shim"></a>**Shim** | A thin layer hiding the differences between providers behind one interface. Here: `shared/llm.py`, one client for Groq, OpenRouter, Ollama, LM Studio and OpenAI. |

---

## Stage 1 — Agent loop

| Term | What it is |
|---|---|
| **Agent** | A language model that can **act**, not merely answer. Three parts: the brain (an LLM), tools, and memory (optional). |
| **Tool** | An ordinary function the agent is allowed to call: `get_weather(city)`, `get_order_status(order_id)`. |
| **Tool call** | A model response carrying, instead of text, a request to call a function with these arguments. **The model executes nothing itself**: it asks, and your code runs it. Arguments arrive as a JSON **string**, not a dictionary. |
| **Tool schema** | The JSON description of a function's name, purpose and parameters. The model chooses a tool by reading exactly this — which is why a bad name and a vague description break the choice harder than a weaker model does. |
| **ReAct loop** | Reasoning + Acting: Plan → Act → Observe → Decide → repeat. The basis of nearly every agent framework. |
| **Max steps** | The upper bound on loop iterations. Not an optimisation but a guard: without it an agent that cannot finish a task spins forever and spends money doing it. |
| **HITL** (human-in-the-loop) | A mandatory human confirmation before an irreversible action — deleting, sending, paying. |
| **Stateless** | The model remembers nothing between calls. Everything it "knows" you passed it in this very request. |
| **Context window** | How many tokens the model sees at once. Finite — which is precisely why both RAG and memory exist. |
| **Token** | A piece of text (roughly 4 characters in English). The unit in which both the limit and the bill are measured. |
| **Step** | One iteration of the loop: one call to the model plus running **all** the tools it asked for in that response. Asking for three tools at once is still one step. |
| **Tool registry** | The mapping "name → function + schema + irreversibility flag". The single source of truth about what the agent is allowed to do. |
| **Guard** | One of the three mechanisms between the model's decision and its consequence: the step limit, argument validation, the confirmation gate. |
| **Irreversible tool** | A tool whose consequences cannot be rolled back automatically. Not the same as "a tool with a side effect": writing a log line has an effect too and needs no confirmation. |
| **Confirmation gate** | The mechanism that stops an irreversible tool from running without explicit human permission. |
| **Rejection** | The **result of a step**, not an exception: the explanation goes back to the model and the loop continues. |
| **Type coercion** | Silently turning `"3"` into `3`. Forbidden here: it hides the model's mistake exactly where you need to see it. |

---

## Stage 2 — RAG

| Term | What it is |
|---|---|
| <a id="rag"></a>**RAG** · retrieval-augmented generation | Find the few paragraphs closest in meaning to the question, put them in the prompt, and ask the model to answer from those alone. Not "the model read your documents" but "you decided which three paragraphs it would see". |
| <a id="embedding"></a>**Embedding** | A list of numbers representing the meaning of a text. The whole idea of search rests on one property: texts close in meaning have close lists. |
| <a id="vector"></a>**Vector** | That same list of numbers seen as a point in space. Its "dimension" is how many numbers it holds; the teaching embedder here uses 256. |
| <a id="cosine"></a>**Cosine similarity** | How similar two vectors are: 1.0 identical, 0.0 nothing in common. Once the vectors are normalised it is an ordinary dot product — which is why normalisation is not cosmetic. |
| <a id="normalization"></a>**Normalization** | Bringing every vector to the same length. Without it a long document would win on length rather than on relevance. |
| <a id="chunking"></a>**Chunking** | Cutting a document into fragments before indexing. What gets indexed and found is a **fragment**, not a document: in a whole-document vector the meaning averages out. |
| <a id="overlap"></a>**Overlap** | Neighbouring fragments repeat part of each other, so a thought landing on a seam is found in at least one of them. The price is the same text indexed twice. |
| <a id="index"></a>**Index** | Every fragment together with its vector. In memory here, built at startup; persistent storage arrives at stage 4. |
| <a id="retrieval"></a>**Retrieval** | Compute the query's closeness to every fragment and sort. Two lines of code; everything else is the threshold, the top-k and the filter around them. |
| <a id="topk"></a>**Top-k** | How many of the closest fragments go on into the prompt. Not a performance setting: `k` decides whether the model sees the right answer at all. |
| <a id="threshold"></a>**Threshold** | The line below which "found" counts as not found. The only place the system can say "I do not know": cosine always returns a number, and a nearest match always exists. |
| <a id="grounding"></a>**Grounding** | The answer stands on the supplied data rather than on the model's memory. In this repository an ungrounded answer **does not exist as a state**: no sources, no text. |
| <a id="provenance"></a>**Provenance** | Where the thing the answer stands on came from. Attached here by the system from the retrieval result — [stage ADR-0003](docs/features/s02-rag/adr/0003-system-attaches-the-source.md). A model asked to cite will sometimes name a document that does not exist, and an invented citation looks exactly like a real one. |
| <a id="access-level"></a>**Access level** | A fact about **who is asking**, not an argument chosen while answering. That is why it is bound to the tool through `partial` rather than sitting in the schema the model sees. |
| <a id="prompt-injection"></a>**Prompt injection** | A line inside a retrieved document that the model may read as an instruction. A marked DATA block does not make the attack impossible — it gives the model a boundary that otherwise does not exist. |
| <a id="fine-tuning"></a>**Fine-tuning** | Changing the model's **behaviour**: format, tone, vocabulary. RAG adds **facts**. These are not two ways of doing one thing — the checklist is in [`DECISION.md`](stages/s02_rag/DECISION.md). |

---

## Stage 3 — Router

| Term | What it is |
|---|---|
| <a id="supervisor"></a>**Supervisor** | An agent whose tools are other agents. No new architecture: the same loop as stage 1, except an agent sits behind the tool name instead of a function |
| <a id="specialist"></a>**Specialist** | An agent with a narrow tool set and one description of its competence. Narrow is not a limitation but the reason it chooses better than a broad one |
| <a id="handoff"></a>**Handoff** | The moment the supervisor gives the task to a specialist. **The quietest place to lose access rights:** the specialist receives a task, not the asker |
| <a id="state-schema"></a>**State schema** | The declared list of what the graph knows about the task. The most expensive decision to change later: adding a field means every node can now rely on it, and none of them will say so. [stage ADR-0002](docs/features/s03-router/adr/0002-state-schema-is-a-declared-contract.md) |
| <a id="node"></a>**Node** | A step of the graph: the supervisor or a specialist. Lands in `path` and in the trace |
| <a id="edge"></a>**Edge** | A transition between nodes. In the hand-written graph it is `while` and `if`; in LangGraph, `add_edge` and `add_conditional_edges` |
| <a id="revision-loop"></a>**Revision loop** | Sending a task back to a specialist after an unsatisfactory answer. **With no counter this is not "a little slower" but an unbounded bill:** the defect that breaks nothing, and is therefore the most expensive |
| <a id="finish-reason"></a>**Finish reason** | Why the run stopped: `answered`, `no_specialist`, `revision_limit`, `specialist_failed`. A run with no named reason is a run you can say nothing about |
| <a id="competence"></a>**Competence description** | The text the model reads when choosing a specialist. It matters more than the node's name: `orders` tells the model nothing |
| <a id="classifier"></a>**Classifier** | A cheap branch choice with no revision loop. The checklist's third verdict, and most often the right one: most systems built as supervisors needed exactly this |
| <a id="langgraph"></a>**LangGraph** | A library for agent graphs. Here it is the **second** implementation of the same task, so there is something to compare the hand-written one against — not a subject of study |
| <a id="typed-dict-state"></a>**TypedDict state** | How LangGraph stores state. `state.get("typo")` returns a silent `None` — exactly the flexibility whose price ADR-0002 names. Not a flaw in the library: it cannot know in advance which nodes you will add |

---

## Stage 4 — MCP

| Term | What it is |
|---|---|
| <a id="mcp"></a>**MCP** · Model Context Protocol | The protocol by which a server declares its tools and a client reads and calls them. Not a library and not a framework — an agreement about format |
| <a id="host"></a>**Host** | Whatever the agent lives inside: your demo, a chat, an IDE. Owns the client |
| <a id="mcp-client"></a>**Client** | The thing that speaks the protocol. One client per server. **Every decision is here** |
| <a id="mcp-server"></a>**Server** | A separate process that declares tools and runs them. May belong to somebody else |
| <a id="list-tools"></a>**`list_tools()`** | The call that makes an integration **discoverable**: the client need not know in advance what the server can do. That, rather than convenience, is what the protocol buys |
| <a id="tool-resource-prompt"></a>**Tool / Resource / Prompt** | An action / data to read / a prompt template. Confusing them is the commonest MCP mistake: a model does not call a `resource`, and a `prompt` is neither an action nor data |
| <a id="narration"></a>**Narration** | The text a server writes around the useful content: a summary, a warning, a mention of another tool. Not a flaw in the server but a property of the format, and the parser has to survive it |
| <a id="failure-phase"></a>**Failure phase** | `startup` (never came up), `call` (went silent), `parse` (answered, no data in it). Three different events, indistinguishable in a traceback and treated differently. Which is why the phase is a field of the result rather than a line in a message |
| <a id="stdio-transport"></a>**stdio transport** | Exchange over a subprocess's `stdin`/`stdout`. Works offline and without ports; it has no authentication at all |
| <a id="stateless-mcp"></a>**Stateless specification** | The server is not obliged to remember anything between calls. State travels **explicitly, in the payload** — which is exactly why a call from a trace can be replayed verbatim |
| <a id="allow-list"></a>**Allow list** | The tools the client is willing to take. The server offers, the client picks from its own list, and anything unknown is **irreversible** by default |
| <a id="tool-not-endpoint"></a>**A tool is not an endpoint** | An MCP tool is a job somebody wants done, not a row from your REST API. Three endpoints about orders make one tool — [`DECISION.md`](stages/s04_mcp/DECISION.md) |

---

## Stage 5 — Memory

| Term | What it is |
|---|---|
| <a id="short-term"></a>**Short-term memory** | What was said **in this conversation**: the verbatim tail of recent turns plus a summary of what fell out. Lives for one run and should not survive the session |
| <a id="long-term"></a>**Long-term memory** | What is worth knowing about the person **always**. Extract → store → retrieve; survives a restart. Does not know what was said three turns ago — that is short-term memory's job |
| <a id="context-rot"></a>**Context rot** | The answer degrading because of irrelevant material in the context. **Not an error** — no check goes red, no log complains; the answer simply gets a little worse, and then a little worse again |
| <a id="selectivity"></a>**Selectivity** | The ability **not** to fetch what is not needed. Memory's main property: storing a fact is twenty lines, leaving the rest out is the actual work |
| <a id="fact"></a>**Fact** | A flat record: owner, topic, text, time, TTL, status. Flat deliberately — relationships between facts are a knowledge graph, a separate problem with a separate price |
| <a id="topic"></a>**Topic** | What a fact is about ("address", "name"). Contradiction is decided by topic rather than by content: comparing content is already inference, and it costs a model call |
| <a id="fact-status"></a>**Status** | `active` or `replaced`. A replaced record stays in the file and never returns to a result — the history of the replacement is valuable in itself |
| <a id="ttl"></a>**TTL** | How long a fact stays valid. Checked **on retrieval** rather than by deleting on write — you cannot explain something that has been deleted |
| <a id="owner-filter"></a>**Owner filter** | Selecting the asker's own facts. Sits **before** the top-k: after it, someone else's fact takes a slot, gets removed, and your own answer disappears with it. Nothing leaked; nothing arrived either |
| <a id="extraction"></a>**Extraction** | Asking the model "what from this conversation is worth remembering". An empty list is a normal answer, not a failure |

---

## Stage 6 — Platform

| Term | What it is |
|---|---|
| <a id="guard-platform"></a>**Guard** | The mechanism deciding whether a request goes further. There are three, and they are **different**: who you are, how often, on whose budget |
| <a id="rate-limit"></a>**Rate limit** | How many requests per window **one** client may make. A counter shared across the service lets one client stop everybody |
| <a id="budget-guard"></a>**Budget guard** | Stopping model calls when the spending limit is reached. The one that fires after the spend is called a report |
| <a id="constant-time"></a>**Constant-time comparison** | A comparison whose duration does not depend on how far the values matched. Plain `==` leaks the length of the shared prefix through response time |
| <a id="health"></a>**Health** | Whether the service and **each** dependency are working right now. "Alive" with no list is the answer that keeps the monitor quiet until a user complains |
| <a id="metrics"></a>**Metrics** | Aggregates over a period, separated by kind. They do not answer "why" — the trace does |
| <a id="worker"></a>**Worker** | One process of the service. A second worker makes any in-process state untrue — and does it silently |
| <a id="process-local"></a>**Process-local state** | A counter, cache or schedule visible only to its own process. The root of three different defects at this stage |
| <a id="reverse-proxy"></a>**Reverse proxy** | The single entrance in front of the service: TLS, redirects, headers. The service knows nothing about HTTPS |
| <a id="smoke"></a>**Smoke** | A short list of checks against a **live** service, with a verdict. The same list against any address |
| <a id="runbook"></a>**Runbook** | What to do when it breaks. Written from real breakage, not from imagination |
| <a id="migration"></a>**Migration** | A schema change as an up/down pair. Applied by **one** process: two changing the schema at once is a corrupted database |

---

## Stage 7 — Voice

| Term | What it is |
|---|---|
| <a id="ttfa"></a>**Time-to-first-audio** | From the end of the user's turn to the first sound of the reply. **The number of this stage**: in voice a person waits in silence, and total duration describes the system's work while this describes the pause in the conversation |
| <a id="batch-pipeline"></a>**Batch pipeline** | Each step waits for the previous one to finish completely. Time to first audio equals the sum of every step |
| <a id="streaming-pipeline"></a>**Streaming pipeline** | The first fragment moves on without waiting for the rest. The same amount of work; only the moment of first delivery differs |
| <a id="overlap-voice"></a>**Overlap** | Work that happened **earlier**, not faster: recognition runs alongside the speech. Scales with the length of the turn |
| <a id="barge-in"></a>**Barge-in** | Interrupting the reply with the other person's voice. **Two** conditions decide it — level and duration — and neither is sufficient alone |
| <a id="vad"></a>**VAD** · voice activity detection | Here: a level threshold plus a minimum duration. Spectral analysis is a different discipline and a separate dependency |
| <a id="prefetch"></a>**Prefetch** | Calling a tool early, before it is known whether it is needed. Buys time with **wasted work**, and both numbers have to be visible |
| <a id="p95"></a>**p95** | The value only 5 % of runs are worse than. What the user feels. Taken by **nearest rank** — `ceil(0.95·n)`, not rounding: rounding gives a rank one lower on roughly half of all sample sizes |
| <a id="handover"></a>**Handover** | The time during which control belongs not to the pipeline but to whoever is consuming the fragments. A separate term in the budget: attributed to the next step, it makes the most expensive step the one the consumer happened to think after |
| <a id="conservation"></a>**Conservation of the time budget** | `sum of steps + handover + unattributed = total`, with the third term equal to zero. A budget that does not add up is worse than none; one that adds up wrongly is worse still |
| <a id="fake-clock"></a>**Fake clock** | A time source that moves only when asked and **never sleeps**. Makes timing checks deterministic and twenty consecutive runs free |
| <a id="fake-delay"></a>**Fake delay** | A pause of a set length instead of real model work. The order of magnitude is real; the absolute numbers are not |

---

## Stage 8 — Evaluation

| Term | What it is |
|---|---|
| <a id="trajectory"></a>**Trajectory** | The maximal set of trace steps sharing a **run key**. Which key that is belongs to the source rather than the evaluator: stage 1 groups by trace, the stage 6 service by request |
| <a id="eval-levels"></a>**Three levels of evaluation** | e2e (about the final answer), trajectory (about the sequence of steps), component (about one step). Three **independent** verdicts; a combined score would hide exactly what having three levels is for |
| <a id="llm-as-judge"></a>**LLM-as-judge** | A model that delivers a verdict on the quality of an answer. **A measuring instrument**, not the truth: an evaluator that declares its verdict to be fact has trusted a number without asking where it came from |
| <a id="deterministic-evaluator"></a>**Deterministic evaluator** | An evaluator that compares rather than judges. Its judge-call counter reads **zero** — and that is checked by machine rather than left as an understanding |
| <a id="position-bias"></a>**Position bias** | A verdict depending on the **order of presentation**. Detected by running the same pair twice — AB and BA; a tie counts as its own value, because "A won" → "tie" is a flip as well |
| <a id="length-bias"></a>**Length bias** | Preferring the longer answer with no gain in content. There is no threshold here **and there cannot be**: if the second answer is the first plus extra text, any preference is a point for length |
| <a id="mirror-half"></a>**Mirror half** | The same detector run against an instrument known to behave correctly. Without it the finding is worthless: a detector that always fires cannot tell a biased judge from an honest one |
| <a id="not-evaluated"></a>**Unscored** · the third state | Neither passed nor failed: there was nothing to look at. A suite that merges it into failure stops distinguishing a broken system from an interrupted run — and does so in favour of green |
| <a id="blind-spot"></a>**Blind measurement** | A check this trace does not support. It does **not** turn into a finding: otherwise a hundred percent of traffic is flagged as problematic because of something the evaluator cannot see |
| <a id="edge-by-observation"></a>**Edge case by observation** | A case's property derived from the trace — a refusal, a limit, an unknown tool, an empty result — rather than from a label. A self-declared label satisfies the requirement by flipping a flag |
| <a id="online-eval"></a>**Online evaluation** | Cheap deterministic checks over all traffic, the judge over a fraction. **Out of band**: no step stands between the request and the response, and the price of that is named — a request that never reached the tracer is not evaluated at all |
| <a id="deterministic-sampling"></a>**Deterministic sampling** | Selection by a hash of the identifier rather than a random number. The same stream always yields the same fraction, and it can be **checked** against the declared one. Determinism is not correctness, though: a sampler that always says yes is deterministic too |
| <a id="drift"></a>**Drift** | Quality changing over time. Needs **stored history**, so the stage prints the numbers drift is computed from and stops there |

---

## Stage 9 — Frameworks

| Term | What it is |
|---|---|
| <a id="scaffolding"></a>**Scaffolding** | A framework from this stage's point of view: it speeds up construction and says nothing about what you are constructing. Chosen before the shape of the building is known, it **becomes** the shape |
| <a id="task-contract"></a>**Task contract** | Input, tools, model, stopping condition, result shape — shared by every implementation and **executable**. Written as prose it catches no deviation, and the comparison starts measuring the author's diligence |
| <a id="explicit-coordination"></a>**Explicit coordination** | **Code** decides the next step: the whole order is visible in one place. Costs lines |
| <a id="implicit-coordination"></a>**Implicit coordination** | **Text the model read** decides the next step. Costs understanding: the reason has to be reconstructed from descriptions exactly when it is needed most |
| <a id="my-lines"></a>**My lines** | Executable lines the implementation's author wrote and maintains. Half of the "less code" argument |
| <a id="invisible-lines"></a>**Invisible lines** | Lines of the package that **executed** during the run. The other half: the code did not go away, it moved somewhere you cannot see it and cannot fix it. Measured by execution rather than package size, and **without the one-off import** |
| <a id="overhead-tokens"></a>**Tokens above the request** | The difference between what went out and what the contract specified. Counted **at the provider boundary**: a counter inside the implementation sees only what that implementation asked for, which is precisely what misses the overhead |
| <a id="prose-places"></a>**Prose places** | How many named arguments describe behaviour as text (`role`, `goal`, `description`…). The price of answering "why did this step run", measured **from the source** rather than declared as a number |
| <a id="baseline-row"></a>**Baseline** | An implementation with no framework at all, in the same table. Without it the comparison answers "which one" rather than "is one needed here" |
| <a id="constraint-to-tool"></a>**Constraint → tool** | The shape of the conclusion, instead of a combined score. Weights on constraints are an opinion about whose constraint matters more, baked into a number nobody agreed on |
| <a id="interpreter-constraint"></a>**Interpreter constraint** | The sharpest and cheapest one: whether a version of the package exists for your Python. It decides the choice **first**, and no blog post shows it, because every one of them is written where the install worked |

---

## Stage 10 — Capstone

| Term | What it is |
|---|---|
| <a id="assembly"></a>**Assembly** | What this stage measures. Not the service and not its answers, but the **joint**: how much of each part actually works and what it cost to stitch them together |
| <a id="imports-vs-uses"></a>**"Imports" ≠ "uses"** | The stage's thesis, measured on its own code: stage 6 imports stage 2 and executes **zero** of its lines. In the import list the stage is present; in the work it is not, and the list hides that |
| <a id="executed-stage-lines"></a>**Executed stage lines** | Proof instead of an import list: the lines of a stage that **executed** on a request, grouped by directory. The instrument comes from stage 9 together with its limits — the number describes this request and this thread |
| <a id="instrument-measuring-itself"></a>**The instrument measuring itself** | Stage 9 sat among the parts and reported exactly one line: tracing being switched off in its own counter's `finally`. "Measures" is not "uses", and the distance is the same as between "imports" and "uses". Caught by running the measurement over **empty work** |
| <a id="declared-part"></a>**Declared part** | A stage named as part of the assembly. It must produce a non-zero number or it reddens the suite **by its own name**. A stage deliberately not wired sits in a separate list with a reason: zero for it is a decision, not a defect |
| <a id="seam"></a>**Seam** | A joint where two parts did not meet, naming both and the reason. Two different `Answer` classes are not a mistake by either stage alone; the mistake appears exactly when they stand next to each other |
| <a id="capstone-adapter"></a>**Adapter** | Code that exists **only** for a seam: it translates shape and **does not decide**. Whatever decides is a part, and a part belongs in a stage — with a lesson and checks |
| <a id="price-of-assembly"></a>**Price of assembly** | Two numbers in **one unit**: executed adapter lines against executed stage lines. Counting the price statically would set "is in the code" against "runs". One number without the other means nothing; the genre's limit is a fifth |
| <a id="written-versus-executed"></a>**Written against executed** | A difference that is not an error: `build_search` has three written lines and zero executed, because it runs at startup rather than per request |
| <a id="mismatch-goes-into-adapter"></a>**A mismatch goes into an adapter** | The rule that is easiest to break: a part you had to change disproves "the parts were mature", and the change reaches that stage's lesson, checks, tag and article too. The need for the edit goes **into the report**, naming the stage |
| <a id="verified-justification"></a>**Verified justification** | `ARCHITECTURE.md` is parsed by code: the stage exists, the named ADR exists. The limit is stated out loud — it asserts the source **exists**, not that it contains this particular decision |
| <a id="unparsed-row"></a>**Unparsed row** | A table row the parser could not read is a **defect, not silence**. A skipped row is indistinguishable from an absent one, and the dangling citation vanished along with it |
| <a id="agreed-by-shape"></a>**Agreed by shape, not by name** | `Reply` deliberately is not called `Answer`, yet it satisfies the stage 6 application's contract completely — which is why the second deploy cost no adapters at all |
| <a id="what-assembly-revealed"></a>**What assembly revealed** | The section of the report whose emptiness would be the most suspicious possible outcome. Nine independently designed modules do not join perfectly, and a report saying otherwise is reporting on something other than the assembly |
| <a id="warmup"></a>**Warm-up** | Running the work **before** measuring it. Without it, the price of one request carries lines that happen once per process: the bodies of lazily imported modules. Measured in a fresh process: 234 against 166 — forty-one percent of overstatement, all of it in the direction of "assembly is expensive" |
| <a id="final-state"></a>**Final state** | The fourth thing a scenario checks, after the branch, the parts that took part and the tools called: what is left in memory. The course twice caught a correct answer reached the wrong way — and both times the text was flawless |

---

## After this

The course is finished. What joined badly is in the "what assembly revealed" section of
[`stages/s10_capstone/ARCHITECTURE.md`](stages/s10_capstone/ARCHITECTURE.md).
