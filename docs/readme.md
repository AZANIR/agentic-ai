# Articles

Every stage of this course has a written article. The code here is the working proof; the
article is the argument, with the numbers it cites measured at that stage's tag rather than
written by hand.

Each link below points at the article for that stage. Each article links back to the tag it
describes, so the code you read is the code it is about — not whatever `main` happens to hold
today.

| # | Stage | Article |
|---|-------|---------|
| 1 | [Agent loop](../stages/s01_agent_loop/) | [Three Guards Every Agent Loop Needs](https://artstroy.net/articles/three_guards_every_agent_loop_needs) |
| 2 | [RAG](../stages/s02_rag/) | [Your RAG Leak Test Is Green](https://artstroy.net/articles/your_rag_leak_test_is_green) |
| 3 | [Router](../stages/s03_router/) | [The Bug That Breaks Nothing](https://artstroy.net/articles/the_bug_that_breaks_nothing) |
| 4 | [MCP](../stages/s04_mcp/) | [The Tool Description You Did Not Write](https://artstroy.net/articles/the_tool_description_you_did_not_write) |
| 5 | [Memory](../stages/s05_memory/) | [Nothing Leaked, the Answer Disappeared](https://artstroy.net/articles/nothing_leaked_the_answer_disappeared) |
| 6 | [Platform](../stages/s06_platform/) | [The Bugs Only Deploying Finds](https://artstroy.net/articles/the_bugs_only_deploying_finds) |
| 7 | [Voice](../stages/s07_voice/) | [Your Streaming Benchmark Measures Two Things](https://artstroy.net/articles/your_streaming_benchmark_measures_two_things) |
| 8 | [Evaluation](../stages/s08_eval/) | [The Detector That Always Finds It](https://artstroy.net/articles/the_detector_that_always_finds_it) |
| 9 | [Frameworks](../stages/s09_frameworks/) | [Less Code Is Half an Argument](https://artstroy.net/articles/less_code_is_half_an_argument) |
| 10 | [Capstone](../stages/s10_capstone/) | [Your Import List Is Not Proof](https://artstroy.net/articles/your_import_list_is_not_proof) |

## How the numbers in an article are kept honest

An article that quotes a number the code no longer produces is worse than an article with no
numbers at all: it reads as evidence and is not. So every article carries a claims file naming
what it asserts, how much, and which computation produces that value — and a script recomputes
each one **at the tag the article links to**:

```bash
python scripts/article_check.py                # all articles
python scripts/article_check.py three_guards   # one
python scripts/article_check.py --facts s03    # what can be verified for a stage
```

The check has three sides, not two: the number must appear in the article's own prose, match
what the computation returns at the tag, and name the source it comes from. Taking both halves
from the tag would only prove that two copies agree.

Code snippets are checked the same way — a fragment either appears in a real file at that tag,
or it is declared a deliberate simplification with the reason recorded. A silent exemption
would turn the check into decoration.
